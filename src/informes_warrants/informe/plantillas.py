"""Relleno de las plantillas Markdown de los bloques y marcadores para el analista.

Un marcador `[[ANALISTA: instrucción]]` señala lo que el SaaS no puede escribir solo.
Mientras quede alguno, el informe muestra el recuadro y lo avisa antes de emitir (no bloquea desde el 2026-10-14).
"""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .secciones import BLOQUES, Tipo

DIR_PLANTILLAS = Path(__file__).resolve().parent.parent / "plantillas" / "secciones"
MARCADOR = re.compile(r"\[\[ANALISTA:\s*(.+?)\]\]", re.DOTALL)
# Borrador de la IA para un apartado del analista (decisión del usuario, 2026-10-14): `[[IA: instrucción || borrador]]`.
# Sigue siendo tarea del analista: cuenta como pendiente hasta que lo revise (y no impide emitir).
MARCADOR_IA = re.compile(r"\[\[IA:\s*(.+?)\s*\|\|\s*(.+?)\]\]", re.DOTALL)

_entorno = Environment(
    loader=FileSystemLoader(DIR_PLANTILLAS),
    undefined=StrictUndefined,  # un dato que falta es un error, nunca un hueco silencioso
    keep_trailing_newline=True,
    autoescape=False,
)


def _num(valor, decimales: int = 1) -> str:
    """Formato español: coma decimal, punto de miles, negativos entre paréntesis."""
    if valor is None:
        return "n.d."
    texto = f"{abs(valor):,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"({texto})" if valor < 0 else texto


def _pct(valor, decimales: int = 1) -> str:
    return "n.d." if valor is None else f"{_num(valor * 100, decimales)} %"


def _var(valor, decimales: int = 1) -> str:
    """Variación con signo explícito para el texto corrido (+15,2 % / −72,5 %); las tablas usan paréntesis."""
    if valor is None:
        return "n.d."
    texto = f"{abs(valor) * 100:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{'+' if valor > 0 else '−' if valor < 0 else ''}{texto} %"


_entorno.filters.update(num=_num, pct=_pct, var=_var)


def rellenar(id_bloque: str, datos: dict) -> str:
    """Rellena la plantilla del bloque con los datos calculados por el SaaS."""
    bloque = next(b for b in BLOQUES if b.id == id_bloque)
    if bloque.tipo not in (Tipo.PLANTILLA, Tipo.ANALISTA) or not bloque.plantilla:
        raise ValueError(f"El bloque {id_bloque} no usa plantilla")
    return _entorno.get_template(bloque.plantilla).render(**datos)


def pendientes(texto: str) -> list[str]:
    """Instrucciones de los marcadores que el analista aún no ha completado (y borradores de la IA sin revisar)."""
    return ([m.strip() for m in MARCADOR.findall(texto)]
            + [f"revisar el borrador de la IA ({instruccion.strip()})" for instruccion, _ in MARCADOR_IA.findall(texto)])


def con_borradores(texto: str, borradores: dict[str, str]) -> str:
    """Sustituye cada marcador del analista que tiene borrador de la IA por `[[IA: instrucción || borrador]]`."""
    def sustituir(m):
        instruccion = m.group(1).strip()
        return f"[[IA: {instruccion} || {borradores[instruccion]}]]" if borradores.get(instruccion) else m.group(0)

    return MARCADOR.sub(sustituir, texto)


def sin_marcas_ia(texto: str) -> str:
    """El texto con cada borrador de la IA en limpio (para que el analista lo edite)."""
    return MARCADOR_IA.sub(lambda m: m.group(2).strip(), texto)
