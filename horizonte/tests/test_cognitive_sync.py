"""Validaciones del servicio de sincronización cognitiva."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from horizonte.core.metacognition import CognitiveMirror, set_cognitive_mirror
from horizonte.net.cognitive_sync import CognitiveSync


@dataclass
class DummyLedger:
    query: str
    response: str


@pytest.mark.anyio
async def test_sync_cycle_generates_collective_score(tmp_path: Path) -> None:
    registros = [
        DummyLedger(query="q1", response="alpha"),
        DummyLedger(query="q1", response="alpha"),
        DummyLedger(query="q2", response="beta"),
    ]
    mirror = CognitiveMirror(
        log_path=tmp_path / "mirror.json",
        ledger_provider=lambda limit: registros[-limit:],
        subinstances=1,
    )
    set_cognitive_mirror(mirror)

    def peers(limit: int) -> list[tuple[str, float]]:
        data = [("node-b", 0.3), ("node-c", 0.2), ("node-d", 0.4)]
        return data[:limit]

    sync = CognitiveSync(
        node_id="node-a",
        log_path=tmp_path / "sync.json",
        interval_seconds=0.1,
        sample_size=3,
        peer_fetcher=peers,
    )

    outcome = await sync.execute_cycle()

    assert outcome.action_taken == "resync"
    assert outcome.collective_score < 0.7
    assert sync.log_path.exists()
    log = sync.log_path.read_text(encoding="utf-8")
    assert "collective_score" in log
    snapshot = mirror.status()
    assert snapshot.collective_consistency == outcome.collective_score

    set_cognitive_mirror(None)
