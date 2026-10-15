"""Observabilidad (C8): registro de errores, tiempos de cada etapa y diagnóstico de la instalación.

- Registro: `directorio_datos()/registro/informes-warrants.log`, rotativo (5 × 1 MB), fuera de OneDrive y del
  repositorio. Nunca se registran claves ni textos del analista: solo etapas, tiempos y errores.
- Tiempos: cada etapa (reunir, componer, pdf, excel, ia) añade una línea a `tiempos.jsonl` (`medir`).
- Diagnóstico: `informes-warrants diagnostico` y la pantalla de Configuración comprueban lo que hace falta para que
  todo funcione (Python, dependencias, PDF, LibreOffice, identidad de EDGAR, claves presentes) y resumen los tiempos.
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler

log = logging.getLogger("informes_warrants")
_configurado = False


def carpeta():
    from .config import directorio_datos

    c = directorio_datos() / "registro"
    c.mkdir(parents=True, exist_ok=True)
    return c


def configurar_registro(nivel: int = logging.INFO) -> None:
    """Añade el registro rotativo a los mensajes del paquete (una vez por proceso)."""
    global _configurado
    if _configurado:
        return
    manejador = RotatingFileHandler(carpeta() / "informes-warrants.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    manejador.setLevel(nivel)
    log.addHandler(manejador)
    log.setLevel(min(log.level or logging.WARNING, nivel))
    _configurado = True


@contextmanager
def medir(etapa: str, **etiquetas):
    """Tiempo de una etapa (y si falló), en tiempos.jsonl; los errores se registran y se propagan."""
    inicio, error = time.perf_counter(), None
    try:
        yield
    except Exception as e:
        error = type(e).__name__
        log.exception("Error en %s %s", etapa, etiquetas)
        raise
    finally:
        segundos = round(time.perf_counter() - inicio, 2)
        try:
            with open(carpeta() / "tiempos.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"fecha": datetime.now().isoformat(timespec="seconds"), "etapa": etapa, "segundos": segundos,
                                    "error": error, **{k: str(v) for k, v in etiquetas.items()}}, ensure_ascii=False) + "\n")
        except OSError:
            pass


def resumen_tiempos(ultimos: int = 200) -> dict[str, dict]:
    """Por etapa: número de ejecuciones, mediana y máximo de segundos y errores (de las últimas `ultimos`)."""
    import statistics

    ruta = carpeta() / "tiempos.jsonl"
    if not ruta.exists():
        return {}
    filas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines()[-ultimos:] if x.strip()]
    salida = {}
    for etapa in sorted({f["etapa"] for f in filas}):
        t = [f["segundos"] for f in filas if f["etapa"] == etapa]
        salida[etapa] = {"n": len(t), "mediana": statistics.median(t), "maximo": max(t),
                         "errores": sum(1 for f in filas if f["etapa"] == etapa and f.get("error"))}
    return salida


def diagnostico() -> list[tuple[str, bool, str]]:
    """(comprobación, correcta, detalle) de todo lo que necesita el SaaS en este equipo."""
    import importlib
    import os
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    filas = [("Python 3.11 o superior", sys.version_info >= (3, 11), sys.version.split()[0])]
    for modulo in ("edgar", "openpyxl", "matplotlib", "streamlit", "yfinance"):
        try:
            m = importlib.import_module(modulo)
            filas.append((f"Paquete {modulo}", True, getattr(m, "__version__", "instalado")))
        except Exception as e:  # noqa: BLE001
            filas.append((f"Paquete {modulo}", False, f"no instalado ({e}); ejecuta: pip install -e \".[pdf,ui]\""))
    try:
        from .visual.pdf import html_a_pdf

        html_a_pdf("<p>prueba</p>")
        filas.append(("PDF (WeasyPrint y GTK)", True, "funciona"))
    except Exception as e:  # noqa: BLE001
        filas.append(("PDF (WeasyPrint y GTK)", False, f"{type(e).__name__}: en Windows instala GTK (README, «Instalación»)"))
    from .calculo.motor.recalculo import soffice

    ruta = soffice()
    filas.append(("LibreOffice (segunda vía del modelo, opcional)", ruta is not None,
                  ruta or "no instalado: el modelo se contrasta solo en Python"))
    identidad = os.getenv("EDGAR_IDENTITY")
    filas.append(("Identidad de EDGAR (obligatoria para la SEC)", bool(identidad and "@" in identidad),
                  "configurada" if identidad else "falta: Configuración → Conexiones, o EDGAR_IDENTITY en .env"))
    for clave, uso in (("GEMINI_API_KEY", "Gemini (borradores, consenso)"), ("GROQ_API_KEY", "Groq (respaldo de la IA)")):
        filas.append((f"Clave {clave} (opcional: {uso})", bool(os.getenv(clave)), "presente" if os.getenv(clave) else "no configurada"))
    from .config import directorio_datos

    datos = directorio_datos()
    filas.append(("Carpeta de datos (fuera de OneDrive)", "onedrive" not in str(datos).lower(), str(datos)))
    return filas


def medido(etapa: str):
    """Decorador de `medir`: con el ticker como etiqueta si el primer argumento es un texto."""
    import functools

    def decorador(funcion):
        @functools.wraps(funcion)
        def envoltura(*args, **kwargs):
            etiquetas = {"ticker": args[0]} if args and isinstance(args[0], str) and len(args[0]) <= 6 else {}
            with medir(etapa, **etiquetas):
                return funcion(*args, **kwargs)
        return envoltura
    return decorador
