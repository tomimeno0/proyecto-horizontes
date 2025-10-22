"""Dashboard en vivo expuesto vía WebSocket."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from horizonte.core import telemetry

logger = logging.getLogger("horizonte.governance.live")


TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
COGNITION_TEMPLATE = Path(__file__).parent / "cognition.html"

router = APIRouter(tags=["dashboard-live"])

POLL_INTERVAL = 5


@router.get("/live", response_class=HTMLResponse)
async def live_page(request: Request) -> HTMLResponse:
    """Renderiza el dashboard de métricas en vivo."""

    return templates.TemplateResponse("live.html", {"request": request})


@router.get("/cognition", response_class=HTMLResponse)
async def cognition_page() -> HTMLResponse:
    """Entrega el dashboard de autoevaluación cognitiva."""

    return HTMLResponse(COGNITION_TEMPLATE.read_text(encoding="utf-8"))


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


__all__ = ["router", "metrics_stream"]
