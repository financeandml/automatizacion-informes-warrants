"""Historial de la empresa en la SEC (A8, apartado 21): publicaciones de resultados y alarmas.

Reutiliza edgartools: el índice de filings (`Filings.to_pandas()`) ya trae los ítems de cada 8-K y la hora de
aceptación de la SEC, sin descargar cada documento; `TenK` da el texto del Item 9A y del 10-K completo.

Alarmas (5 años):
- 8-K ítem 4.01 (cambio de auditor) y 4.02 (las cuentas publicadas dejan de ser fiables: reexpresión).
- 10-K/A y 10-Q/A (informes modificados) y NT 10-K / NT 10-Q (aviso de presentación tardía).
- En el último 10-K, frases literales sobre control interno no eficaz o debilidad material (Item 9A) y sobre
  dudas sobre la continuidad de la empresa (*going concern*). Se citan tal cual para que el analista las valore;
  las frases hipotéticas («could», «may»…) de los factores de riesgo no cuentan.
"""

import logging
import re
from datetime import date, timedelta

log = logging.getLogger(__name__)

ANIOS_ALARMAS = 5
ITEMS_ALARMA = {"4.01": "Cambio de auditor (8-K ítem 4.01)", "4.02": "Cuentas publicadas no fiables: reexpresión (8-K ítem 4.02)"}
FORMULARIOS_ALARMA = {"10-K/A": "10-K modificado", "10-Q/A": "10-Q modificado", "NT 10-K": "Aviso de 10-K tardío",
                      "NT 10-Q": "Aviso de 10-Q tardío"}
HIPOTETICO = re.compile(r"\b(could|may|might|would|if|potential(?:ly)?|risk)\b", re.I)
CONTROL_NO_EFICAZ = re.compile(r"(?:were|was) not effective|material weakness(?:es)? (?:in|that|was|were|has|have|existed|identified)|"
                               r"identified (?:a |two |three |)material weakness", re.I)
CONTINUIDAD = re.compile(r"substantial doubt[^.]{0,120}going concern", re.I)
MAX_FRASES = 3


def eventos_8k(empresa, desde: date) -> list[dict]:
    """8-K presentados desde `desde`: fecha, hora de aceptación (UTC), ítems y accession."""
    try:
        df = empresa.get_filings(form="8-K").to_pandas()
    except Exception as e:  # noqa: BLE001
        log.warning("8-K no disponibles: %s", e)
        return []
    salida = []
    for fila in df.to_dict("records"):
        fecha = date.fromisoformat(str(fila["filing_date"])[:10])
        if fecha < desde:
            continue
        items = [i.strip() for i in str(fila.get("items") or "").split(",") if i.strip()]
        salida.append({"fecha": fecha, "aceptacion": str(fila.get("acceptanceDateTime") or ""), "items": items,
                       "accession": fila["accession_number"]})
    return sorted(salida, key=lambda e: e["fecha"])


def _frases(texto: str, patron: re.Pattern) -> list[str]:
    frases = re.split(r"(?<=[.;])\s+", " ".join((texto or "").split()))
    return [f for f in frases if patron.search(f) and not HIPOTETICO.search(f)][:MAX_FRASES]


def alarmas(empresa, hoy: date, filing_10k=None, eventos: list[dict] | None = None) -> list[dict]:
    """Alarmas de los últimos 5 años (tipo, fecha, detalle, accession); vacía si no hay ninguna."""
    desde = hoy - timedelta(days=365 * ANIOS_ALARMAS)
    salida = []
    for e in eventos if eventos is not None else eventos_8k(empresa, desde):
        for item in e["items"]:
            if item in ITEMS_ALARMA and e["fecha"] >= desde:
                salida.append({"tipo": ITEMS_ALARMA[item], "fecha": e["fecha"], "detalle": "", "accession": e["accession"]})
    try:
        filings = empresa.get_filings(form=list(FORMULARIOS_ALARMA))
        for f in filings:
            fecha = date.fromisoformat(str(f.filing_date)[:10])
            if fecha >= desde:
                salida.append({"tipo": FORMULARIOS_ALARMA.get(f.form, f.form), "fecha": fecha, "detalle": "", "accession": f.accession_no})
    except Exception as e:  # noqa: BLE001
        log.warning("Formularios de alarma no disponibles: %s", e)
    if filing_10k is not None:
        try:
            tenk = filing_10k.obj()
            control = tenk["Item 9A"] or ""
            texto = filing_10k.text() or ""
        except Exception as e:  # noqa: BLE001
            log.warning("Texto del 10-K no disponible para las alarmas: %s", e)
            control = texto = ""
        fecha, accession = date.fromisoformat(str(filing_10k.filing_date)[:10]), filing_10k.accession_no
        for tipo, fuente, patron in (("Control interno (Item 9A del 10-K)", str(control), CONTROL_NO_EFICAZ),
                                     ("Continuidad de la empresa (10-K)", texto, CONTINUIDAD)):
            salida += [{"tipo": tipo, "fecha": fecha, "detalle": frase, "accession": accession} for frase in _frases(fuente, patron)]
    return sorted(salida, key=lambda a: a["fecha"], reverse=True)
