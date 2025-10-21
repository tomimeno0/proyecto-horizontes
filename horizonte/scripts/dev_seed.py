"""Script para poblar el ledger con datos de desarrollo."""

from __future__ import annotations

from datetime import datetime, timezone

from horizonte.common.db import get_session
from horizonte.core.trace_logger import make_hash, persist_ledger


REGISTROS = [
    ("¿Qué es Horizonte?", "Horizonte es una IA auditable enfocada en transparencia."),
    ("Impacto social", "El proyecto promueve gobernanza participativa en IA."),
]


def poblar() -> None:
    """Inserta registros de ejemplo en la base de datos."""
    with get_session() as session:
        for query, response in REGISTROS:
            ts = datetime.now(timezone.utc)
            hash_value = make_hash(query, response, ts)
            persist_ledger(session, query, response, hash_value, ts)
    print("Ledger poblado con datos de desarrollo.")


if __name__ == "__main__":  # pragma: no cover - ejecución manual
    poblar()
