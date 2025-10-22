"""Pruebas para la sincronización cognitiva distribuida."""

from __future__ import annotations

from pathlib import Path

from horizonte.common.db import Base, engine
from horizonte.core.metacognition import CognitiveMirror
from horizonte.net.cognitive_sync import CognitiveSyncManager


def test_ciclo_distribuido_registra_resync(tmp_path: Path) -> None:
    """El gestor registra la sincronización y solicita resync si es necesario."""

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    mirror = CognitiveMirror(
        inference_func=lambda q: "respuesta", log_path=tmp_path / "cognitive_log.json"
    )
    manager = CognitiveSyncManager(
        node_id="nodo-test",
        mirror=mirror,
        peer_score_provider=lambda count: [0.2, 0.3, 0.4],
        log_path=tmp_path / "sync_log.json",
        threshold=0.7,
    )
    status = manager.run_cycle()
    assert status.collective_score < 0.7
    assert status.action_taken == "resync"
    history = manager.history()
    assert history
    assert history[-1]["action_taken"] == "resync"
