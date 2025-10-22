"""Pruebas del consenso asíncrono con latencia simulada."""

from __future__ import annotations

import anyio
import pytest

from horizonte.net import sim_net
from horizonte.net.consensus_manager import broadcast_result_async
from horizonte.net.node_registry import NodePayload, get_registry


@pytest.mark.anyio
async def test_broadcast_result_async(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = get_registry()
    registry.clear()
    registry.register(NodePayload(node_id="origin", address="http://origin.local"))
    registry.register(NodePayload(node_id="node-1", address="http://node1.local"))
    registry.register(NodePayload(node_id="node-2", address="http://node2.local"))
    registry.register(NodePayload(node_id="node-3", address="http://node3.local"))

    async def fake_call(address: str, payload: dict[str, str]) -> bool:
        await anyio.sleep(0.01)
        return True

    monkeypatch.setattr(sim_net, "simulate_call", fake_call)

    result = await broadcast_result_async("origin", "hash-123")
    assert result["approved"] is True
    assert set(result["validators"]) == {"node-1", "node-2", "node-3"}
    assert result["failed"] == []

