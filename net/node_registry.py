"""Registro de nodos participantes en la red Horizonte."""

from __future__ import annotations

from threading import RLock
from typing import Dict, List, Literal

from fastapi import APIRouter, status
from pydantic import AnyHttpUrl, BaseModel, Field


class NodePayload(BaseModel):
    """Modelo de entrada para registrar nodos externos."""

    node_id: str = Field(..., min_length=1, max_length=64)
    address: AnyHttpUrl = Field(..., description="URL base del nodo remoto")
    status: Literal["activo", "inactivo"] = "activo"


class Node(NodePayload):
    """Representación normalizada de un nodo registrado."""


class NodeRegistry:
    """Gestiona en memoria el registro de nodos disponibles."""

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._lock = RLock()

    def register(self, payload: NodePayload) -> Node:
        """Guarda o actualiza la información de un nodo."""

        nodo = Node(**payload.model_dump())
        with self._lock:
            self._nodes[nodo.node_id] = nodo
        return nodo

    def list_nodes(self) -> List[Node]:
        """Devuelve todos los nodos conocidos."""

        with self._lock:
            return list(self._nodes.values())

    def get_active_nodes(self, exclude: str | None = None) -> List[Node]:
        """Obtiene nodos activos, opcionalmente excluyendo uno por id."""

        with self._lock:
            nodos = [n for n in self._nodes.values() if n.status == "activo"]
        if exclude is not None:
            nodos = [n for n in nodos if n.node_id != exclude]
        return nodos

    def count_active(self) -> int:
        """Cuenta los nodos activos en el registro."""

        return len(self.get_active_nodes())

    def clear(self) -> None:
        """Limpia el registro, útil para pruebas."""

        with self._lock:
            self._nodes.clear()


_REGISTRY = NodeRegistry()


def get_registry() -> NodeRegistry:
    """Obtiene la instancia global del registro de nodos."""

    return _REGISTRY


router = APIRouter(tags=["nodos"])


@router.get("/", response_model=List[Node])
def listar_nodos() -> List[Node]:
    """Lista todos los nodos registrados."""

    return get_registry().list_nodes()


@router.post("/", response_model=Node, status_code=status.HTTP_201_CREATED)
def registrar_nodo(payload: NodePayload) -> Node:
    """Registra un nodo remoto accesible por la red."""

    return get_registry().register(payload)
