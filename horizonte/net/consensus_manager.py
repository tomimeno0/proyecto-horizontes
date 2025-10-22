"""Gestor de consenso distribuido con simulación de red."""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import anyio

from horizonte.net import sim_net
from horizonte.net.node_manager import NodeManager
from horizonte.net.node_registry import Node, NodeRegistry, get_registry
from horizonte.net.sync_protocol import get_sync_protocol

logger = logging.getLogger("horizonte.net.consensus")


def _build_payload(origin_node_id: str, h: str) -> Dict[str, str]:
    return {"hash": h, "origin": origin_node_id}


async def _call_validator(node: Node, payload: Dict[str, str]) -> bool:
    address = str(node.address).rstrip("/")
    from net import consensus_manager as legacy_consensus

    verifier = getattr(legacy_consensus, "_simulate_remote_verification", None)
    if verifier is not None:
        return bool(await anyio.to_thread.run_sync(verifier, address, payload))

    result = await sim_net.simulate_call(address, payload)
    return bool(result)


class ConsensusManager:
    """Coordina el proceso de consenso y gestiona estados autónomos."""

    def __init__(
        self,
        *,
        registry: NodeRegistry | None = None,
        node_manager: NodeManager | None = None,
        history_path: Path | None = None,
    ) -> None:
        self.registry = registry or get_registry()
        self.node_manager = node_manager or NodeManager()
        self.history_path = history_path or Path(__file__).with_name("consensus_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history: List[Dict[str, object]] = self._load_history()
        self._history_lock = anyio.Lock()
        self.failure_streak = 0
        self.mode = "autonomous"

    def _load_history(self) -> List[Dict[str, object]]:
        if not self.history_path.exists():
            return []
        try:
            raw = self.history_path.read_text()
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return []
        if isinstance(data, list):
            return data
        return []

    async def _persist_history(self) -> None:
        async with self._history_lock:
            payload = json.dumps(self._history[-200:], indent=2, ensure_ascii=False)
            await anyio.to_thread.run_sync(self.history_path.write_text, payload)

    async def _broadcast_once(
        self, origin_node_id: str, h: str, quorum: int | None = None
    ) -> Dict[str, object]:
        candidates: List[Node] = self.registry.get_active_nodes(exclude=origin_node_id)
        total = len(candidates)
        required = quorum if quorum is not None else math.ceil((2 * total) / 3) or total

        payload = _build_payload(origin_node_id, h)
        validators_ok: List[str] = []
        failed: List[str] = []

        for node in candidates:
            try:
                if await _call_validator(node, payload):
                    validators_ok.append(node.node_id)
                    try:
                        self.registry.set_status(node.node_id, "active")
                    except KeyError:  # pragma: no cover - nodo eliminado en paralelo
                        pass
                else:
                    failed.append(node.node_id)
                    try:
                        self.registry.set_status(node.node_id, "unknown")
                    except KeyError:  # pragma: no cover - nodo eliminado en paralelo
                        pass
            except TimeoutError:
                logger.warning(
                    "validator_timeout",
                    extra={"node_id": node.node_id, "address": str(node.address)},
                )
                failed.append(node.node_id)
                try:
                    self.registry.set_status(node.node_id, "unknown")
                except KeyError:  # pragma: no cover - nodo eliminado en paralelo
                    pass
            except Exception:  # pragma: no cover - protección adicional
                logger.exception(
                    "validator_error",
                    extra={"node_id": node.node_id, "address": str(node.address)},
                )
                failed.append(node.node_id)
                try:
                    self.registry.set_status(node.node_id, "unknown")
                except KeyError:  # pragma: no cover - nodo eliminado en paralelo
                    pass

        approved = len(validators_ok) >= required and required > 0

        logger.info(
            "consensus_result",
            extra={
                "hash": h,
                "approved": approved,
                "ok": len(validators_ok),
                "failed": len(failed),
                "required": required,
                "total": total,
            },
        )

        return {
            "approved": approved,
            "validators": validators_ok,
            "failed": failed,
            "required": required,
            "total": total,
        }

    def _needs_retry(self, result: Dict[str, object]) -> bool:
        total = int(result.get("total", 0))
        if total == 0:
            return False
        validators = len(result.get("validators", []))
        ratio = validators / total if total else 0.0
        return ratio < (2 / 3)

    async def _attempt_resync(self) -> None:
        protocol = get_sync_protocol()
        status = await protocol.get_status()
        await protocol.update_local_ledger([])
        logger.info(
            "consensus_resync",
            extra={"ledger_size": status.ledger_size, "sync_score": status.sync_score},
        )

    async def _record_entry(
        self, hash_value: str, result: Dict[str, object], mode: str
    ) -> None:
        protocol = get_sync_protocol()
        status = await protocol.get_status()
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": hash_value,
            "approved": bool(result.get("approved")),
            "validators": list(result.get("validators", [])),
            "failed": list(result.get("failed", [])),
            "mode": mode,
            "sync_score": status.sync_score,
        }
        self._history.append(entry)
        await self._persist_history()

    async def broadcast(
        self, origin_node_id: str, h: str, quorum: int | None = None
    ) -> Dict[str, object]:
        result = await self._broadcast_once(origin_node_id, h, quorum)

        if self._needs_retry(result):
            await self._attempt_resync()
            retry_quorum = int(result.get("required", 0)) or quorum
            retry = await self._broadcast_once(origin_node_id, h, retry_quorum)
            if len(retry.get("validators", [])) >= len(result.get("validators", [])):
                result = retry

        if result["approved"]:
            self.failure_streak = 0
            self.mode = "autonomous"
            try:
                self.registry.set_mode(self.node_manager.node_id, False)
            except KeyError:
                pass
        else:
            self.failure_streak += 1
            if self.failure_streak > 3:
                self.mode = "isolated"
                self.node_manager.update_status("isolated")
                try:
                    self.registry.set_mode(self.node_manager.node_id, True)
                except KeyError:
                    pass

        await self._record_entry(h, result, self.mode)
        return result


_MANAGER: ConsensusManager | None = None


def get_consensus_manager() -> ConsensusManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ConsensusManager()
    return _MANAGER


async def broadcast_result_async(
    origin_node_id: str, h: str, quorum: int | None = None
) -> Dict[str, object]:
    """Solicita la validación del hash a los nodos activos."""

    manager = get_consensus_manager()
    return await manager.broadcast(origin_node_id, h, quorum)


__all__ = ["broadcast_result_async", "ConsensusManager", "get_consensus_manager"]

