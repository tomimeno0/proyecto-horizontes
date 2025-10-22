from __future__ import annotations

from pathlib import Path

import pytest

from horizonte.common.config import Settings
from horizonte.core.security_monitor import SecurityMonitor


def test_security_monitor_detects_code_changes(tmp_path: Path) -> None:
    code_root = tmp_path / "code"
    code_root.mkdir()
    script = code_root / "module.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    audit_path = tmp_path / "audit_report.json"
    audit_path.write_text("{}", encoding="utf-8")

    monitor = SecurityMonitor(
        code_root=code_root,
        audit_path=audit_path,
        ledger_provider=lambda: "baseline",  # simplifica el digest del ledger para la prueba
        settings=Settings(),
    )

    initial = monitor.check_integrity()
    assert initial["incidents"] == []

    script.write_text("print('alterado')\n", encoding="utf-8")
    result = monitor.check_integrity()
    assert result["incidents"]
    assert any(incident["component"] == "code" for incident in result["incidents"])
    assert monitor.get_alerts(), "La modificación debe generar alertas registradas"

    monitor.register_correction(approved_by="operador humano")
    refreshed = monitor.check_integrity(record_alert=False)
    assert refreshed["incidents"] == []


def test_security_monitor_requires_human_approval_in_prod(tmp_path: Path) -> None:
    code_root = tmp_path / "code"
    code_root.mkdir()
    audit_path = tmp_path / "audit_report.json"

    monitor = SecurityMonitor(
        code_root=code_root,
        audit_path=audit_path,
        ledger_provider=lambda: "baseline",
        settings=Settings(ENV="prod"),
    )

    with pytest.raises(PermissionError):
        monitor.register_correction()

    monitor.register_correction(approved_by="comite")
