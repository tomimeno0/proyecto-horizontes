"""Gestor de consenso simulado entre nodos Horizonte."""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import httpx

from net.node_registry import Node, get_registry

logger = logging.getLogger(__name__)


def _simulate_remote_verification(address: str, payload: Dict[str, str]) -> bool:
    """Invoca el endpoint remoto `/verify` de un nodo validador."""

    url = f"{address.rstrip('/')}/verify"
    with httpx.Client(timeout=5.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return bool(data.get("valid", False))


def _verify_node(node: Node, payload: Dict[str, str]) -> tuple[str, bool]:
    """Realiza la verificación individual de un nodo."""

    try:
        address = str(node.address).rstrip("/")
        is_valid = _simulate_remote_verification(address, payload)
        return node.node_id, is_valid
    except httpx.HTTPError as exc:
        logger.warning(
            "verificacion_fallida", extra={"node_id": node.node_id, "error": str(exc)}
        )
        return node.node_id, False
    except Exception as exc:  # pragma: no cover - protección adicional
        logger.error(
            "error_verificacion", extra={"node_id": node.node_id, "error": str(exc)}
        )
        return node.node_id, False


def broadcast_result(node_id: str, h: str, quorum: int = 3) -> Dict[str, object]:
    """Difunde un hash al resto de nodos y consolida el resultado de consenso."""

    registry = get_registry()
    targets: List[Node] = registry.get_active_nodes(exclude=node_id)
    if not targets:
        return {"hash": h, "approved": False, "validators": []}

    payload = {"hash": h, "origin": node_id}
    validators: List[str] = []
    resultados: List[tuple[str, bool]] = []

    with ThreadPoolExecutor(max_workers=len(targets)) as executor:
        future_map = {
            executor.submit(_verify_node, nodo, payload): nodo for nodo in targets
        }
        for future in as_completed(future_map):
            node_name, aprobado = future.result()
            resultados.append((node_name, aprobado))
            if aprobado:
                validators.append(node_name)

    total_respuestas = len(resultados)
    if total_respuestas == 0:
        return {"hash": h, "approved": False, "validators": []}

    requeridas = max(quorum, math.ceil((2 * total_respuestas) / 3))
    aprobado = len(validators) >= requeridas

    logger.info(
        "resultado_consenso",
        extra={
            "hash": h,
            "aprobado": aprobado,
            "respuestas": total_respuestas,
            "validadores": validators,
        },
    )

    return {"hash": h, "approved": aprobado, "validators": validators}
