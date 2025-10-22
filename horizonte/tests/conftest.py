"""Configuraciones compartidas para las pruebas de Horizonte."""

from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Limita las pruebas de AnyIO a usar asyncio."""
    return "asyncio"
