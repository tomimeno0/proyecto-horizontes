"""Herramientas de seguridad comunes para Horizonte."""

from __future__ import annotations

import re
from hashlib import sha256

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1F\x7F]")
_WHITESPACE_RE = re.compile(r"\s{2,}")


def sanitize_input(text: str) -> str:
    """Normaliza texto eliminando caracteres potencialmente peligrosos."""
    cleaned = _CONTROL_CHARS_RE.sub(" ", text)
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def hash_text_sha256(text: str) -> str:
    """Genera un hash SHA-256 hexadecimal para el texto dado."""
    return sha256(text.encode("utf-8")).hexdigest()
