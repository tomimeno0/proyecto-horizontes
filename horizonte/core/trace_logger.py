"""Herramientas para registrar inferencias en el ledger."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any, Dict

from sqlalchemy.orm import Session

from horizonte.common.db import Ledger


def make_hash(query: str, response: str, ts: datetime) -> str:
    """Genera un hash SHA-256 inmutable para la inferencia."""
    payload = f"{ts.isoformat()}::{query}::{response}".encode("utf-8")
    return sha256(payload).hexdigest()


def persist_ledger(session: Session, query: str, response: str, hash_value: str, ts: datetime) -> Ledger:
    """Inserta una nueva entrada en el ledger."""
    registro = Ledger(query=query, response=response, hash=hash_value, timestamp=ts.isoformat())
    session.add(registro)
    session.flush()
    return registro


def serialize_record(registro: Ledger) -> Dict[str, Any]:
    """Serializa un registro del ledger a un diccionario seguro."""
    return {
        "id": registro.id,
        "query": registro.query,
        "response": registro.response,
        "hash": registro.hash,
        "timestamp": registro.timestamp,
    }
