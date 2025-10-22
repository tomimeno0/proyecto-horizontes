"""Gestión de nodos para la red Horizonte."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List

import anyio

from horizonte.common.config import get_settings
from horizonte.net.node_registry import Node, NodePayload, NodeRegistry, get_registry


@dataclass
class NodeManager:
    """Gestiona información mínima del nodo actual."""

    status: str = "inicializando"
    metadata: Dict[str, str] = field(default_factory=dict)
    registry: NodeRegistry = field(default_factory=get_registry)

    def __post_init__(self) -> None:
        settings = get_settings()
        self.metadata.setdefault("node_id", settings.node_id)
        self.metadata.setdefault("env", settings.env)
        self.metadata.setdefault("boot_time", datetime.now(timezone.utc).isoformat())
        self.status = "activo"
        address = self.metadata.get("address")
        if address:
            self.register_self(address)

    def heartbeat(self) -> Dict[str, str]:
        """Genera un pulso de vida del nodo."""
        pulso = {
            "node_id": self.metadata["node_id"],
            "status": self.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return pulso

    def update_status(self, status: str) -> None:
        """Actualiza el estado operativo del nodo."""
        self.status = status
        try:
            self.registry.set_status(self.metadata["node_id"], status)
        except KeyError:
            # Si el nodo aún no está registrado, se ignora la actualización.
            pass

    @property
    def node_id(self) -> str:
        return self.metadata["node_id"]

    def register_self(self, address: str) -> Node:
        """Registra el nodo actual en el registro distribuido."""

        self.metadata["address"] = address
        payload = NodePayload(
            node_id=self.node_id,
            address=address,
            status="active",
        )
        node = self.registry.register(payload)
        return node

    def get_active_nodes(self) -> List[Node]:
        """Obtiene los nodos activos excluyendo el propio."""

        return self.registry.get_active_nodes(exclude=self.node_id)

    async def reconnect_with_backoff(
        self,
        action: Callable[[], Awaitable[bool]] | None = None,
        *,
        attempts: int = 5,
        base_delay: float = 1.0,
    ) -> bool:
        """Ejecuta un proceso de reconexión con backoff exponencial."""

        success = False
        for attempt in range(attempts):
            try:
                if action is None:
                    # Intento por defecto: re-registrar con la dirección conocida.
                    address = self.metadata.get("address")
                    if not address:
                        raise ValueError("No se ha configurado una dirección para el nodo.")
                    self.register_self(address)
                    success = True
                else:
                    success = bool(await action())
            except Exception:
                success = False

            if success:
                self.registry.set_status(self.node_id, "active")
                self.registry.set_mode(self.node_id, False)
                return True

            delay = base_delay * (2**attempt)
            await anyio.sleep(delay)

        self.registry.set_status(self.node_id, "unreachable")
        return False
