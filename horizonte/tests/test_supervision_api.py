from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from governance.dashboard.main import metrics_manager
from horizonte.api.routes import supervision as supervision_module
from horizonte.api.routes.supervision import router
from horizonte.common.db import Base, engine, get_session
from horizonte.core.metacognition import CognitiveMirror, set_cognitive_mirror
from horizonte.core.security_monitor import SecurityMonitor, set_security_monitor
from horizonte.core.telemetry import telemetry
from horizonte.core.trace_logger import make_hash, persist_ledger
from horizonte.governance import audit_engine
from horizonte.net import consensus_manager as consensus_module
from horizonte.net.consensus_manager import ConsensusManager
from horizonte.net.node_registry import get_registry


@pytest.fixture(autouse=True)
def reset_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    telemetry.reset()
    metrics_manager.reset()
    get_registry().clear()
    mirror = CognitiveMirror(log_path=tmp_path / "cognitive_log.json")
    set_cognitive_mirror(mirror)

    history_path = tmp_path / "consensus_history.json"
    manager = ConsensusManager(history_path=history_path)
    manager._history.append(  # type: ignore[attr-defined]
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": "abc123",
            "approved": True,
            "validators": ["n1"],
            "failed": [],
            "mode": "autonomous",
            "sync_score": 0.99,
        }
    )
    monkeypatch.setattr(consensus_module, "_MANAGER", manager)

    yield

    set_cognitive_mirror(None)
    set_security_monitor(None)
    get_registry().clear()
    Base.metadata.drop_all(bind=engine)


def _seed_data() -> None:
    with get_session() as session:
        ts = datetime.now(timezone.utc)
        data = [
            ("consulta A", "respuesta"),
            ("consulta B", "respuesta"),
            ("consulta C", "respuesta"),
        ]
        for query, response in data:
            hash_value = make_hash(query, response, ts)
            persist_ledger(session, query, response, hash_value, ts)


def test_supervision_routes_generate_and_return_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit_path = tmp_path / "audit_report.json"
    monkeypatch.setattr(audit_engine, "AUDIT_REPORT_PATH", audit_path)
    monkeypatch.setattr(supervision_module, "AUDIT_REPORT_PATH", audit_path)

    code_root = tmp_path / "code"
    code_root.mkdir()
    (code_root / "module.py").write_text("print('ok')\n", encoding="utf-8")

    _seed_data()

    monitor = SecurityMonitor(
        code_root=code_root,
        audit_path=audit_path,
        ledger_provider=lambda: "ledger-baseline",
    )
    set_security_monitor(monitor)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post("/audit/generate")
    assert response.status_code == 201
    payload = response.json()
    assert "signature" in payload

    status_response = client.get("/supervision/status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["latest_report"]["signature"] == payload["signature"]

    report_response = client.get("/audit/report")
    assert report_response.status_code == 200
    assert report_response.json()["signature"] == payload["signature"]
