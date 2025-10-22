"""Ruta de inferencia para Horizonte."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from governance.dashboard.main import metrics_manager
from horizonte.common.db import get_session
from horizonte.common.security import sanitize_input
from horizonte.core import ethics_filter, inference_engine, telemetry, trace_logger
from net import consensus_manager

router = APIRouter(tags=["inferencia"])


class InferRequest(BaseModel):
    """Solicitud de inferencia validada."""

    query: str = Field(
        ..., description="Consulta en lenguaje natural", min_length=1, max_length=8000
    )

    @field_validator("query")
    @classmethod
    def limpiar_query(cls, value: str) -> str:
        """Sanitiza la consulta para evitar caracteres no válidos."""

        return sanitize_input(value)


class InferResponse(BaseModel):
    """Respuesta completa de la inferencia."""

    query: str
    response: str
    hash: str
    timestamp: str
    ethics: dict


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
    inicio = time.perf_counter()
    ts = datetime.now(timezone.utc)
    respuesta = inference_engine.infer(payload.query)
    evaluacion = ethics_filter.check(respuesta)
    hash_value = trace_logger.make_hash(payload.query, respuesta, ts)
    registro = trace_logger.persist_ledger(session, payload.query, respuesta, hash_value, ts)

    metrics_manager.record_inference(payload.query, evaluacion)
    latencia_ms = (time.perf_counter() - inicio) * 1000
    telemetry.record_inference(latencia_ms, ethics_denied=not evaluacion.get("allowed", True))
    settings = getattr(request.app.state, "settings", None)
    node_identifier = getattr(settings, "node_id", "nodo-desconocido")
    consensus = consensus_manager.broadcast_result(node_identifier, hash_value)
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
    )
