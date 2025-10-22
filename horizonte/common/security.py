"""Utilidades de seguridad para el proyecto Horizonte."""

from __future__ import annotations

import hashlib
import re
from typing import Final

_ALLOWED_CONTROL_CHARS: Final[set[str]] = {"\n", "\t", " "}
_DOUBLE_SPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r" {2,}")


def sanitize_input(text: str) -> str:
    """Limpia caracteres de control y espacios duplicados de un texto."""

    if not text:
        return ""

    cleaned_chars = []
    for char in text:
        if char in _ALLOWED_CONTROL_CHARS:
            cleaned_chars.append(char)
            continue
        if char.isprintable():
            cleaned_chars.append(char)

    cleaned = "".join(cleaned_chars)
    cleaned = _DOUBLE_SPACE_PATTERN.sub(" ", cleaned)
    return cleaned.strip()


def hash_text_sha256(text: str) -> str:
    """Calcula el hash SHA-256 de un texto en UTF-8 y lo devuelve en hexadecimal."""

    digest = hashlib.sha256(text.encode("utf-8"))
    return digest.hexdigest()


__all__ = ["sanitize_input", "hash_text_sha256"]
