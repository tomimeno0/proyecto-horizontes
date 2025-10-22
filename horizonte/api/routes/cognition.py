"""Endpoints de transparencia cognitiva para AUREUS."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from horizonte.core.metacognition import get_cognitive_mirror
from horizonte.net.cognitive_sync import get_cognitive_sync_manager

router = APIRouter(tags=["cognition"])

POLL_INTERVAL = 5


def _build_status() -> dict[str, Any]:
    mirror = get_cognitive_mirror()
    snapshot = mirror.snapshot()
    manager = get_cognitive_sync_manager()
    sync_status = manager.status()
    payload: dict[str, Any] = {
        "mirror": {
            "divergence_index": snapshot.divergence_index,
            "last_divergence": snapshot.last_divergence,
            "consistency_score": snapshot.consistency_score,
            "auto_eval_cycles": snapshot.auto_eval_cycles,
            "last_self_check": snapshot.last_self_check,
        },
        "network": None,
    }
    if sync_status:
        payload["network"] = {
            "node_id": sync_status.node_id,
            "local_score": sync_status.local_score,
            "collective_score": sync_status.collective_score,
            "action_taken": sync_status.action_taken,
            "timestamp": sync_status.timestamp,
        }
    return payload


@router.get("/cognition/status")
async def cognition_status() -> dict[str, Any]:
    """Devuelve el estado cognitivo agregado y de red."""

    return _build_status()


@router.get("/cognition/history")
async def cognition_history(
    limit: int | None = Query(default=None, ge=1, le=500)
) -> list[dict[str, Any]]:
    """Recupera el historial del espejo cognitivo."""

    mirror = get_cognitive_mirror()
    return mirror.history(limit=limit)


@router.post("/cognition/recheck")
async def cognition_recheck() -> dict[str, Any]:
    """Fuerza una autoevaluación y sincronización inmediata."""

    manager = get_cognitive_sync_manager()
    status = manager.run_cycle()
    return {
        "status": {
            "local_score": status.local_score,
            "collective_score": status.collective_score,
            "action_taken": status.action_taken,
            "timestamp": status.timestamp,
        }
    }


@router.delete("/cognition/reset", status_code=204)
async def cognition_reset() -> None:
    """Limpia trazas cognitivas y reinicia contadores."""

    mirror = get_cognitive_mirror()
    mirror.reset_logs()
    manager = get_cognitive_sync_manager()
    manager.reset()


@router.websocket("/ws/cognition")
async def cognition_stream(websocket: WebSocket) -> None:
    """Envía actualizaciones cognitivas cada cinco segundos."""

    await websocket.accept()
    try:
        await websocket.send_json(_build_status())
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            await websocket.send_json(_build_status())
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover
        await websocket.close(code=1011, reason=str(exc))
        raise
    finally:
        with suppress(Exception):
            await websocket.close()
