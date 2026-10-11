"""Configuración: identidad ante la SEC y carpeta de datos local."""

import os
from pathlib import Path

from dotenv import load_dotenv
from platformdirs import user_data_dir


class ConfiguracionError(RuntimeError):
    """Falta configuración necesaria para operar."""


def configurar_identidad() -> str:
    """Carga EDGAR_IDENTITY desde el entorno (o .env) y la registra en edgartools."""
    load_dotenv()
    identidad = os.getenv("EDGAR_IDENTITY", "").strip()
    if not identidad or "@" not in identidad:
        raise ConfiguracionError(
            "Define EDGAR_IDENTITY en .env con el formato 'Nombre email@dominio.com' "
            "(la SEC lo exige en cada petición)."
        )

    from edgar import set_identity

    set_identity(identidad)
    return identidad


def directorio_datos() -> Path:
    """Carpeta de la base de datos, snapshots y PDFs.

    Se usa INFORMES_DATA_DIR si está definida; si no, la carpeta de datos del usuario
    del sistema operativo (fuera de OneDrive, cuya sincronización puede corromper SQLite).
    """
    load_dotenv()
    ruta = Path(os.getenv("INFORMES_DATA_DIR") or user_data_dir("informes-warrants", appauthor=False))
    if "onedrive" in str(ruta).lower():
        raise ConfiguracionError(
            f"La carpeta de datos {ruta} está dentro de OneDrive; usa una ruta local en INFORMES_DATA_DIR."
        )
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta
