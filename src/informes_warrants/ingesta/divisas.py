"""Conversión a USD de las cifras de emisores extranjeros (20-F/40-F en IFRS u otra moneda).

1. Tipo medio del año declarado en el propio filing: edgartools `xbrl/currency.CurrencyConverter`
   (trazable: sale del XBRL de la empresa).
2. Si el filing no lo declara (p. ej., TSM), media anual del cruce `{MONEDA}USD=X` en yfinance,
   la misma fuente de mercado que usa edgar_analytics `market_data`.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Conversion:
    valor_usd: float
    tipo: float  # USD por unidad de moneda local
    fuente: str


def tipo_medio_yfinance(moneda: str, anio: int) -> float:
    import yfinance as yf

    cierres = yf.Ticker(f"{moneda}USD=X").history(start=f"{anio}-01-01", end=f"{anio + 1}-01-01")["Close"]
    if cierres.empty:
        raise ValueError(f"yfinance no tiene cotizaciones de {moneda}USD=X en {anio}")
    return float(cierres.mean())


def a_usd(valor: float, moneda: str, anio: int, xbrl=None) -> Conversion:
    moneda = moneda.upper()
    if moneda == "USD":
        return Conversion(valor, 1.0, "USD")
    if xbrl is not None:
        from edgar.xbrl.currency import CurrencyConverter

        convertido = CurrencyConverter(xbrl).to_usd(valor, anio)
        if convertido is not None and valor:
            return Conversion(convertido, convertido / valor, f"Tipo medio {anio} declarado en el filing (XBRL)")
    tipo = tipo_medio_yfinance(moneda, anio)
    return Conversion(valor * tipo, tipo, f"Media anual {anio} de {moneda}USD=X (yfinance)")


def tipo_cierre_yfinance(moneda: str, fecha) -> float:
    """Cierre de `{MONEDA}USD=X` en la fecha o en la última sesión anterior (saldos del balance al cierre del ejercicio)."""
    from datetime import date, timedelta

    import yfinance as yf

    fecha = fecha if isinstance(fecha, date) else date.fromisoformat(str(fecha)[:10])
    serie = yf.Ticker(f"{moneda.upper()}USD=X").history(start=str(fecha - timedelta(days=10)), end=str(fecha + timedelta(days=1)))
    cierres = serie["Close"]
    if cierres.empty:
        raise ValueError(f"yfinance no tiene cotizaciones de {moneda}USD=X hasta el {fecha}")
    return float(cierres.iloc[-1])


def tipos_del_ejercicio(moneda: str, anio: int, cierre, xbrl=None) -> tuple[float, float, str]:
    """(tipo medio del año para los flujos, tipo de cierre para los saldos, fuente) en USD por unidad de `moneda`."""
    medio = a_usd(1.0, moneda, anio, xbrl)
    fin = tipo_cierre_yfinance(moneda, cierre) if cierre else medio.tipo
    return medio.tipo, fin, f"{medio.fuente}; saldos al cierre de {moneda}USD=X del {cierre} (yfinance)"
