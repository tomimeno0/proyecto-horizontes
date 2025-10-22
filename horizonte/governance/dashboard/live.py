"""Dashboard en vivo expuesto vía WebSocket."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from horizonte.core import telemetry
from horizonte.core.metacognition import get_cognitive_mirror
from horizonte.net.consensus_manager import get_consensus_manager
from horizonte.net.node_registry import get_registry

logger = logging.getLogger("horizonte.governance.live")


TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["dashboard-live"])

POLL_INTERVAL = 5
NETWORK_POLL_INTERVAL = 10
COGNITION_POLL_INTERVAL = 5
COGNITION_TEMPLATE = Path(__file__).parent / "cognition.html"
AUDIT_TEMPLATE = Path(__file__).parent / "audit.html"


def _network_payload() -> dict[str, object]:
    registry = get_registry()
    nodes = []
    for node in registry.list_nodes():
        nodes.append(
            {
                "node_id": node.node_id,
                "status": node.status,
                "last_activity": node.last_activity.isoformat() if node.last_activity else None,
                "avg_latency_ms": node.avg_latency_ms,
                "sync_score": node.sync_score,
            }
        )
    sync_values = [n["sync_score"] for n in nodes if n["sync_score"] is not None]
    average_sync = round(sum(sync_values) / len(sync_values), 3) if sync_values else 0.0
    consensus = get_consensus_manager()
    return {
        "nodes": nodes,
        "average_sync": average_sync,
        "consensus": {
            "mode": consensus.mode,
            "failures": consensus.failure_streak,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/live", response_class=HTMLResponse)
async def live_page(request: Request) -> HTMLResponse:
    """Renderiza el dashboard de métricas en vivo."""

    return templates.TemplateResponse("live.html", {"request": request})


@router.get("/cognition", response_class=HTMLResponse)
async def cognition_page() -> HTMLResponse:
    """Entrega el dashboard cognitivo basado en metacognición."""

    return HTMLResponse(COGNITION_TEMPLATE.read_text(encoding="utf-8"))


@router.get("/audit", response_class=HTMLResponse)
async def audit_page() -> HTMLResponse:
    """Entrega el panel de auditoría y transparencia final."""

    return HTMLResponse(AUDIT_TEMPLATE.read_text(encoding="utf-8"))


@router.websocket("/ws/metrics")
async def metrics_stream(websocket: WebSocket) -> None:
    """Entrega métricas periódicamente a través de WebSocket."""

    await websocket.accept()
    try:
        await websocket.send_json(telemetry.get_metrics())
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            await websocket.send_json(telemetry.get_metrics())
    except WebSocketDisconnect:
        logger.info("live_client_disconnected")
    except Exception:  # pragma: no cover - protección ante fallos
        logger.exception("live_metrics_error")
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@router.websocket("/ws/network")
async def network_stream(websocket: WebSocket) -> None:
    """Entrega información de nodos y consenso cada 10 segundos."""

    await websocket.accept()
    try:
        await websocket.send_json(_network_payload())
        while True:
            await asyncio.sleep(NETWORK_POLL_INTERVAL)
            await websocket.send_json(_network_payload())
    except WebSocketDisconnect:
        logger.info("network_client_disconnected")
    except Exception:  # pragma: no cover - protección adicional
        logger.exception("network_metrics_error")
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@router.websocket("/ws/cognition")
async def cognition_stream(websocket: WebSocket) -> None:
    """Envía el estado cognitivo actualizado para el dashboard."""

    await websocket.accept()
    try:
        mirror = get_cognitive_mirror()
        await websocket.send_json(mirror.stream_payload())
        while True:
            await asyncio.sleep(COGNITION_POLL_INTERVAL)
            await websocket.send_json(mirror.stream_payload())
    except WebSocketDisconnect:
        logger.info("cognition_client_disconnected")
    except Exception:  # pragma: no cover - protección adicional
        logger.exception("cognition_stream_error")
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


__all__ = ["router", "metrics_stream", "network_stream", "cognition_stream"]
