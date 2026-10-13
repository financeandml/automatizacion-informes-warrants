"""Apartado «Competition» del Item 1 del 10-K (A5), extraído literalmente y por código.

El texto del Item 1 lo da edgartools (`TenK.business`). Cada apartado empieza en una línea propia
«Competition» y termina en el siguiente encabezado: una línea corta sin punto final (p. ej. «Supply of
Components» en AAPL, «Intelligent Cloud» en MSFT). Si el apartado empieza con un subencabezado («Automotive» en
TSLA), los siguientes subencabezados cuya primera frase trata de competencia siguen dentro. Se saltan los pies
de página («Apple Inc. | 2025 Form 10-K | 2») y los números de página. Si la empresa tiene varios apartados
(uno por segmento, como MSFT), se toman todos en orden. La IA solo traduce este texto (ia/bloques.py); nunca lo elige ni lo amplía.
"""

import re

ENCABEZADO = re.compile(r"\s*#*\s*\**\s*competition\s*\**\s*[:.]?\s*", re.I)
PIE_DE_PAGINA = re.compile(r"(form 10-k|^\s*\d{1,3}\s*$|^\s*page \d+)", re.I)
MAX_ENCABEZADO = 70  # caracteres: más largo es un párrafo, no un encabezado
MAX_CARACTERES = 6000  # el texto traducido cabe en media página; si es más largo se corta en un párrafo completo


COMPETENCIA = re.compile(r"compet", re.I)


def _siguiente_parrafo(lineas: list[str], desde: int) -> str:
    return next((x.strip() for x in lineas[desde:] if x.strip() and not PIE_DE_PAGINA.search(x)), "")


def _es_encabezado(linea: str) -> bool:
    texto = linea.strip()
    return bool(texto) and len(texto) <= MAX_ENCABEZADO and not texto.endswith((".", ":", ";", ",")) and texto[0].isupper()


def apartado_competencia(texto_item_1: str) -> dict | None:
    """{"texto": párrafos literales, "recortado": bool, "apartados": n} o None si el Item 1 no tiene el apartado."""
    lineas = (texto_item_1 or "").split("\n")
    parrafos, apartados, i = [], 0, 0
    while i < len(lineas):
        if ENCABEZADO.fullmatch(lineas[i]):
            apartados += 1
            i += 1
            con_subapartados = _es_encabezado(_siguiente_parrafo(lineas, i))  # TSLA: «Competition» → «Automotive» → …
            while i < len(lineas) and not ENCABEZADO.fullmatch(lineas[i]):
                linea = lineas[i].strip()
                if linea and not PIE_DE_PAGINA.search(linea):
                    siguiente = _siguiente_parrafo(lineas, i + 1)
                    if _es_encabezado(linea) and not siguiente[:1].islower():  # en minúscula: párrafo partido por la página
                        primera_frase = re.split(r"(?<=\.)\s", _siguiente_parrafo(lineas, i + 1), maxsplit=1)[0]
                        if not (con_subapartados and COMPETENCIA.search(primera_frase)):  # otro apartado del Item 1: fin
                            break
                        parrafos.append(f"**{linea}.**")
                        i += 1
                        continue
                    if parrafos and linea[0].islower():  # párrafo partido por un salto de página
                        parrafos[-1] += " " + linea
                    else:
                        parrafos.append(linea)
                i += 1
            continue
        i += 1
    if not parrafos:
        return None
    texto, recortado = "", False
    for p in parrafos:
        if len(texto) + len(p) > MAX_CARACTERES and texto:
            recortado = True
            break
        texto += ("\n\n" if texto else "") + p
    return {"texto": texto, "recortado": recortado, "apartados": apartados}
