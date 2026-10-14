"""Segunda vía de cálculo del motor: el .xlsx recalculado por LibreOffice (sin interfaz) frente al evaluador en Python.

Se comparan TODAS las celdas con fórmula. Las diferencias no impiden emitir (decisión del usuario, 2026-10-14):
salen como avisos que dicen dónde está cada discrepancia. LibreOffice (MPL-2.0, gratuito) recalcula el libro al
abrirlo con un perfil propio que fuerza el recálculo de los archivos de Excel (`OOXMLRecalcMode` = siempre) y guarda
una copia con los valores en `recalculado/`; el .xlsx que descarga el analista es el original (Excel lo recalcula al abrir).
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .excel import Evaluador, iguales

log = logging.getLogger(__name__)
RUTAS = (r"C:\Program Files\LibreOffice\program\soffice.com", r"C:\Program Files\LibreOffice\program\soffice.exe",
         r"C:\Program Files (x86)\LibreOffice\program\soffice.exe", "/usr/bin/soffice", "/usr/bin/libreoffice",
         "/Applications/LibreOffice.app/Contents/MacOS/soffice")
PERFIL = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop></item>
</oor:items>
"""
TIEMPO_MAXIMO = 240  # segundos
MAX_AVISOS = 10


def soffice() -> str | None:
    """Ruta de LibreOffice (variable `SOFFICE`, rutas habituales o el PATH)."""
    for ruta in (os.environ.get("SOFFICE"), *RUTAS, shutil.which("soffice"), shutil.which("libreoffice")):
        if ruta and Path(ruta).exists():
            return ruta
    return None


def recalcular(origen: Path, destino_dir: Path) -> Path:
    """Copia de `origen` recalculada por LibreOffice en `destino_dir` (mismo nombre)."""
    ejecutable = soffice()
    if ejecutable is None:
        raise FileNotFoundError("LibreOffice no está instalado (https://www.libreoffice.org; en Windows: winget install "
                                "TheDocumentFoundation.LibreOffice)")
    destino_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="perfil_lo_") as perfil:
        usuario = Path(perfil) / "user"
        usuario.mkdir(parents=True)
        (usuario / "registrymodifications.xcu").write_text(PERFIL, encoding="utf-8")
        orden = [ejecutable, f"-env:UserInstallation={Path(perfil).as_uri()}", "--headless", "--norestore", "--nolockcheck",
                 "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", str(destino_dir), str(origen)]
        subprocess.run(orden, check=True, capture_output=True, timeout=TIEMPO_MAXIMO)
    salida = destino_dir / origen.name
    if not salida.exists():
        raise RuntimeError(f"LibreOffice no generó {salida.name}")
    return salida


def valores_guardados(ruta: Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(ruta, data_only=True)
    return {(ws.title, c.row, c.column): c.value for ws in wb.worksheets for fila in ws.iter_rows() for c in fila if c.value is not None}


def contrastar(modelo, ruta_xlsx: Path, tolerancia: float = 1e-6, absoluta: float = 1e-6) -> dict:
    """Recalcula el libro con LibreOffice y compara cada celda con fórmula con el evaluador en Python.

    Devuelve {"comparadas", "diferencias": [(celda, python, libreoffice)], "avisos", "recalculado"} o, sin LibreOffice,
    un aviso que lo dice (nunca bloquea)."""
    libro = modelo.libro.a_libro()
    formulas = [k for k, v in libro.celdas.items() if isinstance(v, str) and v.startswith("=")]
    tablas = _tablas_y_dependientes(libro)
    formulas = [k for k in formulas if k not in tablas]
    try:
        recalculado = recalcular(Path(ruta_xlsx), Path(ruta_xlsx).parent / "recalculado")
    except Exception as e:  # noqa: BLE001
        log.warning("Sin contraste con LibreOffice: %s", e)
        return {"comparadas": 0, "diferencias": [], "recalculado": None,
                "avisos": [f"Motor de valoración: sin la segunda vía de cálculo (LibreOffice): {e}"]}
    lo = valores_guardados(recalculado)
    # tolerancia relativa y absoluta de 1e-6 (importes en millones de USD: 1 USD), por los residuos de la iteración
    diferencias = [(k, modelo.valores.get(k), lo.get(k)) for k in formulas
                   if not iguales(modelo.valores.get(k), lo.get(k), tolerancia, absoluta)]
    avisos = [f"Motor de valoración: {hoja}!{_a1(f, c)} da {_corto(p)} en Python y {_corto(x)} en LibreOffice"
              for (hoja, f, c), p, x in diferencias[:MAX_AVISOS]]
    if len(diferencias) > MAX_AVISOS:
        avisos.append(f"Motor de valoración: {len(diferencias) - MAX_AVISOS} discrepancias más entre Python y LibreOffice "
                      "(lista completa en el archivo _discrepancias.csv junto al libro)")
    if tablas:
        avisos.append(f"Motor de valoración: las {len(tablas)} celdas de las tablas de sensibilidad (y lo que lee de ellas) no se "
                      "contrastan: LibreOffice no calcula las tablas de datos de Excel; las calcula Python y Excel al abrir el libro")
    return {"comparadas": len(formulas), "diferencias": diferencias, "avisos": avisos, "recalculado": recalculado,
            "sin_contraste": len(tablas)}


def _tablas_y_dependientes(libro) -> set:
    """Celdas de las tablas de datos y las fórmulas que dependen de ellas (directa o indirectamente)."""
    celdas = {(t.hoja, f, c) for t in libro.tablas for f in range(t.f1, t.f2 + 1) for c in range(t.c1, t.c2 + 1)}
    if not celdas:
        return celdas
    ev = Evaluador(libro)
    previas = {k: ev.precedentes(k) for k in ev.arboles}
    cambiado = True
    while cambiado:
        nuevas = {k for k, p in previas.items() if k not in celdas and p & celdas}
        celdas |= nuevas
        cambiado = bool(nuevas)
    return celdas


def _a1(f, c):
    from openpyxl.utils import get_column_letter

    return f"{get_column_letter(c)}{f}"


def _corto(v) -> str:
    return f"{v:,.4f}" if isinstance(v, float) else repr(v)
