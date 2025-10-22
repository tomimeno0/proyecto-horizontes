from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from governance.dashboard.main import metrics_manager
from horizonte.common.db import Base, engine, get_session
from horizonte.common.security import hash_text_sha256
from horizonte.core.metacognition import CognitiveMirror, set_cognitive_mirror
from horizonte.core.security_monitor import SecurityMonitor, set_security_monitor
from horizonte.core.telemetry import telemetry
from horizonte.core.trace_logger import make_hash, persist_ledger
from horizonte.governance import audit_engine
from horizonte.governance.audit_engine import audit_snapshot


@pytest.fixture(autouse=True)
def reset_environment(tmp_path: Path) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    metrics_manager.reset()
    telemetry.reset()
    mirror = CognitiveMirror(log_path=tmp_path / "cognitive_log.json")
    set_cognitive_mirror(mirror)
    yield
    set_cognitive_mirror(None)
    set_security_monitor(None)
    Base.metadata.drop_all(bind=engine)


def _seed_ledger() -> None:
    with get_session() as session:
        ts = datetime.now(timezone.utc)
        records = [("consulta alfa", "respuesta 1"), ("consulta beta", "respuesta 2")]
        for query, response in records:
            hash_value = make_hash(query, response, ts)
            persist_ledger(session, query, response, hash_value, ts)


def test_audit_snapshot_generates_signed_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit_path = tmp_path / "audit_report.json"
    monkeypatch.setattr(audit_engine, "AUDIT_REPORT_PATH", audit_path)
    code_root = tmp_path / "code"
    code_root.mkdir()
    (code_root / "module.py").write_text("print('ok')\n", encoding="utf-8")

    _seed_ledger()

    monitor = SecurityMonitor(
        code_root=code_root,
        audit_path=audit_path,
        ledger_provider=lambda: "ledger-baseline",
    )
    set_security_monitor(monitor)

    report = audit_snapshot(limit_inferencias=5)

    assert audit_path.exists()
    stored = json.loads(audit_path.read_text(encoding="utf-8"))
    assert stored["signature"] == report["signature"]

    expected_signature = hash_text_sha256(
        json.dumps(report["snapshot"], sort_keys=True, ensure_ascii=False, default=str)
    )
    assert report["signature"] == expected_signature
    assert len(report["snapshot"]["inferences"]) == 2
