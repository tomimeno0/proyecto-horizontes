"""Pruebas para los endpoints de cognición."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from horizonte.api.routes import cognition
from horizonte.core.metacognition import CognitiveMirror, set_cognitive_mirror


@dataclass
class DummyLedger:
    query: str
    response: str


def configurar_mirror(tmp_path: Path) -> CognitiveMirror:
    registros = [
        DummyLedger(query="q1", response="respuesta base"),
        DummyLedger(query="q1", response="respuesta base"),
    ]
    mirror = CognitiveMirror(
        log_path=tmp_path / "mirror.json",
        ledger_provider=lambda limit: registros[-limit:],
        subinstances=1,
    )
    set_cognitive_mirror(mirror)
    mirror.evaluate("consulta inicial", "respuesta base")
    return mirror


def test_cognition_endpoints_expose_state(tmp_path: Path) -> None:
    configurar_mirror(tmp_path)

    app = FastAPI()
    app.include_router(cognition.router)
    client = TestClient(app)

    status = client.get("/cognition/status")
    assert status.status_code == 200
    payload = status.json()
    assert {
        "divergence_index",
        "global_consistency",
        "collective_consistency",
        "cycles",
        "last_audit",
    } <= payload.keys()

    history = client.get("/cognition/history")
    assert history.status_code == 200
    assert history.json()

    recheck = client.post("/cognition/recheck", params={"limit": 10})
    assert recheck.status_code == 200
    assert "consistency_score" in recheck.json()

    reset = client.delete("/cognition/reset")
    assert reset.status_code == 200
    assert client.get("/cognition/history").json() == []

    set_cognitive_mirror(None)
