"""Pruebas del módulo de metacognición."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from horizonte.common.db import Base, Ledger, engine, get_session
from horizonte.core.metacognition import CognitiveMirror


@pytest.fixture(autouse=True)
def limpiar_ledger() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_divergence_index_y_majority(tmp_path: Path) -> None:
    """El espejo cognitivo calcula divergencia y mayoría correctamente."""

    log_path = tmp_path / "cognitive_log.json"
    mirror = CognitiveMirror(
        inference_func=lambda q: f"respuesta:{q}",
        log_path=log_path,
        subcognition_factories=[
            lambda q: "alpha",
            lambda q: "beta",
            lambda q: "alpha",
        ],
        divergence_threshold=0.4,
    )
    resultado = mirror.evaluate("consulta de prueba")
    assert resultado["final_response"] == "alpha"
    assert pytest.approx(0.5, rel=1e-3) == resultado["divergence_index"]
    historia = mirror.history()
    assert historia[-1]["reevaluated"] is True
    assert log_path.exists()


def test_analyze_self_calcula_consistencia(tmp_path: Path) -> None:
    """La autoevaluación analiza el ledger y devuelve consistencia global."""

    log_path = tmp_path / "cognitive_log.json"
    mirror = CognitiveMirror(inference_func=lambda q: "respuesta", log_path=log_path)
    ahora = datetime.now(timezone.utc).isoformat()
    with get_session() as session:
        session.add_all(
            [
                Ledger(query="Q1", response="R1", hash="h1", timestamp=ahora),
                Ledger(query="Q1", response="R1", hash="h2", timestamp=ahora),
                Ledger(query="Q1", response="R2", hash="h3", timestamp=ahora),
                Ledger(query="Q2", response="R3", hash="h4", timestamp=ahora),
            ]
        )
    score = mirror.analyze_self(sample_size=10)
    assert pytest.approx(0.75, rel=1e-3) == score
    snapshot = mirror.snapshot()
    assert snapshot.consistency_score == score
    assert snapshot.auto_eval_cycles == 1
    history = mirror.history()
    assert any(item["type"] == "self_check" for item in history)
    mirror.reset_logs()
    assert mirror.history() == []
