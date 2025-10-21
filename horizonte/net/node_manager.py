"""Gestión de nodos para la red Horizonte."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict

from horizonte.common.config import get_settings


@dataclass
class NodeManager:
    """Gestiona información mínima del nodo actual."""

    status: str = "inicializando"
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        settings = get_settings()
        self.metadata.setdefault("node_id", settings.node_id)
        self.metadata.setdefault("env", settings.env)
        self.metadata.setdefault("boot_time", datetime.now(timezone.utc).isoformat())
        self.status = "activo"

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
