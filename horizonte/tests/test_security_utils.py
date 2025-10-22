"""Pruebas unitarias para utilidades de seguridad."""

from __future__ import annotations

from horizonte.common.security import hash_text_sha256, sanitize_input


def test_sanitize_input_remueve_control() -> None:
    """Los caracteres no imprimibles deben eliminarse."""

    texto = "Hola\x00 Mundo  \n"
    resultado = sanitize_input(texto)
    assert resultado == "Hola Mundo"


def test_hash_text_sha256_constante() -> None:
    """El hash debe ser determinista para entradas conocidas."""

    esperado = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert hash_text_sha256("abc") == esperado
