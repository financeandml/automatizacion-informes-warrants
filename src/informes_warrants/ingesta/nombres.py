"""Nombre de la empresa para el informe (A15): la SEC registra muchos en mayúsculas («IOVANCE BIOTHERAPEUTICS, INC.»).

Solo se toca un nombre escrito entero en mayúsculas: cada palabra pasa a minúscula con inicial mayúscula, salvo
las siglas (palabras de hasta 3 letras que no son formas societarias ni artículos: IBM, HP, AMC) y las que llevan
«&» o cifras (AT&T, 3M). Un nombre que ya trae minúsculas («Apple Inc.») se deja tal cual.
"""

import re

# Formas societarias y palabras cortas que no son siglas: se escriben con su forma habitual
FORMAS = {"INC": "Inc", "CO": "Co", "CORP": "Corp", "LTD": "Ltd", "LLC": "LLC", "PLC": "plc", "LP": "LP", "NV": "N.V",
          "SA": "S.A", "AG": "AG", "SE": "SE", "THE": "The", "OF": "of", "AND": "and", "DE": "de", "DEL": "del"}
SIGLA_MAX = 3


def _palabra(p: str, primera: bool) -> str:
    base = p.rstrip(".,")
    resto = p[len(base):]
    if not base:
        return p
    if base.upper() in FORMAS:
        forma = FORMAS[base.upper()]
        return (forma[0].upper() + forma[1:] if primera else forma) + resto
    if "&" in base or re.search(r"\d", base) or len(base) <= SIGLA_MAX:
        return p
    return "-".join(s[:1] + s[1:].lower() for s in base.split("-")) + resto


SUFIJO_ESTADO = re.compile(r"\s*/\s*[A-Za-z]{2,4}\s*/?\s*$")  # «/DE/», «/ DE», «/NEW/»: estado de constitución en EDGAR


def nombre_legible(nombre: str | None) -> str:
    nombre = SUFIJO_ESTADO.sub("", nombre or "").strip()
    if not nombre or nombre != nombre.upper() or not re.search(r"[A-Z]", nombre):
        return nombre
    return " ".join(_palabra(p, i == 0) for i, p in enumerate(nombre.split()))
