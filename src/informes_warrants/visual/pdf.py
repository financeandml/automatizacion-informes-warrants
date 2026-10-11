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


def html_a_pdf(html: str, destino: Path | None = None, base_url: str | Path | None = None) -> bytes:
    """Genera el PDF; lo guarda en `destino` si se indica y devuelve sus bytes."""
    _preparar_gtk()
    from weasyprint import HTML

    # Los SVG de matplotlib llevan propiedades de presentación en `style` (stroke, text-anchor…) que el
    # analizador CSS de WeasyPrint avisa como desconocidas aunque las dibuja bien: solo se muestran errores.
    logging.getLogger("weasyprint").setLevel(logging.ERROR)
    pdf = HTML(string=html, base_url=str(base_url) if base_url else None).write_pdf()
    if destino:
        Path(destino).write_bytes(pdf)
    return pdf
