from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl

from governance.dashboard.main import router as dashboard_router
from horizonte.governance.dashboard.live import router as live_router
from horizonte.net.consensus_manager import get_consensus_manager
from horizonte.net.node_registry import NodePayload, get_registry


def setup_function() -> None:
    registry = get_registry()
    registry.clear()
    manager = get_consensus_manager()
    manager.failure_streak = 0
    manager.mode = "autonomous"


def test_network_dashboard_renders() -> None:
    registry = get_registry()
    registry.register(
        NodePayload(
            node_id="node-dashboard",
            address=cast(AnyHttpUrl, "http://node-dashboard.local"),
            status="active",
        )
    )
    registry.record_heartbeat(
        "node-dashboard", latency_ms=42.0, timestamp=datetime.now(timezone.utc)
    )
    registry.update_sync_score("node-dashboard", 0.91)

    manager = get_consensus_manager()
    manager.failure_streak = 2
    manager.mode = "autonomous"

    app = FastAPI()
    app.include_router(live_router)
    app.include_router(live_router, prefix="/dashboard")
    app.mount("/dashboard", dashboard_router)
    client = TestClient(app)

    response = client.get("/dashboard/network")
    assert response.status_code == 200
    content = response.text
    assert "Mapa de Red" in content
    assert "Sync score" in content
    assert "node-dashboard" in content

    with client.websocket_connect("/dashboard/ws/network") as websocket:
        payload = websocket.receive_json()
        assert payload["nodes"][0]["node_id"] == "node-dashboard"
        assert payload["consensus"]["failures"] == 2
