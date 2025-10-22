"""Sincronización distribuida de las evaluaciones cognitivas."""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from horizonte.core.metacognition import get_cognitive_mirror
from horizonte.net.node_registry import get_registry

PeerFetcher = Callable[[int], Sequence[tuple[str, float]]]


@dataclass(slots=True)
class SyncOutcome:
    """Resultado de un ciclo de auditoría cognitiva distribuida."""

    node_id: str
    local_score: float
    collective_score: float
    action_taken: str
    timestamp: str


class CognitiveSync:
    """Coordina el intercambio periódico de autoevaluaciones entre nodos."""

    def __init__(
        self,
        *,
        node_id: str,
        log_path: Path | None = None,
        interval_seconds: float = 600.0,
        sample_size: int = 3,
        peer_fetcher: PeerFetcher | None = None,
    ) -> None:
        self.node_id = node_id
        self.interval_seconds = interval_seconds
        self.sample_size = max(1, sample_size)
        self.log_path = log_path or Path(__file__).resolve().with_name("cognitive_sync.json")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text("[]", encoding="utf-8")
        self._peer_fetcher = peer_fetcher or self._default_peer_fetcher
        self._lock = RLock()

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        """Ejecuta ciclos periódicos hasta que se indique lo contrario."""

        while True:
            await self.execute_cycle()
            if stop_event and stop_event.is_set():
                break
            await asyncio.sleep(self.interval_seconds)

    async def execute_cycle(self) -> SyncOutcome:
        """Ejecuta un ciclo completo de sincronización."""

        mirror = get_cognitive_mirror()
        analysis = mirror.analyze_self()
        raw_score = analysis.get("consistency_score", 1.0)
        if isinstance(raw_score, (int, float)):
            local_score = float(raw_score)
        else:
            local_score = 1.0
        peers = list(self._peer_fetcher(self.sample_size))
        scores = [local_score]
        scores.extend(float(score) for _, score in peers if score is not None)
        if not scores:
            collective = local_score
        else:
            collective = sum(scores) / len(scores)
        collective = round(collective, 3)
        action = "resync" if collective < 0.7 else "none"
        timestamp = datetime.now(timezone.utc).isoformat()
        outcome = SyncOutcome(
            node_id=self.node_id,
            local_score=round(local_score, 3),
            collective_score=collective,
            action_taken=action,
            timestamp=timestamp,
        )
        self._append_log(outcome)
        mirror.update_collective_consistency(collective)
        if action == "resync":
            mirror.register_event(
                "cognitive_sync",
                {
                    "peers": [peer for peer, _ in peers],
                    "collective_score": collective,
                    "action": action,
                },
            )
        return outcome

    def _append_log(self, outcome: SyncOutcome) -> None:
        """Almacena un resultado en el log JSON garantizando consistencia."""

        payload = asdict(outcome)
        with self._lock:
            data = self._read_log()
            data.append(payload)
            self.log_path.write_text(
                json.dumps(data[-500:], indent=2, ensure_ascii=False), encoding="utf-8"
            )

    def history(self) -> list[dict[str, object]]:
        """Devuelve los registros almacenados."""

        with self._lock:
            return self._read_log()

    def _read_log(self) -> list[dict[str, object]]:
        try:
            raw = json.loads(self.log_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return list(raw)
        except json.JSONDecodeError:
            pass
        return []

    def _default_peer_fetcher(self, limit: int) -> Sequence[tuple[str, float]]:
        registry = get_registry()
        nodes = registry.get_active_nodes(exclude=self.node_id)
        if not nodes:
            return []
        random.shuffle(nodes)
        selected = nodes[:limit]
        mirror_score = get_cognitive_mirror().status().global_consistency
        peers: list[tuple[str, float]] = []
        for node in selected:
            score = node.sync_score if node.sync_score is not None else mirror_score
            peers.append((node.node_id, float(score)))
        return peers


__all__ = ["CognitiveSync", "SyncOutcome"]
