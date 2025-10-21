"""Configuraciones centrales para el proyecto Horizonte."""

from __future__ import annotations

from functools import lru_cache
from typing import List
from uuid import uuid4

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configura la aplicación utilizando variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Proyecto Horizonte", validation_alias="APP_NAME")
    env: str = Field(default="dev", validation_alias="ENV")
    db_url: str = Field(default="sqlite:///./ledger.db", validation_alias="DB_URL")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    cors_origins_raw: str = Field(default="", validation_alias="CORS_ORIGINS")
    rate_limit: str = Field(default="60/minute", validation_alias="RATE_LIMIT")
    node_id: str = Field(default="", validation_alias="NODE_ID")
    max_payload_bytes: int = Field(default=1_048_576, validation_alias="MAX_PAYLOAD_BYTES")

    @field_validator("env")
    @classmethod
    def validar_env(cls, value: str) -> str:
        """Valida el entorno permitido."""
        if value not in {"dev", "prod"}:
            raise ValueError("ENV debe ser 'dev' o 'prod'.")
        return value

    @field_validator("log_level")
    @classmethod
    def validar_nivel(cls, value: str) -> str:
        """Valida el nivel de log permitido."""
        niveles = {"INFO", "DEBUG", "WARNING", "ERROR"}
        valor = value.upper()
        if valor not in niveles:
            raise ValueError("LOG_LEVEL debe ser INFO, DEBUG, WARNING o ERROR.")
        return valor

    @field_validator("cors_origins_raw")
    @classmethod
    def normalizar_origenes(cls, value: str) -> str:
        """Normaliza la lista de orígenes admitidos."""
        return value.strip()

    @field_validator("node_id", mode="after")
    @classmethod
    def generar_node_id(cls, value: str) -> str:
        """Genera un identificador de nodo si no se proporciona uno."""
        return value or str(uuid4())

    @property
    def cors_origins(self) -> List[str]:
        """Retorna la lista de orígenes para CORS."""
        if not self.cors_origins_raw:
            return []
        return [origen.strip() for origen in self.cors_origins_raw.split(",") if origen.strip()]


@lru_cache
def get_settings() -> Settings:
    """Obtiene una instancia cacheada de la configuración."""
    try:
        return Settings()
    except ValidationError as exc:  # pragma: no cover - configuración inválida debe ser evidente
        raise RuntimeError(f"Configuración inválida: {exc}") from exc
