"""Motor de inferencia simulado para Horizonte."""

from __future__ import annotations

import unicodedata

MAX_QUERY_LENGTH = 8000


def _sanear_query(query: str) -> str:
    """Normaliza la consulta eliminando espacios redundantes."""
    texto = unicodedata.normalize("NFKC", query).strip()
    if not texto:
        raise ValueError("La consulta no puede estar vacía tras la normalización.")
    if len(texto) > MAX_QUERY_LENGTH:
        raise ValueError("La consulta excede el tamaño máximo permitido.")
    return texto


def infer(query: str) -> str:
    """Genera una respuesta determinista a partir de la consulta."""
    consulta_limpia = _sanear_query(query)
    resumen = consulta_limpia[:120]
    return (
        "Horizonte responde con una síntesis responsable: "
        f"{resumen} | Huella semántica: {len(consulta_limpia)} tokens aproximados."
    )
