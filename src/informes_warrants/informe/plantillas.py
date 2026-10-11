"""Relleno de las plantillas Markdown de los bloques y marcadores para el analista.

Un marcador `[[ANALISTA: instrucción]]` señala lo que el SaaS no puede escribir solo.
Mientras quede alguno, el informe no se puede emitir.
"""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .secciones import BLOQUES, Tipo

DIR_PLANTILLAS = Path(__file__).resolve().parent.parent / "plantillas" / "secciones"
MARCADOR = re.compile(r"\[\[ANALISTA:\s*(.+?)\]\]", re.DOTALL)

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


_entorno.filters["num"] = _num
_entorno.filters["pct"] = _pct


def rellenar(id_bloque: str, datos: dict) -> str:
    """Rellena la plantilla del bloque con los datos calculados por el SaaS."""
    bloque = next(b for b in BLOQUES if b.id == id_bloque)
    if bloque.tipo not in (Tipo.PLANTILLA, Tipo.ANALISTA) or not bloque.plantilla:
        raise ValueError(f"El bloque {id_bloque} no usa plantilla")
    return _entorno.get_template(bloque.plantilla).render(**datos)


def pendientes(texto: str) -> list[str]:
    """Instrucciones de los marcadores que el analista aún no ha completado."""
    return [m.strip() for m in MARCADOR.findall(texto)]
