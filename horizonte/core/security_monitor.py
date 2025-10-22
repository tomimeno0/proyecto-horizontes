"""Monitoreo de seguridad e integridad para el núcleo de Horizonte."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from horizonte.common.config import Settings, get_settings
from horizonte.common.db import Ledger, get_session
from horizonte.common.security import hash_text_sha256

LedgerDigestProvider = Callable[[], str]


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_directory(path: Path) -> str:
    digests: list[str] = []
    for file_path in sorted(path.rglob("*.py")):
        if not file_path.is_file():
            continue
        try:
            digests.append(_hash_bytes(file_path.read_bytes()))
        except OSError:
            continue
    payload = "".join(digests) or "empty"
    return hash_text_sha256(payload)


def _hash_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return _hash_bytes(path.read_bytes())
    except OSError:
        return None


@dataclass(slots=True)
class SecurityIncident:
    component: str
    expected: str | None
    observed: str | None


class SecurityMonitor:
    """Detecta modificaciones no autorizadas y expone alertas auditables."""

    def __init__(
        self,
        *,
        code_root: Path | None = None,
        audit_path: Path | None = None,
        ledger_provider: LedgerDigestProvider | None = None,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
        alert_history_limit: int = 200,
    ) -> None:
        self.code_root = (code_root or Path(__file__).resolve().parents[1]).resolve()
        self.audit_path = (
            audit_path or self.code_root.parent / "governance" / "audit_report.json"
        ).resolve()
        self._ledger_provider = ledger_provider or self._ledger_digest
        self.settings = settings or get_settings()
        self.logger = logger or logging.getLogger("horizonte.security.monitor")
        self._alerts: deque[dict[str, object]] = deque(maxlen=alert_history_limit)
        self._baseline = self._compute_state()
        self._last_result: dict[str, object] | None = None

    def _ledger_digest(self) -> str:
        with get_session() as session:
            hashes: Iterable[str] = (
                session.execute(select(Ledger.hash).order_by(Ledger.id)).scalars().all()
            )
        flattened = "".join(hashes)
        return hash_text_sha256(flattened)

    def _compute_state(self) -> dict[str, str | None]:
        code_hash = _hash_directory(self.code_root)
        ledger_hash = self._ledger_provider()
        audit_hash = _hash_file(Path(self.audit_path))
        return {
            "code": code_hash,
            "ledger": ledger_hash,
            "audit_report": audit_hash,
        }

    def check_integrity(self, *, record_alert: bool = True) -> dict[str, object]:
        current = self._compute_state()
        incidents: list[SecurityIncident] = []
        for component, expected in self._baseline.items():
            observed = current.get(component)
            if expected != observed:
                incidents.append(
                    SecurityIncident(component=component, expected=expected, observed=observed)
                )
        incidents_payload = [asdict(incident) for incident in incidents]
        result: dict[str, object] = {
            "baseline": self._baseline.copy(),
            "current": current,
            "incidents": incidents_payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._last_result = result
        if incidents and record_alert:
            payload: dict[str, object] = {
                "timestamp": result["timestamp"],
                "incidents": incidents_payload,
            }
            if not self._alerts or self._alerts[-1]["incidents"] != payload["incidents"]:
                self._alerts.append(payload)
            self.logger.warning(
                "security_incident_detected", extra={"incidents": payload["incidents"]}
            )
        return result

    def get_alerts(self) -> list[dict[str, object]]:
        return list(self._alerts)

    def register_correction(self, *, approved_by: str | None = None) -> None:
        if self.settings.env == "prod" and not approved_by:
            raise PermissionError("Las correcciones en producción requieren aprobación humana")
        self.logger.info(
            "security_baseline_updated", extra={"approved_by": approved_by or "system"}
        )
        self._baseline = self._compute_state()

    def status(self) -> dict[str, object]:
        if self._last_result is None:
            return self.check_integrity(record_alert=False)
        return self._last_result


_MONITOR: SecurityMonitor | None = None


def get_security_monitor() -> SecurityMonitor:
    global _MONITOR
    if _MONITOR is None:
        _MONITOR = SecurityMonitor()
    return _MONITOR


def set_security_monitor(monitor: SecurityMonitor | None) -> None:
    global _MONITOR
    _MONITOR = monitor


__all__ = ["SecurityMonitor", "get_security_monitor", "set_security_monitor"]
