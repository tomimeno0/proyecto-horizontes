"""Rutas de auditoría ética adaptativa."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from horizonte.core.adaptive_learning import get_adaptive_trainer
from horizonte.core.ethics_monitor import get_ethics_monitor
from horizonte.core import ethics_filter

router = APIRouter(prefix="/ethics", tags=["ethics"])


@router.get("/metrics")
async def obtener_metricas_eticas() -> dict[str, object]:
    """Expone las métricas éticas adaptativas actuales."""

    return ethics_filter.get_adaptive_metrics()


@router.get("/logs")
async def obtener_auditoria(limit: int = 50) -> dict[str, object]:
    """Retorna los registros recientes del monitor ético."""

    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'limit' debe ser mayor a cero.",
        )
    monitor = get_ethics_monitor()
    logs = monitor.get_audit_logs(limit=limit)
    return {"logs": logs, "count": len(logs)}


@router.delete("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reiniciar_metricas() -> None:
    """Permite reiniciar el buffer adaptativo y los logs (modo desarrollo)."""

    trainer = get_adaptive_trainer()
    trainer.reset_buffer()
    monitor = get_ethics_monitor()
    monitor.reset_audit()
