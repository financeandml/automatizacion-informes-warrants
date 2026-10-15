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


CONEXIONES = ("EDGAR_IDENTITY", "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY")


def ruta_env() -> Path:
    """El .env del proyecto (ignorado por git): el que encuentre python-dotenv o, si no hay, en la raíz del repositorio."""
    from dotenv import find_dotenv

    encontrado = find_dotenv(usecwd=True) or find_dotenv()
    return Path(encontrado) if encontrado else Path(__file__).resolve().parents[2] / ".env"


def guardar_conexiones(valores: dict[str, str]) -> Path:
    """Escribe en .env las conexiones dadas (vacías = no se tocan) conservando el resto de líneas, y las carga."""
    ruta = ruta_env()
    lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
    for clave, valor in valores.items():
        valor = (valor or "").strip()
        if clave not in CONEXIONES or not valor:
            continue
        nueva = f'{clave}="{valor}"' if " " in valor else f"{clave}={valor}"
        indice = next((i for i, x in enumerate(lineas) if x.split("=", 1)[0].strip() == clave), None)
        if indice is None:
            lineas.append(nueva)
        else:
            lineas[indice] = nueva
        os.environ[clave] = valor
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta
