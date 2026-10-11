"""Los dos únicos bloques de IA del informe: riesgos principales y catalizadores del MD&A."""

import re

from .llm import LLMSettings
from .seleccion import Seleccion, seleccionar

# Señales de frases prospectivas en el MD&A (selección determinista de candidatos).
SENALES = re.compile(
    r"\b(expect|anticipat|plan(s|ned)?|launch|introduc|growth|grow|increase|demand|new product|"
    r"invest|outlook|opportunit|expand|backlog|pipeline)\w*", re.IGNORECASE)
MAX_CANDIDATOS = 60


def frases_candidatas(texto_mdna: str) -> tuple[list[str], int]:
    """Frases prospectivas del MD&A y número total de frases con señal (para no ocultar el recorte)."""
    frases = re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(texto_mdna.split()))
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
