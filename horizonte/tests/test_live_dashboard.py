"""Pruebas del dashboard en vivo vía WebSocket."""

from __future__ import annotations

from fastapi.testclient import TestClient

from horizonte.api.main import app
from horizonte.core import telemetry


def setup_function() -> None:  # pragma: no cover - usado por pytest
    telemetry.telemetry.reset()


def test_live_dashboard_websocket() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/metrics") as websocket:
            message = websocket.receive_json()
            assert "inferencias_totales" in message

        response = client.get("/dashboard/live")
        assert response.status_code == 200
        assert "Monitoreo en vivo" in response.text

