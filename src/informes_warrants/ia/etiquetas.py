"""P1 y P2 (propuestas R1 y R5, aparcadas hasta el 2026-10-15): borradores de la IA sobre lo que ya dice el informe.

- P1: una «lectura» de una línea para cada hecho clave (su etiqueta temática la pone el código). No puede traer
  cifras que no estén en el hecho; si las trae, se descarta.
- P2: cada riesgo principal (título literal del Item 1A, ya elegido y verificado) se clasifica en la taxonomía de la
  propuesta R5 y se dice qué supuesto del modelo amenaza. Las categorías se validan contra una lista cerrada.

Proveedor: el de `ia/llm.py` (Gemini si hay GEMINI_API_KEY; si no, el siguiente). Sin modelo, sin borrador: el
informe sale igual con las etiquetas del código.
"""

import json
import logging
import re

from .bloques import _cifras
from .llm import completar

log = logging.getLogger(__name__)
SISTEMA = ("Eres un analista financiero que escribe en español de España, con registro formal. Respondes solo con JSON "
           "válido. No inventas datos ni cifras: trabajas únicamente con el texto que se te da.")
MAX_PALABRAS = 25
CATEGORIAS = ("macro", "crecimiento", "rentabilidad", "competencia", "regulatorio", "financiero", "ejecución", "M&A")
CATEGORIAS_BIOTEC = ("clínico", "regulatorio", "comercial", "precio", "financiero", "competencia", "macro")
NIVELES = ("baja", "media", "alta")  # P16: probabilidad e impacto de la matriz de riesgos
SUPUESTOS = ("crecimiento de ventas", "margen", "coste del capital", "múltiplo de salida", "balance y liquidez")


def _lista_json(texto: str) -> list:
    m = re.search(r"\[.*\]", texto or "", re.S)
    try:
        return json.loads(m.group(0)) if m else []
    except ValueError:
        return []


def lecturas_hechos(hechos: list[str]) -> tuple[list[str | None], str | None]:
    """Una lectura por hecho (o None si no pasa la verificación) y el modelo usado."""
    if not hechos:
        return [], None
    lista = "\n".join(f"{i}. {h}" for i, h in enumerate(hechos, 1))
    usuario = ("Estos son los hechos clave de un informe de análisis. Para cada uno escribe una lectura de una frase "
               f"(máximo {MAX_PALABRAS} palabras) sobre qué significa para la tesis de inversión, SIN cifras nuevas: solo puedes "
               'repetir las del propio hecho. Devuelve una lista JSON de {"n": número, "lectura": "frase"}.\n\n' + lista)
    try:
        respuesta, cfg = completar(SISTEMA, usuario)
    except Exception as e:  # noqa: BLE001
        log.warning("Lecturas de los hechos clave sin IA: %s", e)
        return [None] * len(hechos), None
    salida: list[str | None] = [None] * len(hechos)
    for item in _lista_json(respuesta):
        try:
            i = int(item["n"]) - 1
        except (KeyError, TypeError, ValueError):
            continue
        lectura = " ".join(str(item.get("lectura", "")).split())
        sin_cifras_nuevas = set(_cifras(lectura)) <= set(_cifras(hechos[i])) if 0 <= i < len(hechos) else False
        if sin_cifras_nuevas and lectura and len(lectura.split()) <= MAX_PALABRAS + 5:
            salida[i] = lectura
    return salida, f"{cfg.proveedor} · {cfg.modelo}"


def clasificar_riesgos(riesgos: list[dict], biotecnologia: bool = False) -> list[dict]:
    """Añade a cada riesgo {"categoria", "supuesto"} validados (o nada si el modelo no da una categoría válida)."""
    if not riesgos:
        return riesgos
    categorias = CATEGORIAS_BIOTEC if biotecnologia else CATEGORIAS
    lista = "\n".join(f"{i}. {r['cita']}" for i, r in enumerate(riesgos, 1))
    usuario = (f"Clasifica cada riesgo en una categoría de esta lista: {', '.join(categorias)}; y di qué supuesto del modelo de "
               f"valoración amenaza más, de esta lista: {', '.join(SUPUESTOS)}; y estima su probabilidad y su impacto en la "
               "tesis (baja, media o alta) a partir de lo que dice el texto. Devuelve una lista JSON de "
               '{"n": número, "categoria": "...", "supuesto": "...", "probabilidad": "...", "impacto": "..."}.\n\n' + lista)
    try:
        respuesta, _ = completar(SISTEMA, usuario)
    except Exception as e:  # noqa: BLE001
        log.warning("Clasificación de riesgos sin IA: %s", e)
        return riesgos
    for item in _lista_json(respuesta):
        try:
            i = int(item["n"]) - 1
        except (KeyError, TypeError, ValueError):
            continue
        categoria, supuesto = str(item.get("categoria", "")).strip(), str(item.get("supuesto", "")).strip()
        if 0 <= i < len(riesgos) and categoria in categorias and supuesto in SUPUESTOS:
            riesgos[i] = {**riesgos[i], "categoria": categoria, "supuesto": supuesto}
            probabilidad, impacto = str(item.get("probabilidad", "")).strip(), str(item.get("impacto", "")).strip()
            if probabilidad in NIVELES and impacto in NIVELES:  # P16: matriz probabilidad × impacto (borrador)
                riesgos[i] = {**riesgos[i], "probabilidad": probabilidad, "impacto": impacto}
    return riesgos


def emparejar_miembros(nombres_10k: list[str], nombres_10q: list[str]) -> dict[str, str]:
    """F7: nombre en el 10-Q → nombre en el 10-K para los miembros que cambian de nombre. Solo pares de nombres que
    existen, uno a uno; las cifras y la validación contra el total LTM siguen en el código (calculo/normalizador)."""
    faltan = [n for n in nombres_10k if n not in nombres_10q]
    sobran = [n for n in nombres_10q if n not in nombres_10k]
    if not faltan or not sobran:
        return {}
    usuario = ("Una empresa ha cambiado el nombre de algunos segmentos entre su informe anual y su informe trimestral. "
               f"Nombres del anual sin pareja: {json.dumps(faltan, ensure_ascii=False)}. Nombres del trimestral sin pareja: "
               f"{json.dumps(sobran, ensure_ascii=False)}. Empareja solo los que sean claramente el mismo segmento. Devuelve una "
               'lista JSON de {"trimestral": "...", "anual": "..."}; si no hay ninguno claro, [].')
    try:
        respuesta, _ = completar(SISTEMA, usuario)
    except Exception as e:  # noqa: BLE001
        log.warning("Emparejamiento de segmentos sin IA: %s", e)
        return {}
    pares, usados = {}, set()
    for item in _lista_json(respuesta):
        q, k = str(item.get("trimestral", "")), str(item.get("anual", ""))
        if q in sobran and k in faltan and k not in usados:
            pares[q] = k
            usados.add(k)
    return pares
