from __future__ import annotations

from typing import cast

import pytest
from pydantic import AnyHttpUrl

from horizonte.governance import vote_system
from horizonte.governance.auto_governor import AutoGovernor
from horizonte.net.node_manager import NodeManager
from horizonte.net.node_registry import NodePayload, get_registry


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    vote_system.reset_system()
    registry = get_registry()
    registry.clear()
    yield
    vote_system.reset_system()
    registry.clear()


@pytest.mark.anyio
async def test_auto_governor_creates_system_proposals(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = get_registry()
    registry.register(
        NodePayload(
            node_id="node-1",
            address=cast(AnyHttpUrl, "http://node1.local"),
            status="active",
        )
    )
    registry.set_reliability("node-1", 1.5)

    def fake_metrics() -> dict[str, object]:
        return {
            "ethics_adaptive": {
                "bias_index": 0.45,
                "precision": 0.62,
            }
        }

    monkeypatch.setattr(
        "horizonte.governance.auto_governor.get_metrics", fake_metrics
    )

    governor = AutoGovernor(interval=0.1, registry=registry, node_manager=NodeManager())

    actions = await governor.evaluate_once()
    assert len(actions) == 2

    proposals = vote_system.get_results()
    assert len(proposals) == 2
    for proposal in proposals:
        assert proposal.system is True
        assert "system" in proposal.tags
        assert proposal.votes_for >= 1.5

    # Repetir con las mismas métricas no genera nuevas propuestas
    actions = await governor.evaluate_once()
    assert not actions

    # Métricas normalizadas eliminan los flags activos
    def stable_metrics() -> dict[str, object]:
        return {
            "ethics_adaptive": {
                "bias_index": 0.1,
                "precision": 0.95,
            }
        }

    monkeypatch.setattr(
        "horizonte.governance.auto_governor.get_metrics", stable_metrics
    )
    actions = await governor.evaluate_once()
    assert not actions
