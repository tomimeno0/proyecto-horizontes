"""Pruebas para las métricas expuestas por la API."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from horizonte.api.main import app
from horizonte.core import telemetry


@pytest.mark.anyio
async def test_metrics_json_endpoint(monkeypatch) -> None:
    """El endpoint JSON debe exponer las métricas básicas."""

    monkeypatch.setattr(telemetry, "_COLLECTOR", telemetry.TelemetryCollector())
    telemetry.record_inference(120.0, ethics_denied=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics/json")

    assert response.status_code == 200
    payload = response.json()
    assert {
        "inferencias_totales",
        "consultas_por_minuto",
        "respuestas_ethics_denegadas",
        "promedio_latencia_ms",
    } <= payload.keys()
    assert payload["inferencias_totales"] == 1
    assert payload["respuestas_ethics_denegadas"] == 1
