"""Pruebas unitarias para el módulo de metacognición."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from horizonte.core.metacognition import CognitiveMirror, set_cognitive_mirror


@dataclass
class DummyLedger:
    query: str
    response: str


def crear_mirror(tmp_path: Path, registros: list[DummyLedger]) -> CognitiveMirror:
    mirror = CognitiveMirror(
        log_path=tmp_path / "cognitive.json",
        subinstances=2,
        inference_fn=lambda query: "respuesta base",
        ledger_provider=lambda limit: registros[-limit:],
    )
    set_cognitive_mirror(mirror)
    return mirror


def test_divergence_index_calculation(tmp_path: Path) -> None:
    registros: list[DummyLedger] = []
    mirror = crear_mirror(
        tmp_path,
        registros,
    )
    mirror._subgenerator = lambda query, base, count: [
        base,
        "respuesta alternativa divergente",
    ]

    resultado = mirror.evaluate("consulta alfa", "respuesta base")

    assert resultado["divergence_index"] > 0.3
    history = mirror.history()
    assert history and history[-1]["type"] == "evaluation"
    assert any("candidates" in entry for entry in history)
    set_cognitive_mirror(None)


def test_majority_reasoning_for_high_divergence(tmp_path: Path) -> None:
    registros: list[DummyLedger] = []
    mirror = crear_mirror(tmp_path, registros)
    mirror._subgenerator = lambda query, base, count: [
        "hipotesis alternativa",  # mayoría divergente
        "hipotesis alternativa",
    ]

    resultado = mirror.evaluate("consulta beta", "respuesta base")

    assert resultado["strategy"] == "majority"
    assert resultado["response"] == "hipotesis alternativa"
    set_cognitive_mirror(None)


def test_analyze_self_returns_consistency_score(tmp_path: Path) -> None:
    registros = [
        DummyLedger(query="q1", response="respuesta-1"),
        DummyLedger(query="q1", response="respuesta-1"),
        DummyLedger(query="q2", response="otra"),
    ]
    mirror = crear_mirror(tmp_path, registros)

    resultado = mirror.analyze_self(limit=10)

    assert 0.0 <= resultado["consistency_score"] <= 1.0
    assert resultado["type"] == "analysis"
    snapshot = mirror.status()
    assert snapshot.global_consistency == resultado["consistency_score"]

    set_cognitive_mirror(None)
