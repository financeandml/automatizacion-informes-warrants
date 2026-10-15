"""Comparables: propuesta automática por código SIC (solo SEC, sin *bulk*) y sus datos LTM.

La lista es una **propuesta**: el informe la marca «Revisar» y el analista puede sustituirla.
Selección, determinista y trazable:
  1. CIK con el mismo SIC (4 dígitos) que han presentado 10-K: SEC `browse-edgar?action=getcompany
     &SIC=…&type=10-K&output=atom`. Si salen menos de MINIMO cotizadas, se amplía al SIC de 3 dígitos.
     (edgartools `get_companies_by_industry` necesita descargar antes el *bulk* de *submissions*, de más
     de 1 GB; esta vía no.)
  2. Solo cotizadas en NYSE o Nasdaq, una por CIK (doble clase): lista oficial de tickers de la SEC
     (edgartools `reference.tickers.get_company_tickers`). Fuera preferentes y *warrants* (regla de
     FinRobot `peer_screen._is_non_common_listing`, Apache-2.0).
  3. Las N más parecidas por tamaño: distancia logarítmica de los ingresos anuales, de la API *frames*
     de la SEC (`api/xbrl/frames/us-gaap/<concepto>/USD/CY<año>.json`: un dato por empresa).
Los múltiplos de cada comparable salen del mismo normalizador (LTM) y las mismas fórmulas que los de
la empresa analizada (calculo/metricas.py), con su cotización de yfinance.
"""

import logging
import math
import re
from datetime import date

from .nombres import nombre_legible

log = logging.getLogger(__name__)
URL_SIC = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&SIC={sic}&type=10-K&dateb=&owner=include&count=100&start={inicio}&output=atom"
URL_FRAMES = "https://data.sec.gov/api/xbrl/frames/us-gaap/{concepto}/USD/CY{anio}.json"
BOLSAS = {"NYSE", "Nasdaq"}
MINIMO, NUMERO = 3, 6
RATIO_TAMANO_MAX = 50  # fuera los comparables más de 50 veces mayores o menores por ingresos
PAGINAS_MAX = 4  # hasta 400 empresas por código SIC
NO_ORDINARIAS = re.compile(r"-P[A-Z]{0,3}$|-W[ST]?$|\.W[ST]?$")  # preferentes (-PA…) y warrants (-WT, .WS)
CONCEPTOS_INGRESOS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues")


def ciks_por_sic(sic: int) -> list[int]:
    from edgar.httprequests import download_file

    ciks: list[int] = []
    for pagina in range(PAGINAS_MAX):
        atom = download_file(URL_SIC.format(sic=sic, inicio=pagina * 100), as_text=True)
        nuevos = [int(c) for c in re.findall(r"<cik>(\d+)</cik>", atom)]
        ciks += nuevos
        if len(nuevos) < 100:
            break
    return ciks


def cotizadas():
    """Tabla cik → (ticker, nombre) de las cotizadas en NYSE/Nasdaq, una fila por CIK."""
    from edgar.reference.tickers import get_company_tickers

    t = get_company_tickers()
    t = t[t["exchange"].isin(BOLSAS) & ~t["ticker"].astype(str).str.contains(NO_ORDINARIAS)]
    return t.drop_duplicates("cik").set_index("cik")


def ingresos_por_cik(anio: int) -> dict[int, float]:
    from edgar.httprequests import download_json

    salida: dict[int, float] = {}
    for concepto in reversed(CONCEPTOS_INGRESOS):  # el concepto preferente sobrescribe al alternativo
        try:
            datos = download_json(URL_FRAMES.format(concepto=concepto, anio=anio))
        except Exception as e:  # noqa: BLE001  (sin frames se ordena sin tamaño, con aviso)
            log.warning("SEC frames %s CY%s no disponible: %s", concepto, anio, e)
            continue
        salida.update({int(d["cik"]): float(d["val"]) for d in datos.get("data", []) if d.get("val")})
    return salida


def ordenar_por_tamano(candidatos: list[int], tamano: dict[int, float], referencia: float | None) -> list[int]:
    """Más parecidos primero (|log ingresos − log referencia|); fuera los de tamaño incomparable (más de
    RATIO_TAMANO_MAX veces); los que no tienen dato de tamaño, al final."""
    def distancia(cik):
        valor = tamano.get(cik)
        if not valor or not referencia or valor <= 0 or referencia <= 0:
            return math.inf
        return abs(math.log(valor) - math.log(referencia))

    validos = [c for c in candidatos if distancia(c) == math.inf or distancia(c) <= math.log(RATIO_TAMANO_MAX)]
    return sorted(validos, key=lambda c: (distancia(c), c))


def proponer(sic: int | str | None, cik_propio: int, ingresos_propios: float | None, n: int = NUMERO,
             ticker: str | None = None) -> tuple[list[str], str]:
    """(tickers propuestos, criterio usado): los «comparables modelo» del SaaS. Primero, las empresas del mismo
    sector de Damodaran (clasificación de NYU Stern, mejor que el SIC); si la empresa no está clasificada, el código
    SIC. Lista vacía si no hay candidatos cotizados o la SEC no responde: el informe sale igual, con aviso «Revisar»."""
    if ticker:
        try:
            propuesta = _proponer_por_sector(ticker, cik_propio, ingresos_propios, n)
            if propuesta:
                return propuesta
        except Exception as e:  # noqa: BLE001  (sin Damodaran: el código SIC)
            log.warning("Comparables por sector de Damodaran no disponibles (%s): %s", ticker, e)
    if not sic or not str(sic).isdigit():
        return [], "sin código SIC"
    try:
        return _proponer(int(sic), cik_propio, ingresos_propios, n)
    except Exception as e:  # noqa: BLE001  (sin red o SEC caída: el analista añade la lista)
        log.warning("Comparables no disponibles (SIC %s): %s", sic, e)
        return [], f"propuesta automática no disponible ({type(e).__name__}): añade la lista de comparables"


def _proponer_por_sector(ticker: str, cik_propio: int, ingresos_propios: float | None, n: int) -> tuple[list[str], str] | None:
    from .damodaran import empresas_del_sector

    sector, tickers = empresas_del_sector(ticker)
    if not sector:
        return None
    tabla = cotizadas()
    por_ticker = {str(t).upper(): cik for cik, t in tabla["ticker"].items()}
    candidatos = [por_ticker[t] for t in tickers if t in por_ticker and por_ticker[t] != int(cik_propio)]
    if len(candidatos) < MINIMO:
        return None
    elegidos = ordenar_por_tamano(list(dict.fromkeys(candidatos)), ingresos_por_cik(date.today().year - 1), ingresos_propios)[:n]
    return ([str(tabla.loc[c, "ticker"]) for c in elegidos],
            f"sector «{sector}» de Damodaran (NYU Stern), cotizadas en NYSE/Nasdaq, las {n} más parecidas por ingresos")


def _proponer(sic: int, cik_propio: int, ingresos_propios: float | None, n: int) -> tuple[list[str], str]:
    tabla = cotizadas()
    tamano = ingresos_por_cik(date.today().year - 1)
    criterio, codigos = f"SIC {sic}", [sic]
    candidatos = [c for c in dict.fromkeys(ciks_por_sic(sic)) if c in tabla.index and c != int(cik_propio)]
    if len(candidatos) < MINIMO:
        codigos = list(range(sic // 10 * 10, sic // 10 * 10 + 10))
        criterio = f"SIC {sic // 10 * 10}-{sic // 10 * 10 + 9} (ampliado: menos de {MINIMO} cotizadas con SIC {sic})"
        candidatos = [c for s in codigos for c in ciks_por_sic(s)]
        candidatos = [c for c in dict.fromkeys(candidatos) if c in tabla.index and c != int(cik_propio)]
    elegidos = ordenar_por_tamano(candidatos, tamano, ingresos_propios)[:n]
    return [str(tabla.loc[c, "ticker"]) for c in elegidos], f"{criterio}, cotizadas en NYSE/Nasdaq, las {n} más parecidas por ingresos"


PARTIDAS_CRECIMIENTO = ("ingresos", "resultado_operativo", "bpa_diluido")


def crecimiento_3_anios(fuente, por_id, normalizar, cagr, ticker: str) -> dict:
    """Crecimiento anual compuesto de ventas y BPA en los 3 últimos ejercicios fiscales (R10), con el normalizador."""
    ultimos = [h.fiscal_year for c in por_id["ingresos"].conceptos if (h := fuente.fact(c, None)) is not None and h.fiscal_year]
    if not ultimos:
        return {"tacc_ventas_3a": None, "tacc_bpa_3a": None}
    from ..calculo.analitica import estabilidad_margen, margenes_operativos

    fin = max(ultimos)
    anios = list(range(fin - 4, fin + 1))
    e = normalizar(fuente, anios, ticker, PARTIDAS_CRECIMIENTO)  # C5: solo lo necesario (antes, ~50 partidas × 5 años)
    margenes = margenes_operativos(e, anios)
    return {"tacc_ventas_3a": cagr(e.valor("ingresos", fin - 3), e.valor("ingresos", fin), 3),
            "tacc_bpa_3a": cagr(e.valor("bpa_diluido", fin - 3), e.valor("bpa_diluido", fin), 3), "ejercicio_crecimiento": fin,
            "estabilidad_margen_5a": estabilidad_margen(margenes)}  # A5


def _mercado_motor(ticker: str) -> dict:
    """Beta semanal de 5 años y variaciones de 1, 3 y 6 meses (si yfinance no responde, sin dato: la hoja lo marca)."""
    from .mercado import beta_semanal, variaciones

    try:
        return {"beta": beta_semanal(ticker), "variaciones": variaciones(ticker)}
    except Exception as e:  # noqa: BLE001
        log.warning("Comparable %s sin beta ni variaciones: %s", ticker, e)
        return {"beta": None, "variaciones": {}}


def datos(ticker: str) -> dict | None:
    """Fundamentales y múltiplos LTM de un comparable (None si la SEC o el mercado no dan lo necesario)."""
    from edgar import Company

    from ..calculo.metricas import Mercado, cagr, fundamentales, valoracion
    from ..calculo.normalizador import LTM, LTM_PREVIO, POR_ID, FuenteEntityFacts, FuenteLTM, acciones_en_circulacion, normalizar
    from .mercado import cotizacion

    try:
        empresa = Company(ticker)
        ultimo = empresa.get_filings(form=["10-Q", "10-K"], amendments=False).latest()
        facts = empresa.get_facts()
        fecha = date.fromisoformat(str(ultimo.period_of_report))
        estados = normalizar(FuenteLTM(facts, fecha), [LTM_PREVIO, LTM], ticker)
        precio = cotizacion(ticker)
        acciones, _ = acciones_en_circulacion(facts, fecha, estados.valor("acciones_diluidas", LTM))
        if LTM in estados.faltan or not acciones:
            log.warning("Comparable %s sin datos LTM completos: se omite", ticker)
            return None
        f = fundamentales(estados, LTM)
        crecimiento = crecimiento_3_anios(FuenteEntityFacts(facts), POR_ID, normalizar, cagr, ticker)
        return {"ticker": ticker, "nombre": nombre_legible(empresa.name), "fecha_ltm": str(ultimo.period_of_report), "fundamentales": f,
                "multiplos": valoracion(estados, LTM, Mercado(precio.precio, acciones, precio.fecha)), **crecimiento,
                # Motor de valoración (B1): LTM − 1, balance del puente del EV, beta y cotización (hojas Comps y WACC)
                "estados": estados, "acciones": acciones, "cotizacion": precio, "origen": ultimo.accession_no, **_mercado_motor(ticker)}
    except Exception as e:  # noqa: BLE001  (un comparable que falla no rompe el informe: se omite con aviso)
        log.warning("Comparable %s omitido: %s", ticker, e)
        return None
