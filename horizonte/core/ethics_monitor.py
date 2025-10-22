"""Supervisión periódica de métricas éticas adaptativas."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from .adaptive_learning import AdaptiveTrainer, get_adaptive_trainer

_AUDIT_FILENAME = "ethics_audit.json"
_DEFAULT_AUDIT_PATH = Path(__file__).resolve().parent / _AUDIT_FILENAME


class EthicsMonitor:
    """Tarea periódica que vigila la salud ética del sistema."""

    def __init__(
        self,
        trainer: AdaptiveTrainer | None = None,
        audit_path: Path | None = None,
        max_snapshots: int = 500,
    ) -> None:
        self._trainer = trainer or get_adaptive_trainer()
        self.audit_path = audit_path or _DEFAULT_AUDIT_PATH
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self._max_snapshots = max_snapshots
        self._lock = Lock()
        if not self.audit_path.exists():
            self.audit_path.write_text("[]", encoding="utf-8")

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def _read_snapshots(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.audit_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[-self._max_snapshots :]
        except json.JSONDecodeError:
            pass
        return []

    def _write_snapshots(self, snapshots: Iterable[dict[str, Any]]) -> None:
        data = list(snapshots)[-self._max_snapshots :]
        self.audit_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Monitorización
    # ------------------------------------------------------------------
    async def poll(self) -> dict[str, Any]:
        """Ejecuta una iteración de supervisión y guarda un snapshot."""

        metrics = self._trainer.export_metrics()
        precision = float(metrics.get("precision", 1.0))
        alert = None
        if precision < 0.75:
            alert = "degradacion_moral"
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "alert": alert,
        }
        with self._lock:
            registros = self._read_snapshots()
            registros.append(snapshot)
            self._write_snapshots(registros)
        from horizonte.core.metacognition import get_cognitive_mirror

        get_cognitive_mirror().register_event("ethics_monitor", snapshot)
        return snapshot

    async def run(self, interval: float = 60.0, stop_event: asyncio.Event | None = None) -> None:
        """Ciclo continuo de monitorización."""

        while True:
            await self.poll()
            if stop_event and stop_event.is_set():
                break
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Consulta externa
    # ------------------------------------------------------------------
    def get_audit_logs(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Devuelve los registros más recientes del archivo de auditoría."""

        with self._lock:
            logs = self._read_snapshots()
        if limit is not None:
            return logs[-limit:]
        return logs

    def reset_audit(self) -> None:
        """Limpia el archivo de auditoría (uso para entornos de prueba/desarrollo)."""

        with self._lock:
            self._write_snapshots([])


_MONITOR: EthicsMonitor | None = None


def get_ethics_monitor() -> EthicsMonitor:
    """Obtiene un monitor global reutilizable."""

    global _MONITOR
    if _MONITOR is None:
        _MONITOR = EthicsMonitor()
    return _MONITOR


def set_ethics_monitor(monitor: EthicsMonitor | None) -> None:
    """Reemplaza el monitor global (principalmente para pruebas)."""

    global _MONITOR
    _MONITOR = monitor
