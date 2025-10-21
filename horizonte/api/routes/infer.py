"""Ruta de inferencia para Horizonte."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, constr
from sqlalchemy.orm import Session

from horizonte.common.db import get_session
from horizonte.core import ethics_filter, inference_engine, trace_logger


router = APIRouter(tags=["inferencia"])


class InferRequest(BaseModel):
    """Solicitud de inferencia validada."""

    query: constr(min_length=1, max_length=8000) = Field(..., description="Consulta en lenguaje natural")


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
async def realizar_inferencia(payload: InferRequest, request: Request, session: Session = Depends(_get_db_session)) -> InferResponse:
    """Procesa la solicitud de inferencia y almacena la traza en el ledger."""
    ts = datetime.now(timezone.utc)
    respuesta = inference_engine.infer(payload.query)
    evaluacion = ethics_filter.check(respuesta)
    hash_value = trace_logger.make_hash(payload.query, respuesta, ts)
    registro = trace_logger.persist_ledger(session, payload.query, respuesta, hash_value, ts)

    return InferResponse(
        query=registro.query,
        response=registro.response,
        hash=registro.hash,
        timestamp=registro.timestamp,
        ethics=evaluacion,
    )
