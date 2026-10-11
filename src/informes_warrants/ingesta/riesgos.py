"""Títulos de los factores de riesgo del 10-K (Item 1A), sin IA.

Las empresas escriben cada riesgo como una frase en negrita o cursiva seguida de su desarrollo.
Se buscan esas frases en el HTML del filing y se conservan solo las que aparecen en el texto del
Item 1A que extrae edgartools (`TenK.risk_factors`). El resultado es la lista completa de riesgos
declarados, literal, que alimenta el bloque AUTO «riesgos.lista» y la selección de la IA.
"""

import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

LONGITUD_MIN, LONGITUD_MAX = 40, 600


def normalizar(texto: str) -> str:
    """Espacios y comillas tipográficas unificados para comparar textos de la SEC."""
    texto = texto.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(texto.split())


def _destacado(tag) -> bool:
    estilo = (tag.get("style") or "").replace(" ", "").lower()
    return (tag.name in ("b", "strong", "i", "em") or "font-weight:700" in estilo
            or "font-weight:bold" in estilo or "font-style:italic" in estilo)


def titulos_de_riesgo(html: str, texto_item_1a: str) -> list[str]:
    """Frases destacadas del Item 1A, en orden y sin duplicados."""
    item = normalizar(texto_item_1a)
    vistos, titulos = set(), []
    with warnings.catch_warnings():  # los iXBRL son XHTML; se leen como HTML a propósito para ver los estilos
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        sopa = BeautifulSoup(html, "lxml")
    for tag in sopa.find_all(["span", "b", "strong", "i", "em", "font"]):
        if not _destacado(tag):
            continue
        frase = normalizar(tag.get_text(" "))
        if (LONGITUD_MIN <= len(frase) <= LONGITUD_MAX and re.search(r"[.:]$", frase)
                and frase not in vistos and frase in item):
            vistos.add(frase)
            titulos.append(frase)
    return titulos


FORMULARIOS_ANUALES = ["10-K", "20-F", "40-F"]


def riesgos_anuales(ticker: str) -> tuple[list[str], str, str]:
    """(títulos, texto de riesgos, accession) del último informe anual: 10-K (Item 1A) o 20-F (Item 3.D).

    Sin enmiendas (las 10-K/A no traen el Item 1A). Si la empresa remite sus riesgos a un anexo
    (p. ej., NVO o muchos 40-F), la lista sale vacía y el bloque pasa al analista.
    Requiere EDGAR_IDENTITY.
    """
    from edgar import Company

    filing = Company(ticker).get_filings(form=FORMULARIOS_ANUALES, amendments=False).latest()
    texto = getattr(filing.obj(), "risk_factors", None) or ""
    return titulos_de_riesgo(filing.html(), texto), texto, filing.accession_no
