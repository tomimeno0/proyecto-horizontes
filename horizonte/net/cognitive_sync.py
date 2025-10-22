"""Sincronización cognitiva distribuida entre nodos Horizonte."""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable

from horizonte.core.metacognition import CognitiveMirror, get_cognitive_mirror

DEFAULT_INTERVAL = 600.0


@dataclass(frozen=True)
class CognitiveSyncStatus:
    """Último estado conocido del proceso de sincronización."""

    node_id: str
    local_score: float
    collective_score: float
    action_taken: str
    timestamp: str


class CognitiveSyncManager:
    """Coordina autoevaluaciones locales y comparte resultados con pares."""

    def __init__(
        self,
        node_id: str,
        mirror: CognitiveMirror | None = None,
        peer_score_provider: Callable[[int], Sequence[float]] | None = None,
        resync_callback: Callable[[float], None] | None = None,
        log_path: Path | None = None,
        interval: float = DEFAULT_INTERVAL,
        peers_sample: int = 3,
        threshold: float = 0.7,
        max_logs: int = 500,
    ) -> None:
        self._node_id = node_id
        self._mirror = mirror or get_cognitive_mirror()
        self._peer_score_provider = peer_score_provider or (lambda count: [])
        self._resync_callback = resync_callback
        self._log_path = log_path or Path(__file__).resolve().parent / "cognitive_sync_log.json"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.write_text("[]", encoding="utf-8")
        self._interval = interval
        self._peers_sample = peers_sample
        self._threshold = threshold
        self._max_logs = max_logs
        self._lock = Lock()
        self._last_status: CognitiveSyncStatus | None = None

    # ------------------------------------------------------------------
    # Ejecución de ciclos
    # ------------------------------------------------------------------
    def run_cycle(self) -> CognitiveSyncStatus:
        """Ejecuta un ciclo completo de autoevaluación y sincronización."""

        local_score = self._mirror.analyze_self()
        peer_scores = list(self._peer_score_provider(self._peers_sample))
        if len(peer_scores) > self._peers_sample:
            peer_scores = random.sample(peer_scores, self._peers_sample)
        all_scores = [local_score]
        all_scores.extend(peer_scores[: self._peers_sample])
        if all_scores:
            collective = sum(all_scores) / len(all_scores)
        else:  # pragma: no cover - escenario degenerado
            collective = local_score
        action = "none"
        if collective < self._threshold:
            action = "resync"
            if self._resync_callback:
                try:
                    self._resync_callback(collective)
                except Exception:  # pragma: no cover - evitar fallos cascada
                    pass
        timestamp = datetime.now(timezone.utc).isoformat()
        status = CognitiveSyncStatus(
            node_id=self._node_id,
            local_score=round(local_score, 3),
            collective_score=round(collective, 3),
            action_taken=action,
            timestamp=timestamp,
        )
        with self._lock:
            self._last_status = status
            self._append_log(status)
        return status

    async def run_periodic(self, stop_event: asyncio.Event | None = None) -> None:
        """Ejecuta ciclos periódicos hasta que se solicite detener."""

        while True:
            self.run_cycle()
            if stop_event and stop_event.is_set():
                break
            await asyncio.sleep(self._interval)

    # ------------------------------------------------------------------
    # Logs y consultas
    # ------------------------------------------------------------------
    def _append_log(self, status: CognitiveSyncStatus) -> None:
        entry = {
            "node_id": status.node_id,
            "local_score": status.local_score,
            "collective_score": status.collective_score,
            "action_taken": status.action_taken,
            "timestamp": status.timestamp,
        }
        try:
            data = json.loads(self._log_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except json.JSONDecodeError:
            data = []
        data.append(entry)
        data = data[-self._max_logs :]
        self._log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def history(self, limit: int | None = None) -> list[dict[str, object]]:
        try:
            data = json.loads(self._log_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
        except json.JSONDecodeError:
            return []
        if limit is None:
            return data
        return data[-limit:]

    def reset(self) -> None:
        with self._lock:
            self._log_path.write_text("[]", encoding="utf-8")
            self._last_status = None

    def status(self) -> CognitiveSyncStatus | None:
        with self._lock:
            return self._last_status

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------
    @property
    def interval(self) -> float:
        return self._interval


# ----------------------------------------------------------------------
# Gestión global
# ----------------------------------------------------------------------
_SYNC_MANAGER: CognitiveSyncManager | None = None


def get_cognitive_sync_manager() -> CognitiveSyncManager:
    """Obtiene o crea un gestor global de sincronización cognitiva."""

    global _SYNC_MANAGER
    if _SYNC_MANAGER is None:
        from horizonte.common.config import get_settings

        settings = get_settings()
        _SYNC_MANAGER = CognitiveSyncManager(node_id=settings.node_id)
    return _SYNC_MANAGER


def set_cognitive_sync_manager(manager: CognitiveSyncManager | None) -> None:
    global _SYNC_MANAGER
    _SYNC_MANAGER = manager


async def periodic_cognitive_sync(interval: float | None = None) -> None:
    """Lanza sincronizaciones periódicas utilizando el gestor global."""

    manager = get_cognitive_sync_manager()
    wait_interval = interval if interval is not None else manager.interval
    while True:
        manager.run_cycle()
        await asyncio.sleep(wait_interval)


__all__ = [
    "CognitiveSyncManager",
    "CognitiveSyncStatus",
    "get_cognitive_sync_manager",
    "set_cognitive_sync_manager",
    "periodic_cognitive_sync",
]
