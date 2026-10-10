"""Configuración del acceso a EDGAR."""

import os

from dotenv import load_dotenv


class ConfiguracionError(RuntimeError):
    """Falta configuración necesaria para operar."""


def configurar_identidad() -> str:
    """Carga EDGAR_IDENTITY desde el entorno (o .env) y la registra en edgartools."""
    load_dotenv()
    identidad = os.getenv("EDGAR_IDENTITY", "").strip()
    if not identidad or "@" not in identidad:
        raise ConfiguracionError(
            "Define EDGAR_IDENTITY en .env con el formato 'Nombre Apellido email@dominio.com' "
            "(la SEC lo exige en cada petición)."
        )

    from edgar import set_identity

    set_identity(identidad)
    return identidad
