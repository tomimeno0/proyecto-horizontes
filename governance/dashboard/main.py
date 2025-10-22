"""Aplicación web pública de métricas para Horizonte."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from threading import RLock
from typing import Dict, List, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from net.node_registry import get_registry


class DashboardMetrics:
    """Acumula métricas públicas generadas por la plataforma."""

    def __init__(self) -> None:
        self._total = 0
        self._allowed = 0
        self._queries: Counter[str] = Counter()
        self._last_hash: str | None = None
        self._lock = RLock()

    def record_inference(self, query: str, ethics: Dict[str, object]) -> None:
        """Registra una inferencia para efectos estadísticos."""

        permitido = bool(ethics.get("allowed", False))
        with self._lock:
            self._total += 1
            if permitido:
                self._allowed += 1
            self._queries[query] += 1

    def register_consensus(self, hash_value: str) -> None:
        """Actualiza el último hash aprobado por consenso."""

        with self._lock:
            self._last_hash = hash_value

    def snapshot(self) -> Dict[str, object]:
        """Genera una vista inmutable con los valores actuales."""

        with self._lock:
            total = self._total
            allowed = self._allowed
            last_hash = self._last_hash
            top_queries: List[Tuple[str, int]] = self._queries.most_common(5)
        ethic_score = 0.0 if total == 0 else round((allowed / total) * 100, 2)
        return {
            "total": total,
            "ethic_score": ethic_score,
            "top_queries": top_queries,
            "last_hash": last_hash,
        }

    def reset(self) -> None:
        """Reinicia las métricas acumuladas (uso de pruebas)."""

        with self._lock:
            self._total = 0
            self._allowed = 0
            self._queries.clear()
            self._last_hash = None


metrics_manager = DashboardMetrics()

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

router = FastAPI(title="Horizonte Dashboard", docs_url=None, redoc_url=None)
router.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="dashboard-static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request) -> HTMLResponse:
    """Renderiza el dashboard con los indicadores consolidados."""

    snapshot = metrics_manager.snapshot()
    nodos_activos = get_registry().count_active()
    context = {
        "request": request,
        "total": snapshot["total"],
        "nodos": nodos_activos,
        "last_hash": snapshot["last_hash"] or "N/A",
        "ethic_score": f"{snapshot['ethic_score']:.2f}",
        "top_queries": snapshot["top_queries"],
    }
    return templates.TemplateResponse("index.html", context)
