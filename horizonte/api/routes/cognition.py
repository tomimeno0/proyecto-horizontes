"""Endpoints públicos para la metacognición de Horizonte."""

from __future__ import annotations

from fastapi import APIRouter, Query

from horizonte.core.metacognition import get_cognitive_mirror

router = APIRouter(prefix="/cognition", tags=["cognicion"])


@router.get("/status")
async def cognition_status() -> dict[str, object]:
    """Devuelve el estado actual del espejo cognitivo."""

    snapshot = get_cognitive_mirror().status()
    return {
        "divergence_index": snapshot.divergence_index,
        "global_consistency": snapshot.global_consistency,
        "collective_consistency": snapshot.collective_consistency,
        "cycles": snapshot.cycles,
        "last_audit": snapshot.last_audit,
    }


@router.get("/history")
async def cognition_history(
    limit: int | None = Query(None, ge=1, le=500, description="Entradas más recientes"),
) -> list[dict[str, object]]:
    """Lista las entradas registradas en el log cognitivo."""

    return get_cognitive_mirror().history(limit=limit)


@router.post("/recheck")
async def cognition_recheck(limit: int = Query(50, ge=5, le=200)) -> dict[str, object]:
    """Fuerza una autoevaluación inmediata."""

    return get_cognitive_mirror().analyze_self(limit=limit)


@router.delete("/reset")
async def cognition_reset() -> dict[str, str]:
    """Limpia las trazas cognitivas registradas."""

    get_cognitive_mirror().reset()
    return {"detail": "trazas_cognitivas_reiniciadas"}


__all__ = ["router"]
