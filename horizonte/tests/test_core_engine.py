"""Pruebas del núcleo de inferencia y trazabilidad."""

from __future__ import annotations

from datetime import datetime, timezone

from horizonte.core.inference_engine import infer
from horizonte.core.trace_logger import make_hash


def test_infer_produce_respuesta_determinista() -> None:
    """La inferencia debe ser determinista para la misma consulta."""
    consulta = "Impacto de la deforestación"
    respuesta_1 = infer(consulta)
    respuesta_2 = infer(consulta)
    assert respuesta_1 == respuesta_2
    assert respuesta_1


def test_make_hash_longitud_correcta() -> None:
    """El hash generado debe tener 64 caracteres hexadecimales."""
    ts = datetime.now(timezone.utc)
    hash_value = make_hash("q", "r", ts)
    assert len(hash_value) == 64
    int(hash_value, 16)
