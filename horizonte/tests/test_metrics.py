"""Validaciones del router de métricas internas."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from governance.dashboard import metrics as metrics_router
from horizonte.core.telemetry import telemetry


def test_metrics_json_expone_claves_basicas() -> None:
    telemetry.reset()
    app = FastAPI()
    app.include_router(metrics_router.router, prefix="/metrics")
    client = TestClient(app)

    response = client.get("/metrics/json")

    assert response.status_code == 200
    data = response.json()
    assert {
        "inferencias_totales",
        "promedio_latencia_ms",
        "respuestas_ethics_denegadas",
        "consultas_por_minuto",
    } <= data.keys()
