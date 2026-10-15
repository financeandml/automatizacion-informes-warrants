"""Estructura corporativa y equipo directivo (B3, apartados 4 y 5), desde la SEC.

Reutiliza edgartools: `TenK.subsidiaries` (Exhibit 21: filial y jurisdicción) y los Form 3 y 4 (`Ownership`:
nombre y cargo declarados). Las tablas de directivos del 10-K tienen un formato distinto en cada empresa y no se
extraen; el equipo es el que presenta Form 4 (directivos y consejeros con obligación de declarar), con su cargo tal
como lo declara, y su antigüedad como insider sale del Form 3 (declaración inicial). Lo que la SEC no estructura
(trayectoria, independencia) sigue siendo del analista.
"""

import logging
from collections import Counter
from datetime import date

log = logging.getLogger(__name__)

MAX_FILIALES = 15
MAX_FORM3_PERSONA = 15  # Form 3 de una persona (consejeros de varias empresas)
MAX_FORM3 = 120  # Form 3 que se revisan, del más reciente al más antiguo, buscando el alta de cada persona
LOTE_FORM3 = 8  # descargas simultáneas (la SEC admite 10 por segundo)


def filiales(tenk) -> dict | None:
    """Filiales del Exhibit 21: total, las primeras y las jurisdicciones más frecuentes."""
    try:
        lista = tenk.subsidiaries
        df = lista.to_dataframe() if lista is not None else None
    except Exception as e:  # noqa: BLE001  (sin Exhibit 21 legible: el apartado queda para el analista)
        log.warning("Exhibit 21 no disponible: %s", e)
        return None
    if df is None or df.empty:
        return None
    filas = [{"nombre": " ".join(str(f.get("name", "")).split()), "jurisdiccion": " ".join(str(f.get("jurisdiction") or "—").split())}
             for f in df.to_dict("records")]
    jurisdicciones = Counter(f["jurisdiccion"] for f in filas if f["jurisdiccion"] != "—").most_common(5)
    return {"total": len(filas), "lista": filas[:MAX_FILIALES], "jurisdicciones": jurisdicciones}


def altas_como_insider(empresa, nombres: list[str], ciks: dict[str, str] | None = None) -> tuple[dict[str, date], set[str]]:
    """Fecha del Form 3 (declaración inicial como insider) de cada persona: primero entre los más recientes de la
    empresa y, para quien siga en ella sin aparecer ahí (P18: directivos con mucha antigüedad), en los Form 3 que
    presentó la propia persona (su CIK), el de esta empresa. Sin Form 3 electrónico (anteriores a 2003, p. ej. Tim
    Cook en 1998), su primer Form 4 sobre la empresa: «al menos desde». Devuelve (altas, nombres con fecha aproximada)."""
    pendientes = {n.lower(): n for n in nombres}
    altas, aproximadas = {}, set()
    try:
        filings = empresa.get_filings(form="3", amendments=False)
    except Exception:  # noqa: BLE001
        return altas, aproximadas
    from concurrent.futures import ThreadPoolExecutor

    def declarante(filing) -> str:
        try:
            return " ".join(str(filing.obj().get_ownership_summary().insider_name).split())
        except Exception:  # noqa: BLE001
            return ""

    recientes = list(filings.head(MAX_FORM3))
    with ThreadPoolExecutor(max_workers=LOTE_FORM3) as hilos:  # C5: por lotes en paralelo, en orden de recencia
        for inicio in range(0, len(recientes), LOTE_FORM3):
            if not pendientes:
                break
            lote = recientes[inicio:inicio + LOTE_FORM3]
            for filing, nombre in zip(lote, hilos.map(declarante, lote), strict=True):
                original = pendientes.pop(nombre.lower(), None) if nombre else None
                if original:
                    altas[original] = date.fromisoformat(str(filing.filing_date)[:10])
    for original in list(pendientes.values()):
        cik = (ciks or {}).get(original)
        alta = _alta_por_cik(cik, empresa.cik, "3")
        if alta is None and (alta := _alta_por_cik(cik, empresa.cik, "4")):
            aproximadas.add(original)
        if alta:
            altas[original] = alta
    return altas, aproximadas


def _alta_por_cik(cik: str | None, cik_empresa, formulario: str = "3") -> date | None:
    """El formulario más antiguo (Form 3 o, en su defecto, Form 4) de la persona sobre esta empresa."""
    if not cik:
        return None
    from edgar import Company

    try:
        formularios = Company(int(cik)).get_filings(form=formulario, amendments=False)
    except Exception:  # noqa: BLE001
        return None
    lista = list(formularios)
    for filing in (lista[-MAX_FORM3_PERSONA:][::-1] if formulario == "4" else lista[:MAX_FORM3_PERSONA][::-1]):
        try:
            emisor = filing.obj().issuer
            if int(getattr(emisor, "cik", 0) or 0) == int(cik_empresa):
                return date.fromisoformat(str(filing.filing_date)[:10])
        except Exception:  # noqa: BLE001
            continue
    return None
