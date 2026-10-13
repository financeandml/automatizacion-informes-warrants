"""Los tres únicos bloques de IA del informe: riesgos principales, catalizadores del MD&A y competencia.

El de competencia (decisión del usuario, 2026-10-13) solo traduce al español el apartado «Competition» del
Item 1, que el código ya extrajo literalmente (ingesta/competencia.py); los nombres de competidores, productos y
marcas quedan en su idioma original. La traducción se comprueba por código: mismas cifras, mismos nombres propios
y longitud razonable. Si no pasa, el informe muestra el original en inglés y lo marca para el analista.
"""

import re
from dataclasses import dataclass

from .llm import LLMSettings, completar
from .seleccion import Seleccion, seleccionar

# Señales de frases prospectivas en el MD&A (selección determinista de candidatos).
SENALES = re.compile(
    r"\b(expect|anticipat|plan(s|ned)?|launch|introduc|growth|grow|increase|demand|new product|"
    r"invest|outlook|opportunit|expand|backlog|pipeline)\w*", re.IGNORECASE)
MAX_CANDIDATOS = 60


def frases_candidatas(texto_mdna: str) -> tuple[list[str], int]:
    """Frases prospectivas del MD&A y número total de frases con señal (para no ocultar el recorte)."""
    from ..ingesta.competencia import _es_encabezado

    # sin las líneas de encabezado, que se pegaban a la frase siguiente («Europe Europe net sales…»)
    sin_encabezados = " ".join(linea for linea in texto_mdna.splitlines() if not _es_encabezado(linea))
    frases = re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(sin_encabezados.split()))
    con_senal = [f for f in frases if 60 <= len(f) <= 400 and SENALES.search(f)]
    return con_senal[:MAX_CANDIDATOS], len(con_senal)


def riesgos_principales(titulos: list[str], texto_item_1a: str,
                        cfg: LLMSettings | None = None) -> tuple[list[Seleccion], LLMSettings]:
    return seleccionar(
        titulos, texto_item_1a,
        "Estos son los títulos de los factores de riesgo del 10-K de una empresa. Elige los más "
        "materiales para un inversor (impacto potencial en resultados y probabilidad) y resume cada uno.",
        n=5, cfg=cfg)


def catalizadores(texto_mdna: str, cfg: LLMSettings | None = None) -> tuple[list[Seleccion], LLMSettings, int]:
    candidatos, total = frases_candidatas(texto_mdna)
    elegidos, usado = seleccionar(
        candidatos, texto_mdna,
        "Estas frases proceden del MD&A del 10-K. Elige las que describen catalizadores de crecimiento "
        "o de mejora de resultados según la dirección y resume cada una.",
        n=5, cfg=cfg)
    return elegidos, usado, total


SISTEMA_TRADUCCION = (
    "Eres un traductor financiero. Traduces del inglés al español de España, con registro formal de informe de "
    "análisis. No añades, quitas, resumes ni interpretas nada: traduces frase a frase. Dejas sin traducir los nombres "
    "propios de empresas, productos, marcas y servicios, y no cambias ninguna cifra. «The Company» y «the Company» no son "
    "un nombre propio: tradúcelos como «la compañía». Respondes solo con la traducción."
)
# Nombres propios que deben quedar igual: con mayúscula interna (LinkedIn, AbelZeta, iPhone) o marca registrada
# (Amtagvi®). Las siglas no cuentan: «AI» se traduce «IA» y «SUVs», «SUV».
PROPIO = re.compile(r"\b[A-Za-z0-9&.-]*[a-z][A-Z][A-Za-z0-9&.-]*\b|\b\w+(?=[®™])")
LONGITUD_MIN, LONGITUD_MAX = 0.8, 1.6  # el español ocupa algo más que el inglés


@dataclass(frozen=True)
class Traduccion:
    texto: str
    original: str
    valida: bool
    motivo: str = ""


def _cifras(texto: str) -> list[str]:
    return sorted(re.sub(r"(?<=\d)[.,](?=\d)", "", n) for n in re.findall(r"\d[\d.,]*\d|\d", texto))


def verificar_traduccion(original: str, traduccion: str) -> str:
    """Motivo por el que la traducción no vale ("" si vale)."""
    if not traduccion:
        return "sin respuesta del modelo"
    if not LONGITUD_MIN <= len(traduccion) / max(len(original), 1) <= LONGITUD_MAX:
        return "la longitud no corresponde a una traducción completa"
    if _cifras(original) != _cifras(traduccion):
        return "las cifras no coinciden con el original"
    faltan = sorted({n for n in PROPIO.findall(original) if n not in traduccion})
    if faltan:
        return f"faltan nombres propios del original: {', '.join(faltan[:5])}"
    return ""


def competencia_en_espanol(texto_literal: str, cfg: LLMSettings | None = None) -> tuple[Traduccion, LLMSettings | None]:
    """Traducción verificada del apartado «Competition» (texto ya extraído por código)."""
    try:
        respuesta, usado = completar(SISTEMA_TRADUCCION, texto_literal, cfg)
    except Exception as e:  # noqa: BLE001  (sin modelo: el original queda para el analista)
        return Traduccion(texto_literal, texto_literal, False, f"modelo de lenguaje no disponible ({e})"), None
    motivo = verificar_traduccion(texto_literal, respuesta)
    return Traduccion(respuesta if not motivo else texto_literal, texto_literal, not motivo, motivo), usado
