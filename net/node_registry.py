"""Compatibilidad hacia delante para el registro de nodos."""

from __future__ import annotations

from horizonte.net.node_registry import (  # noqa: F401
    Node,
    NodePayload,
    NodeRegistry,
    NodeStatus,
    get_registry,
    router,
)

__all__ = [
    "Node",
    "NodePayload",
    "NodeRegistry",
    "NodeStatus",
    "get_registry",
    "router",
]

