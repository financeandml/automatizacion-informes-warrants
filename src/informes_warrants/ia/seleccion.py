"""Uso mínimo de la IA: elegir y resumir entre fragmentos literales propuestos por el código.

El código extrae del 10-K los candidatos (títulos de riesgo, frases del MD&A) y los numera. El
modelo solo devuelve números y un resumen de una línea en español. La cita del informe es el
candidato elegido, tal cual, y se comprueba que existe en el texto original (idea de los
validadores de mtcb `dataset/validator.py`, Apache-2.0: coincidencia exacta tras normalizar).
"""

import json
import re
from dataclasses import dataclass

from ..ingesta.riesgos import normalizar
from .llm import LLMSettings, completar

SISTEMA = (
    "Eres un analista financiero. Respondes solo con JSON válido, sin texto adicional. "
    "No inventes datos: trabaja únicamente con los fragmentos numerados que se te dan."
)


@dataclass(frozen=True)
class Seleccion:
    resumen: str
    cita: str


def cita_valida(cita: str, texto_fuente: str) -> bool:
    return bool(cita) and normalizar(cita) in normalizar(texto_fuente)


MAX_CARACTERES_FRAGMENTO = 240


def _json(respuesta: str) -> list:
    bloque = re.search(r"\[.*\]", respuesta, re.DOTALL)
    if not bloque:
        raise ValueError(f"La respuesta del modelo no contiene una lista JSON: {respuesta[:200]}")
    return json.loads(bloque.group(0))


def seleccionar(candidatos: list[str], texto_fuente: str, instruccion: str, n: int = 5,
                cfg: LLMSettings | None = None) -> tuple[list[Seleccion], LLMSettings]:
    """Elige hasta n candidatos con la IA y devuelve resumen + cita literal verificada."""
    candidatos = [c for c in candidatos if cita_valida(c, texto_fuente)]
    if not candidatos:
        return [], cfg or LLMSettings.desde_entorno()
    # La IA elige por número viendo el comienzo de cada fragmento; la cita es el fragmento literal entero. Así la
    # llamada cabe en el cupo por minuto de Groq gratuito (8.000 tokens) y gasta menos cupo diario.
    lista = "\n".join(f"{i}. {c[:MAX_CARACTERES_FRAGMENTO]}" for i, c in enumerate(candidatos, 1))
    usuario = (f"{instruccion}\nElige como máximo {n} fragmentos. Devuelve una lista JSON de objetos "
               '{"n": número del fragmento, "resumen": "una frase en español de España, con registro formal de '
               'informe de análisis, de 25 palabras como máximo"}.'
               f"\n\nFragmentos:\n{lista}")
    respuesta, usado = completar(SISTEMA, usuario, cfg)
    elegidos, vistos = [], set()
    for item in _json(respuesta):
        try:
            i = int(item["n"])
        except (KeyError, TypeError, ValueError):
            continue
        resumen = str(item.get("resumen", "")).strip()
        if 1 <= i <= len(candidatos) and i not in vistos and resumen:
            vistos.add(i)
            elegidos.append(Seleccion(resumen=resumen, cita=candidatos[i - 1]))
    return elegidos[:n], usado
