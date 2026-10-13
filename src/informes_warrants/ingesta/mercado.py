"""Datos de mercado: cotización, histórico y comportamiento relativo (capa 1).

Fuente: yfinance, la misma que usan edgar_analytics `market_data` y financial-research-analyst-agent
`src/data/provider.py`. El cálculo del comportamiento relativo (1m…5a, YTD frente a SPY y al ETF
sectorial) sigue la idea de financial-research-analyst-agent `performance_tracker.track_performance`.
Las acciones en circulación salen de la portada del último filing (dei, SEC), no de Yahoo.
El mapeo SIC → ETF sectorial SPDR no existía en ningún repo: se define aquí.

Tipo libre de riesgo: bono del Tesoro de EEUU a 10 años (serie DGS10 de FRED). Se lee del CSV público,
que no requiere clave (financial-research-analyst-agent `macro_data.get_treasury_yields` usa la API con
clave); si falla, `^TNX` de yfinance; si también falla, el valor por defecto y un aviso.
"""

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)
URL_DGS10 = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"

# (desde, hasta, ETF) por orden: el primer rango que contiene el SIC gana
SIC_A_ETF: tuple[tuple[int, int, str], ...] = (
    (1300, 1399, "XLE"), (2900, 2999, "XLE"),
    (2830, 2836, "XLV"), (3840, 3851, "XLV"), (5122, 5122, "XLV"), (8000, 8099, "XLV"),
    (3570, 3579, "XLK"), (3600, 3629, "XLK"), (3640, 3699, "XLK"), (3800, 3839, "XLK"), (3852, 3899, "XLK"), (7370, 7379, "XLK"),
    (2700, 2799, "XLC"), (4800, 4899, "XLC"), (7800, 7999, "XLC"),
    (4900, 4999, "XLU"),
    (6500, 6553, "XLRE"), (6798, 6798, "XLRE"),
    (6000, 6799, "XLF"),
    (2000, 2199, "XLP"), (2840, 2844, "XLP"), (5400, 5499, "XLP"), (5912, 5912, "XLP"),
    (2200, 2399, "XLY"), (2500, 2599, "XLY"), (3630, 3639, "XLY"), (3710, 3716, "XLY"), (3900, 3999, "XLY"),
    (5200, 5999, "XLY"), (7000, 7099, "XLY"), (7200, 7299, "XLY"),
    (1500, 1799, "XLI"), (3400, 3569, "XLI"), (3580, 3599, "XLI"), (3717, 3799, "XLI"), (4000, 4799, "XLI"),
    (5000, 5199, "XLI"), (7300, 7369, "XLI"), (7380, 7399, "XLI"), (8700, 8799, "XLI"),
    (1000, 1499, "XLB"), (2400, 2499, "XLB"), (2600, 2699, "XLB"), (2800, 2899, "XLB"), (3000, 3399, "XLB"),
)
INDICE = "SPY"
HORIZONTES = {"1m": 21, "3m": 63, "12m": 252, "3a": 756, "5a": 1260}  # sesiones bursátiles


@dataclass(frozen=True)
class TipoLibreRiesgo:
    valor: float  # en tanto por uno
    fecha: str
    fuente: str


def ultimo_dgs10(csv: str) -> tuple[float, str] | None:
    """Último dato válido del CSV de FRED (las fechas sin dato vienen con «.» o vacías)."""
    for linea in reversed(csv.strip().splitlines()[1:]):
        fecha, _, valor = linea.partition(",")
        try:
            return float(valor) / 100, fecha
        except ValueError:
            continue
    return None


def tipo_libre_riesgo(por_defecto: float = 0.045) -> TipoLibreRiesgo:
    import urllib.request

    try:
        with urllib.request.urlopen(URL_DGS10, timeout=20) as respuesta:
            dato = ultimo_dgs10(respuesta.read().decode("utf-8"))
        if dato:
            return TipoLibreRiesgo(dato[0], dato[1], "FRED DGS10 (Tesoro de EEUU a 10 años)")
    except OSError as e:
        log.warning("FRED no disponible (%s): se usa ^TNX de yfinance", e)
    try:
        import yfinance as yf

        cierre = yf.Ticker("^TNX").history(period="10d")["Close"].dropna()
        if len(cierre):
            return TipoLibreRiesgo(float(cierre.iloc[-1]) / 100, cierre.index[-1].date().isoformat(), "yfinance ^TNX")
    except Exception as e:  # noqa: BLE001  (cualquier fallo de red o de datos lleva al valor por defecto)
        log.warning("^TNX no disponible (%s)", e)
    log.warning("Tipo libre de riesgo no disponible: se usa el valor por defecto %.2f %%", por_defecto * 100)
    return TipoLibreRiesgo(por_defecto, "", "valor por defecto (sin conexión)")


def etf_sectorial(sic: int | str | None) -> str:
    try:
        sic = int(sic)
    except (TypeError, ValueError):
        return INDICE
    return next((etf for desde, hasta, etf in SIC_A_ETF if desde <= sic <= hasta), INDICE)


@dataclass(frozen=True)
class Cotizacion:
    ticker: str
    precio: float
    fecha: str
    maximo_12m: float
    minimo_12m: float
    medio_12m: float
    volumen_medio_12m: float  # en USD
    volumen_medio_acciones_12m: float | None = None


def historico(ticker: str, anios: int = 6, ajustado: bool = True):  # 6 años: rentabilidad a 5 años completos
    """Cotizaciones diarias de los últimos `anios` años.

    `ajustado=True`: ajustadas por dividendos y desdoblamientos (rentabilidad total: base 100, beta, comportamiento).
    `ajustado=False`: solo por desdoblamientos (precio de mercado real: rangos de 12 meses, volumen y múltiplos
    históricos; ajustar por dividendos rebajaría los precios pasados).
    """
    import yfinance as yf

    datos = yf.Ticker(ticker).history(period=f"{anios}y", auto_adjust=ajustado)
    if datos.empty:
        raise ValueError(f"yfinance no devuelve cotizaciones de {ticker}")
    return datos


def cotizacion(ticker: str) -> Cotizacion:
    h = historico(ticker, 1, ajustado=False)
    cierre = h["Close"]
    return Cotizacion(ticker.upper(), float(cierre.iloc[-1]), str(cierre.index[-1].date()), float(cierre.max()),
                      float(cierre.min()), float(cierre.mean()), float((h["Close"] * h["Volume"]).mean()),
                      float(h["Volume"].mean()))


def precios_semanales(ticker: str, anios: int = 6) -> list:
    """(fecha, cierre del viernes sin ajustar por dividendos) para los múltiplos históricos."""
    cierre = historico(ticker, anios, ajustado=False)["Close"].resample("W-FRI").last().dropna()
    return [(i.date(), float(v)) for i, v in cierre.items()]


def rentabilidades(cierres) -> dict[str, float | None]:
    """Rentabilidad simple por horizonte y en el año (YTD) de una serie de cierres."""
    ultimo = float(cierres.iloc[-1])
    r = {k: (ultimo / float(cierres.iloc[-n - 1]) - 1) if len(cierres) > n else None for k, n in HORIZONTES.items()}
    del_anio = cierres[cierres.index.year == cierres.index[-1].year]
    previos = cierres[cierres.index < del_anio.index[0]]
    r["ytd"] = ultimo / float(previos.iloc[-1]) - 1 if len(previos) else None
    return r


def comportamiento(ticker: str, sic: int | str | None) -> dict[str, dict[str, float | None]]:
    """Rentabilidad absoluta y relativa (diferencia en puntos) frente a SPY y al ETF del sector."""
    etf = etf_sectorial(sic)
    series = {t: historico(t)["Close"] for t in dict.fromkeys((ticker, INDICE, etf))}
    absoluta = {t: rentabilidades(s) for t, s in series.items()}
    propia = absoluta[ticker]

    def relativa(ref):
        return {k: None if propia[k] is None or absoluta[ref][k] is None else propia[k] - absoluta[ref][k] for k in propia}

    return {"absoluta": propia, f"vs {INDICE}": relativa(INDICE), f"vs {etf}": relativa(etf)}


def participaciones(ticker: str) -> dict | None:
    """Participación de insiders e institucional y mayores tenedores institucionales (A6).

    **Fuente externa, no auditada (yfinance)**: excepción aprobada por el usuario solo para este bloque (como el
    resto de financial-research-analyst-agent `insider_activity.get_institutional_holdings`). El informe la etiqueta
    así y nunca la usa en cifras financieras ni en la valoración. None si yfinance no responde.
    """
    from datetime import date

    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        mayores = t.major_holders
        instituciones = t.institutional_holders
    except Exception as e:  # noqa: BLE001
        log.warning("yfinance sin participaciones de %s: %s", ticker, e)
        return None
    if mayores is None or getattr(mayores, "empty", True):
        return None
    valores = mayores["Value"].to_dict() if "Value" in mayores else {}
    principales = []
    if instituciones is not None and not instituciones.empty:
        for fila in instituciones.head(5).to_dict("records"):
            principales.append({"nombre": str(fila.get("Holder", "")), "porcentaje": fila.get("pctHeld"),
                                "fecha": str(fila.get("Date Reported", ""))[:10]})
    return {"insiders": valores.get("insidersPercentHeld"), "instituciones": valores.get("institutionsPercentHeld"),
            "numero_instituciones": valores.get("institutionsCount"), "principales": principales,
            "consulta": date.today().isoformat()}
