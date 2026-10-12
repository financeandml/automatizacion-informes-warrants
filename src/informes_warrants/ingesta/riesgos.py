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
# Similitud de títulos (0-1) calibrada con AAPL 2025 frente a 2024 (tests/test_red.py):
IGUAL, MODIFICADO, POSIBLE_REFORMULACION = 0.98, 0.75, 0.60
VACIAS = frozenset("""the company company's companys and that could which with from other their this these those such its
may can are for has have been into than will would upon about including include includes inc""".split())


def _palabras(texto: str) -> set[str]:
    """Palabras con contenido, sin plural final: «markets» y «market» cuentan igual."""
    palabras = re.findall(r"[a-z]+", normalizar(texto).lower())
    return {p[:-1] if p.endswith("s") and len(p) > 4 else p for p in palabras if len(p) > 2 and p not in VACIAS}


def _caracteres(a: str, b: str) -> float:
    import difflib

    return difflib.SequenceMatcher(None, normalizar(a).lower(), normalizar(b).lower()).ratio()


def _similitud(a: str, b: str) -> float:
    """Máximo de la similitud de caracteres (difflib) y del solapamiento de palabras con contenido
    (|A ∩ B| / min(|A|, |B|)): el segundo detecta los títulos ampliados o reformulados, que difflib no ve.
    «Sin cambios» exige además casi el mismo texto (caracteres ≥ IGUAL)."""
    pa, pb = _palabras(a), _palabras(b)
    solapamiento = len(pa & pb) / min(len(pa), len(pb)) if pa and pb else 0.0
    return max(_caracteres(a, b), solapamiento)


def comparar_riesgos(actual: list[str], anterior: list[str]) -> dict[str, list]:
    """Factores de riesgo nuevos, eliminados y modificados frente al informe anual anterior (sin IA).

    Un título «nuevo» puede ser la reformulación de uno eliminado: si se parecen (≥ 0,50), se emparejan
    como «posible reformulación» para que el analista lo confirme.
    """
    def mejor(titulo, otros):
        return max(((o, _similitud(titulo, o)) for o in otros), key=lambda x: x[1], default=(None, 0.0))

    nuevos, modificados = [], []
    for t in actual:
        pareja, s = mejor(t, anterior)
        if s < MODIFICADO:
            nuevos.append({"titulo": t, "posible_origen": pareja if s >= POSIBLE_REFORMULACION else None})
        elif _caracteres(t, pareja) < IGUAL:
            modificados.append({"titulo": t, "anterior": pareja})
    eliminados = [t for t in anterior if mejor(t, actual)[1] < MODIFICADO]
    return {"nuevos": nuevos, "eliminados": eliminados, "modificados": modificados,
            "sin_cambios": len(actual) - len(nuevos) - len(modificados)}


def riesgos_anteriores(ticker: str) -> tuple[list[str], str]:
    """(títulos, accession) del informe anual anterior al último (para `comparar_riesgos`)."""
    from edgar import Company

    filings = Company(ticker).get_filings(form=FORMULARIOS_ANUALES, amendments=False).head(2)
    if len(filings) < 2:
        return [], ""
    filing = filings[1]
    return titulos_de_riesgo(filing.html(), getattr(filing.obj(), "risk_factors", None) or ""), filing.accession_no


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
