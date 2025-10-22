"""Gestor de consenso distribuido con simulación de red."""

from __future__ import annotations

import logging
import math
from typing import Dict, List

import anyio

from horizonte.net import sim_net
from horizonte.net.node_registry import Node, NodeRegistry, get_registry

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


async def broadcast_result_async(
    origin_node_id: str, h: str, quorum: int | None = None
) -> dict[str, object]:
    """Solicita la validación del hash a los nodos activos."""

    registry: NodeRegistry = get_registry()
    candidates: List[Node] = registry.get_active_nodes(exclude=origin_node_id)
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
                    registry.set_status(node.node_id, "active")
                except KeyError:  # pragma: no cover - nodo eliminado en paralelo
                    pass
            else:
                failed.append(node.node_id)
                try:
                    registry.set_status(node.node_id, "unknown")
                except KeyError:  # pragma: no cover - nodo eliminado en paralelo
                    pass
        except TimeoutError:
            logger.warning(
                "validator_timeout",
                extra={"node_id": node.node_id, "address": str(node.address)},
            )
            failed.append(node.node_id)
            try:
                registry.set_status(node.node_id, "unknown")
            except KeyError:  # pragma: no cover - nodo eliminado en paralelo
                pass
        except Exception:  # pragma: no cover - protección adicional
            logger.exception(
                "validator_error",
                extra={"node_id": node.node_id, "address": str(node.address)},
            )
            failed.append(node.node_id)
            try:
                registry.set_status(node.node_id, "unknown")
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

    return {"approved": approved, "validators": validators_ok, "failed": failed}


__all__ = ["broadcast_result_async"]
