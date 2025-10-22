"""Rutas de supervisión y auditoría final para Proyecto Horizonte."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse

from horizonte.core.security_monitor import get_security_monitor
from horizonte.governance.audit_engine import AUDIT_REPORT_PATH, audit_snapshot

router = APIRouter(tags=["supervision"])


@router.get("/supervision/status")
async def supervision_status() -> dict[str, object]:
    """Expone el estado actual de seguridad y las últimas alertas."""

    monitor = get_security_monitor()
    integrity = monitor.check_integrity(record_alert=False)
    alerts = monitor.get_alerts()
    report: dict[str, object] | None = None
    if AUDIT_REPORT_PATH.exists():
        try:
            report = json.loads(AUDIT_REPORT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = None
    return {
        "security": integrity,
        "alerts": alerts,
        "latest_report": report,
    }


@router.post("/audit/generate", status_code=status.HTTP_201_CREATED)
async def generate_audit_report() -> JSONResponse:
    """Genera un nuevo informe auditado y devuelve su contenido firmado."""

    payload = audit_snapshot()
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=payload)


@router.get("/audit/report")
async def download_audit_report() -> Response:
    """Entrega el último informe auditado generado."""

    if not AUDIT_REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="No hay informes generados")
    try:
        content = AUDIT_REPORT_PATH.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as exc:  # pragma: no cover - corrupción extrema
        raise HTTPException(status_code=500, detail="Informe corrupto") from exc
    return JSONResponse(content=data)


__all__ = ["router"]
