from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable, cast

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl

from horizonte.net.heartbeat import HeartbeatService, build_signature, router as heartbeat_router
from horizonte.net.node_manager import NodeManager
from horizonte.net.node_registry import NodePayload, get_registry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    registry = get_registry()
    registry.clear()
    yield
    registry.clear()


@pytest.mark.anyio
async def test_heartbeat_service_updates_latency() -> None:
    registry = get_registry()
    manager = NodeManager()
    manager.register_self(cast(AnyHttpUrl, "http://self.local"))
    registry.register(
        NodePayload(
            node_id="peer-1",
            address=cast(AnyHttpUrl, "http://peer1.local"),
            status="active",
        )
    )

    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        payload = json.loads(request.content.decode())
        timestamp = datetime.fromisoformat(payload["timestamp"])  # type: ignore[arg-type]
        assert payload["signature"] == build_signature(payload["node_id"], timestamp)
        return httpx.Response(200, json={"status": "ack"})

    factory: Callable[[], httpx.AsyncClient] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    service = HeartbeatService(manager, client_factory=factory)
    await service.send_cycle()

    assert len(calls) == 1
    node = registry.get("peer-1")
    assert node is not None
    assert node.last_activity is not None
    assert node.avg_latency_ms is not None


@pytest.mark.anyio
async def test_heartbeat_marks_node_unreachable_after_failures() -> None:
    registry = get_registry()
    manager = NodeManager()
    manager.register_self(cast(AnyHttpUrl, "http://self.local"))
    registry.register(
        NodePayload(
            node_id="peer-timeout",
            address=cast(AnyHttpUrl, "http://peer-timeout.local"),
            status="active",
        )
    )

    async def failing_handler(_: httpx.Request) -> httpx.Response:  # pragma: no cover - auxiliar
        raise httpx.ConnectError("offline")

    factory = lambda: httpx.AsyncClient(transport=httpx.MockTransport(failing_handler))
    service = HeartbeatService(manager, client_factory=factory)

    for _ in range(3):
        await service.send_cycle()

    node = registry.get("peer-timeout")
    assert node is not None
    assert node.status == "unreachable"


def test_receive_heartbeat_endpoint_records_activity() -> None:
    registry = get_registry()
    registry.register(
        NodePayload(
            node_id="peer-api",
            address=cast(AnyHttpUrl, "http://peer-api.local"),
            status="active",
        )
    )
    app = FastAPI()
    app.include_router(heartbeat_router, prefix="/nodes")
    client = TestClient(app)

    timestamp = datetime.now(timezone.utc)
    payload = {
        "node_id": "peer-api",
        "timestamp": timestamp.isoformat(),
        "signature": build_signature("peer-api", timestamp),
    }

    response = client.post("/nodes/heartbeat", json=payload)
    assert response.status_code == 200
    node = registry.get("peer-api")
    assert node is not None
    assert node.last_activity is not None
