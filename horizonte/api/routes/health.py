"""Ruta de salud del sistema Horizonte."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter(tags=["status"])


@router.get("/health")
async def health_check(request: Request) -> dict[str, str]:
    """Retorna el estado básico del servicio."""
    settings = request.app.state.settings
    return {
        "status": "ok",
        "node_id": settings.node_id,
        "time": datetime.now(timezone.utc).isoformat(),
    }
