"""Datos de la ficha de empresa (apartado 1) que no son estados financieros: bolsa, cierre del ejercicio y empleados.

- Bolsa: la que declara la SEC para cada ticker de la empresa (edgartools `Company.get_exchanges`).
- Cierre del ejercicio: el del último 10-K.
- Empleados: no hay tag US GAAP (solo IFRS, `NumberOfEmployees`); se toma la frase literal del Item 1 («Human Capital»)
  donde la empresa los declara, y su primera cifra (sin fechas). Si no la encuentra, «n.d.»: el analista la completa.
"""

import re
from dataclasses import dataclass
from datetime import date

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
_PLANTILLA = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{2,7})\s+(?:full[- ]time(?:[- ]equivalent)?\s+|total\s+|regular\s+)?"
                        r"(?:employees|people|associates|team members|colleagues|workers)\b", re.I)
_CONTEXTO = re.compile(r"employ|workforce|headcount|\bhad\b|approximately", re.I)
_CIFRA = re.compile(r"(?<![\d,.])(\d{1,3}(?:,\d{3})+|\d{3,7})(?![\d,])")


@dataclass(frozen=True)
class Empleados:
    numero: int
    frase: str  # literal del Item 1 del 10-K


def empleados(texto_negocio: str) -> Empleados | None:
    """Plantilla declarada en el Item 1: la primera frase que la cifra y su primera cifra que no sea un año."""
    texto = (texto_negocio or "").replace("\xa0", " ")
    for frase in re.split(r"(?<=[.;])\s+", texto):
        if not (_PLANTILLA.search(frase) and _CONTEXTO.search(frase)):
            continue
        for m in _CIFRA.finditer(frase):
            valor = int(m.group(1).replace(",", ""))
            if not 1900 <= valor <= 2100:  # años de «As of December 31, 2025»
                return Empleados(valor, " ".join(frase.split()))
    return None


def cierre_fiscal(cierre: str | date | None) -> str | None:
    """«26 de septiembre» a partir del cierre del último ejercicio."""
    if not cierre:
        return None
    d = cierre if isinstance(cierre, date) else date.fromisoformat(str(cierre)[:10])
    return f"{d.day} de {MESES[d.month - 1]}"


def bolsa(empresa) -> str | None:
    try:
        return ", ".join(dict.fromkeys(empresa.get_exchanges() or [])) or None
    except Exception:  # noqa: BLE001  (sin dato de la SEC: la ficha lo omite)
        return None


_NUMEROS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twenty": 20}
_ADS = re.compile(r"\b(?:each|one|every)\s+(?:ADS|ADR|American\s+Depositary\s+(?:Share|Receipt))s?\b[^.;]{0,40}?\brepresents?\s+"
                  r"(?P<n>\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|twenty)(?:\s*\(\d+\))?"
                  r"(?:\s+[A-Za-z-]+){0,4}?\s+shares?\b", re.I)  # «one deposited Novo Nordisk B share»


def acciones_por_ads(texto: str) -> tuple[float, str] | None:
    """Acciones ordinarias por ADS que declara el 20-F (p. ej. TSM: «each ADS represents five (5) common shares»)."""
    m = _ADS.search(" ".join((texto or "").replace("\xa0", " ").split()))
    if not m:
        return None
    n = m.group("n").lower()
    return float(_NUMEROS.get(n) or n), m.group(0)
