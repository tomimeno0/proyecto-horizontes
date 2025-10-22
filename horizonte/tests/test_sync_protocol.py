from __future__ import annotations

import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl
from typing import cast

from horizonte.net.node_manager import NodeManager
from horizonte.net.node_registry import NodePayload, get_registry
from horizonte.net import sync_protocol
from horizonte.net.sync_protocol import SyncProtocol, SyncUpdateRequest, configure_sync, router


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = get_registry()
    registry.clear()
    monkeypatch.setattr(sync_protocol, "_PROTOCOL", None)
    yield
    registry.clear()
    monkeypatch.setattr(sync_protocol, "_PROTOCOL", None)


@pytest.mark.anyio
async def test_sync_protocol_detects_divergence() -> None:
    registry = get_registry()
    registry.register(
        NodePayload(
            node_id="peer-sync",
            address=cast(AnyHttpUrl, "http://peer-sync.local"),
            status="active",
        )
    )
    manager = NodeManager()
    protocol = SyncProtocol(manager, registry=registry)
    await protocol.update_local_ledger(["hash-a", "hash-b", "hash-c"])

    payload = SyncUpdateRequest(peer_id="peer-sync", hashes=["hash-b", "hash-c", "hash-d"])
    result = await protocol.process_update(payload)

    assert "hash-d" in result["missing"]
    peer = registry.get("peer-sync")
    assert peer is not None
    assert pytest.approx(peer.sync_score or 0.0, rel=1e-3) == 2 / 3
    status = await protocol.get_status()
    assert status.ledger_size == 2  # hash-d dropped locally
    assert status.history


def test_sync_protocol_router_endpoints() -> None:
    registry = get_registry()
    registry.register(
        NodePayload(
            node_id="peer-router",
            address=cast(AnyHttpUrl, "http://peer-router.local"),
            status="active",
        )
    )
    manager = NodeManager()
    protocol = configure_sync(manager)

    async def prepare() -> None:
        await protocol.update_local_ledger(["ledger-1"])

    anyio.run(prepare)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/sync/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ledger_size"] == 1

    response = client.post(
        "/sync/update",
        json={
            "peer_id": "peer-router",
            "hashes": ["ledger-1", "ledger-2"],
            "records": ["ledger-2"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "ledger-2" in data["missing"] or "ledger-2" in data.get("added", [])
