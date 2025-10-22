"""Simulación de red para llamadas entre nodos Horizonte."""

from __future__ import annotations

import logging
import os
import random
from typing import Any, Dict

import anyio

logger = logging.getLogger("sim_net")


def _get_float_env(name: str, default: float) -> float:
    """Obtiene una configuración flotante tolerante a errores."""

    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("invalid_sim_setting", extra={"name": name, "value": raw})
        return default


async def simulate_call(address: str, payload: Dict[str, Any] | None = None) -> bool:
    """Simula una llamada remota con latencia y fallos probabilísticos."""

    min_latency = _get_float_env("SIM_LATENCY_MS_MIN", 40.0)
    max_latency = max(min_latency, _get_float_env("SIM_LATENCY_MS_MAX", 250.0))
    drop_rate = min(max(_get_float_env("SIM_DROP_RATE", 0.1), 0.0), 1.0)

    latency_ms = random.uniform(min_latency, max_latency)
    await anyio.sleep(latency_ms / 1000)

    if random.random() < drop_rate:
        logger.info(
            "simulated_drop",
            extra={"address": address, "latency_ms": round(latency_ms, 2)},
        )
        raise TimeoutError(f"Simulated drop when contacting {address}")

    logger.debug(
        "simulated_call_ok",
        extra={"address": address, "latency_ms": round(latency_ms, 2)},
    )
    return True


__all__ = ["simulate_call"]

