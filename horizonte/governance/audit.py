"""Funciones de auditoría ampliada para gobernanza."""

from __future__ import annotations

from collections import Counter
from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from horizonte.common.db import Ledger


def export_audit_json(session: Session, limite: int = 50) -> Dict[str, object]:
    """Exporta un resumen de auditoría con métricas básicas."""
    consulta = select(Ledger).order_by(Ledger.id.desc()).limit(limite)
    registros = session.execute(consulta).scalars().all()
    contador = Counter(registro.query for registro in registros)
    return {
        "total_registros": len(registros),
        "top_consultas": contador.most_common(5),
        "items": [
            {
                "id": registro.id,
                "query": registro.query,
                "response": registro.response,
                "hash": registro.hash,
                "timestamp": registro.timestamp,
            }
            for registro in registros
        ],
    }
