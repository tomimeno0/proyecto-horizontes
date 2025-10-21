"""Módulo para explicar respuestas del motor de inferencia."""

from __future__ import annotations

from typing import Dict, List


def explain(query: str, response: str) -> Dict[str, object]:
    """Construye una explicación humanamente legible de la respuesta."""
    rasgos: List[str] = ["tokens_simulados", "ideas_clave"]
    return {
        "respuesta": response,
        "rasgos": rasgos,
        "nivel_confianza": 0.85,
        "nota_sesgo": "científico-occidental (simulado)",
        "fuente_consulta": query,
    }
