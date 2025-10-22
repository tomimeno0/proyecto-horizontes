"""Router para exponer métricas internas del sistema."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from horizonte.core.telemetry import get_metrics

router = APIRouter(tags=["metrics-internas"])

_templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/json")
async def metrics_json() -> dict[str, float | int | dict[str, object]]:
    """Retorna las métricas internas en formato JSON."""
    return get_metrics()


@router.get("/html", response_class=HTMLResponse)
async def metrics_html(request: Request) -> HTMLResponse:
    """Renderiza un tablero HTML con las métricas actuales."""
    metrics = get_metrics()
    context = {"request": request, **metrics}
    return templates.TemplateResponse("metrics.html", context)
