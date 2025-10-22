"""Protocolo de sincronización tipo gossip entre nodos Horizonte."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, TYPE_CHECKING

import anyio
from fastapi import APIRouter
from pydantic import BaseModel, Field

from horizonte.net.node_manager import NodeManager
from horizonte.net.node_registry import get_registry

if TYPE_CHECKING:
    from horizonte.net.node_registry import NodeRegistry

logger = logging.getLogger("horizonte.net.sync")


class SyncUpdateRequest(BaseModel):
    """Payload esperado para intercambiar información de ledger."""

    peer_id: str = Field(..., min_length=1, max_length=64)
    hashes: List[str] = Field(default_factory=list)
    records: List[str] | None = None


class SyncStatusResponse(BaseModel):
    """Estado actual del proceso de sincronización local."""

    node_id: str
    ledger_size: int
    sync_score: float
    history: List[Dict[str, object]]


router = APIRouter(prefix="/sync", tags=["sync"])


class SyncProtocol:
    """Implementación simplificada de un protocolo gossip."""

    def __init__(
        self,
        node_manager: NodeManager,
        *,
        registry: "NodeRegistry" | None = None,
        window: int = 200,
    ) -> None:
        self.node_manager = node_manager
        self.registry = registry or get_registry()
        self.window = window
        self._ledger: List[str] = []
        self._history: List[Dict[str, object]] = []
        self._scores: Dict[str, float] = {}
        self._lock = anyio.Lock()
        self._sync_score = 1.0

    async def update_local_ledger(self, records: List[str]) -> List[str]:
        """Incorpora registros nuevos al ledger local."""

        async with self._lock:
            added = [record for record in records if record not in self._ledger]
            if added:
                self._ledger.extend(added)
            return added

    async def _register_history(
        self,
        peer_id: str,
        matched: List[str],
        added: List[str],
        dropped: List[str],
    ) -> None:
        entry = {
            "peer": peer_id,
            "matched": matched,
            "added": added,
            "dropped": dropped,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(entry)
        if len(self._history) > self.window:
            self._history = self._history[-self.window :]
        logger.info("sync_event", extra=entry)

    async def process_update(self, payload: SyncUpdateRequest) -> Dict[str, object]:
        """Compara los hashes remotos y actualiza la puntuación local."""

        async with self._lock:
            hashes = payload.hashes
            matched = sorted(set(self._ledger).intersection(hashes))
            missing_here = [h for h in hashes if h not in self._ledger]
            dropped = [h for h in self._ledger if h not in hashes]
            denominator = max(len(self._ledger), len(hashes), 1)
            score = len(matched) / denominator
            self._scores[payload.peer_id] = score
            try:
                self.registry.update_sync_score(payload.peer_id, score)
            except KeyError:
                # el peer aún no se ha registrado localmente
                pass

            added: List[str] = []
            if payload.records:
                for record in payload.records:
                    if record not in self._ledger:
                        self._ledger.append(record)
                        added.append(record)

            if dropped:
                # Se eliminan los registros que ningún peer reconoce
                self._ledger = [h for h in self._ledger if h not in dropped]

            if self._scores:
                self._sync_score = round(
                    sum(self._scores.values()) / len(self._scores), 3
                )
            else:
                self._sync_score = 1.0

        await self._register_history(payload.peer_id, matched, added, dropped)
        return {
            "peer": payload.peer_id,
            "matched": matched,
            "missing": missing_here,
            "added": added,
            "dropped": dropped,
            "sync_score": self._sync_score,
            "request_pull": missing_here,
        }

    async def get_status(self) -> SyncStatusResponse:
        async with self._lock:
            history = list(self._history)
            ledger_size = len(self._ledger)
            score = self._sync_score
        return SyncStatusResponse(
            node_id=self.node_manager.node_id,
            ledger_size=ledger_size,
            sync_score=score,
            history=history,
        )


_PROTOCOL: SyncProtocol | None = None


def configure_sync(node_manager: NodeManager) -> SyncProtocol:
    global _PROTOCOL
    _PROTOCOL = SyncProtocol(node_manager)
    return _PROTOCOL


def get_sync_protocol() -> SyncProtocol:
    global _PROTOCOL
    if _PROTOCOL is None:
        _PROTOCOL = SyncProtocol(NodeManager())
    return _PROTOCOL


@router.get("/status", response_model=SyncStatusResponse)
async def sync_status() -> SyncStatusResponse:
    protocol = get_sync_protocol()
    return await protocol.get_status()


@router.post("/update")
async def sync_update(payload: SyncUpdateRequest) -> Dict[str, object]:
    protocol = get_sync_protocol()
    return await protocol.process_update(payload)
