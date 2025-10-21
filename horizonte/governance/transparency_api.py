"""API de transparencia para el proyecto Horizonte."""

from __future__ import annotations

from random import random
from typing import Dict

from fastapi import APIRouter


class TransparencyService:
    """Servicio que expone métricas públicas de transparencia."""

    def metrics(self) -> Dict[str, float | str]:
        """Entrega métricas simuladas listas para ser auditadas."""
        bias_index = round(0.2 + random() * 0.1, 3)
        return {
            "bias_index": bias_index,
            "transparency_score": 0.82,
            "ethics_panel_status": "operativo",
        }


def get_router() -> APIRouter:
    """Crea el router con el endpoint de transparencia."""
    service = TransparencyService()
    router = APIRouter(prefix="", tags=["transparencia"])

    @router.get("/transparencia")
    async def obtener_transparencia() -> Dict[str, float | str]:
        return service.metrics()

    return router
