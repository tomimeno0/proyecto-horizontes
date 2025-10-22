"""Compatibilidad con el gestor de consenso moderno."""

from __future__ import annotations

import anyio

from horizonte.net import sim_net
from horizonte.net.consensus_manager import broadcast_result_async  # noqa: F401


def _simulate_remote_verification(address: str, payload: dict[str, str]) -> bool:
    """Compatibilidad con las pruebas legadas."""

    return anyio.run(sim_net.simulate_call, address, payload)


def broadcast_result(origin_node_id: str, h: str, quorum: int | None = None) -> dict[str, object]:
    """Ejecuta el consenso asíncrono en modo síncrono."""

    return anyio.run(broadcast_result_async, origin_node_id, h, quorum)


__all__ = ["broadcast_result", "broadcast_result_async"]

