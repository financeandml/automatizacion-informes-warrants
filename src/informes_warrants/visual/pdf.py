"""HTML → PDF con WeasyPrint (patrón de equity-research-agent `combine_reports`, MIT).

Se pasa el documento HTML completo, con <head> y charset (el original usaba el fragmento sin
cabecera, que rompe los acentos). En Windows, WeasyPrint necesita las DLL de GTK/Pango de MSYS2
(ver README); si existen en la ruta estándar, se configuran solas.
"""

import logging
import os
import sys
from pathlib import Path

RUTA_GTK_WINDOWS = Path(r"C:\msys64\mingw64\bin")


def _preparar_gtk() -> None:
    if sys.platform == "win32" and "WEASYPRINT_DLL_DIRECTORIES" not in os.environ and RUTA_GTK_WINDOWS.is_dir():
        os.environ["WEASYPRINT_DLL_DIRECTORIES"] = str(RUTA_GTK_WINDOWS)


def ejecutable_weasyprint() -> Path | None:
    """C3: WeasyPrint autónomo para Windows (trae GTK dentro), si se instaló con instalar.ps1 o WEASYPRINT_EXE."""
    from ..config import directorio_datos

    for ruta in (os.environ.get("WEASYPRINT_EXE"), directorio_datos() / "weasyprint" / "weasyprint.exe"):
        if ruta and Path(ruta).is_file():
            return Path(ruta)
    return None


def _con_ejecutable(exe: Path, html: str, base_url) -> bytes:
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        entrada, salida = Path(tmp) / "informe.html", Path(tmp) / "informe.pdf"
        entrada.write_text(html, encoding="utf-8")
        orden = [str(exe), str(entrada), str(salida)] + (["-u", str(base_url)] if base_url else [])
        subprocess.run(orden, check=True, capture_output=True, timeout=600)
        return salida.read_bytes()


def html_a_pdf(html: str, destino: Path | None = None, base_url: str | Path | None = None) -> bytes:
    """Genera el PDF; lo guarda en `destino` si se indica y devuelve sus bytes. Sin GTK en Windows, con el ejecutable
    autónomo de WeasyPrint (misma versión) si está instalado."""
    _preparar_gtk()
    try:
        from weasyprint import HTML
    except OSError:  # faltan las bibliotecas de GTK/Pango
        exe = ejecutable_weasyprint()
        if exe is None:
            raise
        pdf = _con_ejecutable(exe, html, base_url)
        if destino:
            Path(destino).write_bytes(pdf)
        return pdf

    # Los SVG de matplotlib llevan propiedades de presentación en `style` (stroke, text-anchor…) que el
    # analizador CSS de WeasyPrint avisa como desconocidas aunque las dibuja bien: solo se muestran errores.
    logging.getLogger("weasyprint").setLevel(logging.ERROR)
    pdf = HTML(string=html, base_url=str(base_url) if base_url else None).write_pdf()
    if destino:
        Path(destino).write_bytes(pdf)
    return pdf
