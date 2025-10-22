"""Router de métricas internas para el dashboard de Horizonte."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from horizonte.core import telemetry

router = APIRouter()
templates = Jinja2Templates(directory="horizonte/governance/dashboard/templates")


@router.get("/json", response_class=JSONResponse)
async def get_metrics_json() -> JSONResponse:
    """Devuelve las métricas en formato JSON."""

    return JSONResponse(content=telemetry.get_metrics())


@router.get("/html", response_class=HTMLResponse)
async def get_metrics_html(request: Request) -> HTMLResponse:
    """Renderiza el dashboard HTML con métricas en tiempo real."""

    context = {"request": request, **telemetry.get_metrics()}
    return templates.TemplateResponse("metrics.html", context)


__all__ = ["router"]
