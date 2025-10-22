"""Pruebas del dashboard público de transparencia."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from governance.dashboard.main import metrics_manager, router
from net.node_registry import NodePayload, get_registry


def setup_function() -> None:
    """Resetea el estado compartido antes de cada caso."""

    metrics_manager.reset()
    get_registry().clear()


def test_dashboard_renderiza_metricas() -> None:
    """El dashboard debe incluir las métricas clave en el HTML."""

    metrics_manager.record_inference("consulta alfa", {"allowed": True})
    metrics_manager.record_inference("consulta beta", {"allowed": False})
    metrics_manager.register_consensus("hash-final")
    get_registry().register(
        NodePayload(
            node_id="validator-1",
            address="http://validator1.example.com",
            status="activo",
        )
    )

    app = FastAPI()
    app.mount("/dashboard", router)
    client = TestClient(app)

    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    contenido = response.text
    assert "Proyecto Horizonte — Dashboard Público" in contenido
    assert "Inferencias totales" in contenido
    assert "Nodos activos" in contenido
    assert "Último hash validado" in contenido
    assert "Índice de ética" in contenido
