"""Gestor de consenso para la red Horizonte."""

from __future__ import annotations

import logging
import math
from typing import Dict, List

from net.node_registry import Node, get_registry

logger = logging.getLogger("net.consensus_manager")


def _simulate_remote_verification(address: str, payload: Dict[str, str]) -> bool:
    """Simula la verificación remota realizada por un nodo validador."""

    return True


def _build_payload(origin_node_id: str, h: str) -> Dict[str, str]:
    """Construye el cuerpo común enviado a los validadores."""

    return {"hash": h, "origin": origin_node_id}


def broadcast_result(origin_node_id: str, h: str, quorum: int | None = None) -> dict[str, str | bool | List[str]]:
    """Obtiene un consenso distribuido para el hash indicado."""

    registry = get_registry()
    nodes: List[Node] = registry.list_nodes()
    candidates = [node for node in nodes if node.node_id != origin_node_id]

    total = len(candidates)
    required = quorum if quorum is not None else math.ceil((2 * total) / 3)
    validators_ok: List[str] = []

    if total > 0:
        payload = _build_payload(origin_node_id, h)
        for node in candidates:
            address = str(node.address).rstrip("/")
            try:
                if _simulate_remote_verification(address, payload):
                    validators_ok.append(node.node_id)
            except Exception:  # pragma: no cover - protege ante fallos inesperados
                logger.error(
                    "error_verificacion",
                    extra={"address": address},
                    exc_info=True,
                )

        approved = len(validators_ok) >= required
    else:
        approved = False

    logger.info(
        "resultado_consenso",
        extra={
            "hash": h,
            "approved": approved,
            "ok": len(validators_ok),
            "total": total,
            "required": required,
        },
    )

    return {"hash": h, "approved": approved, "validators": validators_ok}

