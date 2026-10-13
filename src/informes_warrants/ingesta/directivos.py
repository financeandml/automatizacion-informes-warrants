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
MAX_FORM3 = 120  # Form 3 que se revisan, del más reciente al más antiguo, buscando el alta de cada persona


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


def altas_como_insider(empresa, nombres: list[str]) -> dict[str, date]:
    """Fecha del Form 3 (declaración inicial como insider) de cada persona, si está entre los más recientes."""
    pendientes = {n.lower(): n for n in nombres}
    altas = {}
    try:
        filings = empresa.get_filings(form="3", amendments=False)
    except Exception:  # noqa: BLE001
        return altas
    for filing in filings.head(MAX_FORM3):
        if not pendientes:
            break
        try:
            nombre = " ".join(str(filing.obj().get_ownership_summary().insider_name).split())
        except Exception:  # noqa: BLE001
            continue
        original = pendientes.pop(nombre.lower(), None)
        if original:
            altas[original] = date.fromisoformat(str(filing.filing_date)[:10])
    return altas
