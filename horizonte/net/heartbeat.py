"""Mecanismo de heartbeat distribuido para los nodos Horizonte."""

from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Dict

import anyio
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from horizonte.net.node_manager import NodeManager
from horizonte.net.node_registry import Node, NodeRegistry, get_registry

logger = logging.getLogger("horizonte.net.heartbeat")


def _default_client_factory() -> httpx.AsyncClient:
    timeout = httpx.Timeout(5.0, read=5.0, write=5.0, connect=5.0)
    return httpx.AsyncClient(timeout=timeout)


def build_signature(node_id: str, timestamp: datetime) -> str:
    """Construye una firma SHA256 simple para validar heartbeats."""

    base = f"{node_id}:{timestamp.isoformat()}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()


class HeartbeatPing(BaseModel):
    """Carga útil esperada para pings de heartbeat."""

    node_id: str = Field(..., min_length=1, max_length=64)
    timestamp: datetime
    signature: str

    @field_validator("signature")
    @classmethod
    def validate_signature(cls, value: str, info: ValidationInfo) -> str:
        data = info.data or {}
        node_id = data.get("node_id")
        timestamp = data.get("timestamp")
        if isinstance(node_id, str) and isinstance(timestamp, datetime):
            expected = build_signature(node_id, timestamp)
            if expected != value:
                raise ValueError("Firma de heartbeat inválida")
        return value


class HeartbeatAck(BaseModel):
    """Respuesta canónica para heartbeats recibidos."""

    status: str = "ack"
    received_at: datetime
    latency_ms: float | None = None


router = APIRouter(tags=["nodes"])


@router.post("/heartbeat", response_model=HeartbeatAck)
async def receive_heartbeat(payload: HeartbeatPing) -> HeartbeatAck:
    """Procesa un heartbeat entrante y actualiza el registro."""

    registry = get_registry()
    now = datetime.now(timezone.utc)
    try:
        registry.record_heartbeat(payload.node_id, latency_ms=None, timestamp=now)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Nodo no registrado") from exc
    return HeartbeatAck(received_at=now)


class HeartbeatService:
    """Servicio asincrónico encargado de enviar heartbeats periódicos."""

    def __init__(
        self,
        node_manager: NodeManager,
        *,
        registry: NodeRegistry | None = None,
        interval: float = 15.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.node_manager = node_manager
        self.registry = registry or get_registry()
        self.interval = interval
        self._client_factory = client_factory or _default_client_factory
        self._missed_cycles: Dict[str, int] = defaultdict(int)
        self._running = False

    def build_payload(self) -> Dict[str, str]:
        timestamp = datetime.now(timezone.utc)
        signature = build_signature(self.node_manager.node_id, timestamp)
        return {
            "node_id": self.node_manager.node_id,
            "timestamp": timestamp.isoformat(),
            "signature": signature,
        }

    async def _ping_node(self, client: httpx.AsyncClient, node: Node) -> None:
        url = f"{str(node.address).rstrip('/')}/nodes/heartbeat"
        payload = self.build_payload()
        start = time.perf_counter()
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except Exception:
            logger.warning("heartbeat_failed", extra={"node": node.node_id, "url": url})
            updated = self.registry.mark_failure(node.node_id)
            self._missed_cycles[node.node_id] = updated.consecutive_failures
            return

        latency_ms = (time.perf_counter() - start) * 1000
        self.registry.record_heartbeat(
            node.node_id, latency_ms=latency_ms, timestamp=datetime.now(timezone.utc)
        )
        self._missed_cycles[node.node_id] = 0

    async def send_cycle(self) -> None:
        nodes = self.node_manager.get_active_nodes()
        if not nodes:
            return
        async with self._client_factory() as client:
            async with anyio.create_task_group() as tg:
                for node in nodes:
                    tg.start_soon(self._ping_node, client, node)

    async def run(self) -> None:
        """Ejecuta el ciclo de heartbeats hasta que se detenga."""

        if self._running:
            return
        self._running = True
        try:
            while self._running:
                await self.send_cycle()
                await anyio.sleep(self.interval)
        finally:
            self._running = False

    async def stop(self) -> None:
        self._running = False
