"""Ruta de inferencia para Horizonte."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from governance.dashboard.main import metrics_manager
from horizonte.common.db import get_session
from horizonte.common.security import sanitize_input
from horizonte.core import ethics_filter, inference_engine, trace_logger
from horizonte.core.telemetry import record_inference as record_internal_inference
from net import consensus_manager

router = APIRouter(tags=["inferencia"])


class InferRequest(BaseModel):
    """Solicitud de inferencia validada."""

    query: str = Field(
        ..., description="Consulta en lenguaje natural", min_length=1, max_length=8000
    )


class InferResponse(BaseModel):
    """Respuesta completa de la inferencia."""

    query: str
    response: str
    hash: str
    timestamp: str
    ethics: dict
    ethics_metrics: dict


def _get_db_session() -> Iterator[Session]:
    with get_session() as session:
        yield session


@router.post("/inferencia", response_model=InferResponse)
async def realizar_inferencia(
    payload: InferRequest,
    request: Request,
    session: Session = Depends(_get_db_session),  # noqa: B008
) -> InferResponse:
    """Procesa la solicitud de inferencia y almacena la traza en el ledger."""
    ts = datetime.now(timezone.utc)
    inicio = time.perf_counter()
    query_sanitizado = sanitize_input(payload.query)
    respuesta = inference_engine.infer(query_sanitizado)
    evaluacion = ethics_filter.check(respuesta)
    hash_value = trace_logger.make_hash(query_sanitizado, respuesta, ts)
    registro = trace_logger.persist_ledger(
        session, query_sanitizado, respuesta, hash_value, ts
    )

    latency_ms = (time.perf_counter() - inicio) * 1000
    ethics_denegada = not bool(evaluacion.get("allowed", False))
    record_internal_inference(latency_ms, ethics_denegada)

    metrics_manager.record_inference(query_sanitizado, evaluacion)
    adaptive_metrics = ethics_filter.register_adaptive_inference(
        query=query_sanitizado,
        response_hash=hash_value,
        flags=evaluacion.get("flags", []),
        response_time_ms=latency_ms,
        allowed=bool(evaluacion.get("allowed", False)),
    )
    settings = getattr(request.app.state, "settings", None)
    node_identifier = getattr(settings, "node_id", "nodo-desconocido")
    consensus = await consensus_manager.broadcast_result_async(
        node_identifier, hash_value
    )
    logger = getattr(request.app.state, "logger", None)
    if logger:
        logger.info("consenso_inferencia", extra=consensus)
    if consensus.get("approved"):
        metrics_manager.register_consensus(hash_value)

    return InferResponse(
        query=registro.query,
        response=registro.response,
        hash=registro.hash,
        timestamp=registro.timestamp,
        ethics=evaluacion,
        ethics_metrics=adaptive_metrics,
    )
