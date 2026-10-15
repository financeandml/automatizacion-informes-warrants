"""P22: previsiones sobre la empresa, en lugar de FactSet (aparcado por el usuario el 2026-10-15).

1. *Guidance* de la propia empresa (fuente oficial): frases literales del comunicado de resultados (8-K, ítem 2.02,
   anexo 99.1) que el código propone y la IA elige y resume, como los catalizadores del MD&A. La cita se comprueba en
   el texto y el resumen no puede traer cifras que no estén en la cita.
2. Consenso publicado de analistas (fuente externa, no auditada): Gemini con búsqueda en Google. Cada estimación se
   admite solo si su frase literal aparece en la página citada (el código la descarga y lo comprueba) y su valor es una
   cifra de esa frase; si no, se descarta. Nunca entra sola en la valoración: el analista la confirma.
"""

import logging
import re
from datetime import date

from .bloques import _cifras
from .seleccion import seleccionar

log = logging.getLogger(__name__)
PREVISION = re.compile(r"\b(outlook|guidance|expects?|expected|forecasts?|anticipates?|full[- ]year|for (?:fiscal )?(?:year )?20\d\d|"
                       r"next quarter|(?:first|second|third|fourth) quarter of (?:fiscal )?20\d\d|range of)\b", re.I)
MAX_CANDIDATOS = 50


def frases_de_prevision(texto: str) -> list[str]:
    frases = re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])", " ".join((texto or "").replace("\xa0", " ").split()))
    return [f for f in frases if 40 <= len(f) <= 450 and PREVISION.search(f) and re.search(r"\d", f)][:MAX_CANDIDATOS]


def guidance_8k(texto: str, accession: str, fecha, cfg=None) -> dict | None:
    """Previsiones de la dirección en el último comunicado de resultados, con su cita literal."""
    candidatos = frases_de_prevision(texto)
    if not candidatos:
        return None
    elegidos, usado = seleccionar(
        candidatos, texto,
        "Estas frases proceden del comunicado de resultados de la empresa (8-K, anexo 99.1). Elige las que dan la "
        "previsión de la propia dirección (guidance) para los próximos trimestres o el ejercicio: ventas, márgenes, BPA, "
        "inversión o similares. Resume cada una en español sin cambiar, añadir ni redondear ninguna cifra.", n=5, cfg=cfg)
    lista = [{"resumen": s.resumen if set(_cifras(s.resumen)) <= set(_cifras(s.cita)) else "", "cita": s.cita} for s in elegidos]
    if not lista:
        return None
    return {"lista": lista, "accession": accession, "fecha": str(fecha), "modelo": f"{usado.proveedor} · {usado.modelo}"}


SISTEMA_CONSENSO = (
    "Eres un asistente de investigación financiera. Buscas datos publicados y respondes solo con JSON válido. "
    "No estimes ni calcules nada: copia las cifras tal como aparecen en la página y la frase o fila literal donde aparecen.")


def _numero(texto: str) -> float | None:
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", texto or "")
    return float(m.group(0).replace(",", "")) if m else None


def consenso_publicado(ticker: str, empresa: str) -> dict | None:
    """Estimaciones medias de consenso (ventas y BPA del ejercicio en curso y del siguiente) verificadas en su fuente."""
    from .gemini import disponible, generar, texto_de_pagina

    if not disponible():
        return None
    usuario = (f"Busca la estimación media de consenso de los analistas para {empresa} (ticker {ticker}): ventas y BPA "
               "del ejercicio fiscal en curso y del siguiente, con el número de analistas si se publica. Devuelve "
               '{"estimaciones": [{"concepto": "ventas" o "bpa", "ejercicio": "FY2027", "valor": número tal como aparece, '
               '"unidad": "USD", "USD mn" o "USD bn", "analistas": número o null, "url": "página donde aparece", '
               '"literal": "frase o fila copiada de la página"}]}')
    try:
        r = generar(SISTEMA_CONSENSO, usuario, buscar=True)
    except Exception as e:  # noqa: BLE001  (sin consenso el informe sale igual)
        log.warning("Consenso de %s no disponible: %s", ticker, e)
        return None
    datos = r.get("datos") or {}
    admitidas, descartadas, paginas = [], 0, {}
    for est in (datos.get("estimaciones") if isinstance(datos, dict) else None) or []:
        url, literal, valor = str(est.get("url") or ""), str(est.get("literal") or ""), est.get("valor")
        try:
            if url not in paginas:
                paginas[url] = texto_de_pagina(url) if url.startswith("http") else ""
            pagina = " ".join(paginas[url].split()).lower()
        except Exception:  # noqa: BLE001  (página inaccesible: no se puede verificar)
            pagina = ""
        literal_norm = " ".join(literal.split()).lower()
        cifras_literal = [_numero(x) for x in re.findall(r"-?\d[\d,]*(?:\.\d+)?", literal)]
        if literal_norm and literal_norm in pagina and isinstance(valor, (int, float)) and float(valor) in cifras_literal:
            admitidas.append({k: est.get(k) for k in ("concepto", "ejercicio", "valor", "unidad", "analistas", "url", "literal")})
        else:
            descartadas += 1
    if not admitidas and not descartadas:
        return None
    return {"estimaciones": admitidas, "descartadas": descartadas, "consulta": date.today().isoformat(), "modelo": r.get("modelo"),
            "fuentes": r.get("fuentes", [])}
