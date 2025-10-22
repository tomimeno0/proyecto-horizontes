"""Registro de nodos distribuido con API pública."""

from __future__ import annotations

from datetime import datetime
from threading import RLock
from typing import Dict, List, Literal

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


NodeStatus = Literal["active", "unknown", "unreachable", "isolated"]


class NodePayload(BaseModel):
    """Carga útil para registrar nodos en la red."""

    node_id: str = Field(..., min_length=1, max_length=64)
    address: AnyHttpUrl
    status: NodeStatus = "active"

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str) -> NodeStatus:
        translations = {
            "activo": "active",
            "inactivo": "unknown",
            "aislado": "isolated",
            "desconectado": "unreachable",
        }
        normalized = translations.get(value, value)
        if normalized not in ("active", "unknown", "unreachable", "isolated"):
            raise ValueError("Estado de nodo inválido.")
        return normalized  # type: ignore[return-value]


class Node(NodePayload):
    """Representación inmutable de un nodo registrado."""

    last_activity: datetime | None = None
    avg_latency_ms: float | None = None
    heartbeat_count: int = 0
    sync_score: float | None = None
    reliability: float = 1.0
    consecutive_failures: int = 0


class NodeRegistry:
    """Gestiona la información de nodos Horizonte en memoria."""

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._lock = RLock()

    def register(self, payload: NodePayload) -> Node:
        """Inserta o actualiza un nodo validando la dirección única."""

        candidate_data = payload.model_dump()
        candidate = Node(**candidate_data)
        with self._lock:
            for node_id, node in self._nodes.items():
                if (
                    node.address == candidate.address
                    and node_id != candidate.node_id
                ):
                    raise ValueError("La dirección ya está asociada a otro nodo.")
            previous = self._nodes.get(candidate.node_id)
            if previous is not None:
                merged = previous.model_copy(update=candidate_data)
                candidate = Node(**merged.model_dump())
            self._nodes[candidate.node_id] = candidate
        return candidate

    def list_nodes(self) -> List[Node]:
        with self._lock:
            return list(self._nodes.values())

    def remove(self, node_id: str) -> None:
        with self._lock:
            if node_id not in self._nodes:
                raise KeyError(node_id)
            del self._nodes[node_id]

    def set_status(self, node_id: str, status: NodeStatus) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(node_id)
            self._nodes[node_id] = node.model_copy(update={"status": status})

    def set_mode(self, node_id: str, isolated: bool) -> None:
        """Marca un nodo como aislado o normal."""

        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(node_id)
            status = "isolated" if isolated else node.status
            if not isolated and node.status == "isolated":
                status = "active"
            update = {"status": status}
            self._nodes[node_id] = node.model_copy(update=update)

    def get(self, node_id: str) -> Node | None:
        with self._lock:
            return self._nodes.get(node_id)

    def get_active_nodes(self, exclude: str | None = None) -> List[Node]:
        with self._lock:
            nodes = [
                node
                for node in self._nodes.values()
                if node.status == "active"
            ]
        if exclude is not None:
            nodes = [node for node in nodes if node.node_id != exclude]
        return nodes

    def count_active(self) -> int:
        return len(self.get_active_nodes())

    def record_heartbeat(
        self, node_id: str, *, latency_ms: float | None, timestamp: datetime
    ) -> Node:
        """Actualiza métricas de latencia y actividad para un nodo."""

        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(node_id)

            heartbeat_count = node.heartbeat_count + 1
            avg_latency = node.avg_latency_ms or 0.0
            if latency_ms is not None:
                if node.avg_latency_ms is None:
                    avg_latency = latency_ms
                else:
                    avg_latency = round(
                        ((node.avg_latency_ms * node.heartbeat_count) + latency_ms)
                        / heartbeat_count,
                        3,
                    )

            updated = node.model_copy(
                update={
                    "last_activity": timestamp,
                    "avg_latency_ms": avg_latency if latency_ms is not None else node.avg_latency_ms,
                    "heartbeat_count": heartbeat_count,
                    "status": "active",
                    "consecutive_failures": 0,
                }
            )
            self._nodes[node_id] = updated
            return updated

    def mark_failure(self, node_id: str) -> Node:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(node_id)
            failures = node.consecutive_failures + 1
            status = node.status
            if failures >= 3:
                status = "unreachable"
            updated = node.model_copy(
                update={"consecutive_failures": failures, "status": status}
            )
            self._nodes[node_id] = updated
            return updated

    def update_sync_score(self, node_id: str, sync_score: float) -> Node:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(node_id)
            updated = node.model_copy(update={"sync_score": round(sync_score, 3)})
            self._nodes[node_id] = updated
            return updated

    def set_reliability(self, node_id: str, reliability: float) -> Node:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(node_id)
            updated = node.model_copy(update={"reliability": float(reliability)})
            self._nodes[node_id] = updated
            return updated

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()


_REGISTRY = NodeRegistry()


def get_registry() -> NodeRegistry:
    """Devuelve la instancia global utilizada por la aplicación."""

    return _REGISTRY


router = APIRouter(tags=["nodes"])


@router.post("/register", response_model=Node, status_code=status.HTTP_201_CREATED)
def register_node(payload: NodePayload) -> Node:
    """Registra o actualiza un nodo remoto."""

    registry = get_registry()
    try:
        return registry.register(payload)
    except ValueError as exc:  # pragma: no cover - ruta de validación
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=List[Node])
def list_nodes() -> List[Node]:
    """Lista todos los nodos registrados."""

    return get_registry().list_nodes()


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(node_id: str) -> Response:
    """Elimina un nodo del registro."""

    registry = get_registry()
    try:
        registry.remove(node_id)
    except KeyError as exc:  # pragma: no cover - protección frente a abusos
        raise HTTPException(status_code=404, detail="Nodo no encontrado") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = [
    "Node",
    "NodePayload",
    "NodeRegistry",
    "NodeStatus",
    "get_registry",
    "router",
]

