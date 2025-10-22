"""Módulo de base de datos para el proyecto Horizonte."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import get_settings

settings = get_settings()
engine = create_engine(settings.db_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Clase base declarativa."""


class Ledger(Base):
    """Tabla de ledger para auditar inferencias."""

    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timestamp: Mapped[str] = mapped_column(
        String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )


def init_db() -> None:
    """Inicializa la base de datos en entornos de desarrollo."""
    if settings.env == "dev":
        Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Provee una sesión de base de datos gestionada."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - la excepción se relanza para trazabilidad
        session.rollback()
        raise
    finally:
        session.close()
