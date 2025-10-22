"""Ruta de auditoría para Horizonte."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from horizonte.common.db import Ledger, get_session
from horizonte.core import trace_logger

router = APIRouter(tags=["auditoria"])


class AuditRecord(BaseModel):
    """Representación serializada de una entrada del ledger."""

    id: int
    query: str
    response: str
    hash: str
    timestamp: str


class AuditResponse(BaseModel):
    """Respuesta paginada de auditoría."""

    items: list[AuditRecord]
    limit: int
    offset: int


def _get_db_session() -> Iterator[Session]:
    with get_session() as session:
        yield session


@router.get("/auditoria", response_model=AuditResponse)
async def listar_auditoria(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(_get_db_session),  # noqa: B008
) -> AuditResponse:
    """Recupera las entradas del ledger con paginación sencilla."""
    consulta = select(Ledger).order_by(Ledger.id.desc()).limit(limit).offset(offset)
    registros = session.execute(consulta).scalars().all()
    items = [
        AuditRecord.model_validate(trace_logger.serialize_record(registro))
        for registro in registros
    ]
    return AuditResponse(items=items, limit=limit, offset=offset)
