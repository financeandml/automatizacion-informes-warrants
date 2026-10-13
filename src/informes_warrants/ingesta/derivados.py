"""Opciones y posiciones cortas (B5, apartados 15-17 y 19) desde yfinance.

**Fuente externa, no auditada**: aprobada por el usuario SOLO para opciones y posiciones en corto. El informe la
etiqueta así, con la fecha de la consulta, y nunca la usa en cifras financieras ni en la valoración. Mismo uso de
yfinance que financial-research-analyst-agent `options_analyzer.analyze_options` y `short_interest` (MIT).
Los cálculos sobre estos datos están en `calculo/derivados.py`.
"""

import logging
from datetime import date

log = logging.getLogger(__name__)

MAX_VENCIMIENTOS = 4  # como FRAA: los 4 vencimientos más próximos (peticiones razonables)


def cadena_opciones(ticker: str) -> dict | None:
    """{"vencimientos": [...], "calls": DataFrame, "puts": DataFrame, "consulta"}; None si no hay opciones."""
    import pandas as pd
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        vencimientos = list(t.options or [])[:MAX_VENCIMIENTOS]
        calls, puts = [], []
        for v in vencimientos:
            cadena = t.option_chain(v)
            calls.append(cadena.calls.assign(vencimiento=v))
            puts.append(cadena.puts.assign(vencimiento=v))
    except Exception as e:  # noqa: BLE001  (sin opciones o sin respuesta: el apartado no se muestra)
        log.warning("Opciones de %s no disponibles: %s", ticker, e)
        return None
    if not calls:
        return None
    return {"vencimientos": vencimientos, "calls": pd.concat(calls, ignore_index=True), "puts": pd.concat(puts, ignore_index=True),
            "consulta": date.today().isoformat()}


def posiciones_cortas(ticker: str) -> dict | None:
    """Acciones en corto declaradas por los intermediarios (FINRA, vía yfinance), con su fecha."""
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:  # noqa: BLE001
        log.warning("Posiciones cortas de %s no disponibles: %s", ticker, e)
        return None
    if not info.get("sharesShort"):
        return None
    fecha = info.get("dateShortInterest")
    return {"acciones": info.get("sharesShort"), "acciones_mes_anterior": info.get("sharesShortPriorMonth"),
            "sobre_flotante": info.get("shortPercentOfFloat"), "dias_para_cubrir": info.get("shortRatio"),
            "fecha": date.fromtimestamp(fecha).isoformat() if isinstance(fecha, int | float) else None,
            "consulta": date.today().isoformat()}
