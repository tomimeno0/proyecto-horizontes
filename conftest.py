import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Fuerza a AnyIO a utilizar el backend de asyncio durante las pruebas."""

    return "asyncio"
