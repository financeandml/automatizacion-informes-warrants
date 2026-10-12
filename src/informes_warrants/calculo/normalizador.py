"""Normalizador SEC: el único punto que traduce tags XBRL a partidas canónicas.

Regla de cero alucinaciones: cada partida se lee de una lista EXACTA de tags us-gaap por orden de
prioridad (p. ej. `RevenueFromContractWithCustomerExcludingAssessedTax` → `Revenues` →
`SalesRevenueNet`), sin desgloses dimensionales, del ejercicio fiscal pedido. Nunca se estima.

Por qué no se usa directamente `standard_concept` de edgartools (aunque se probó primero): en el
10-K 2023 de AAPL etiqueta los dividendos pagados como `DistributionsToMinorityInterests`, repite
`NetCashFromInvestingActivities` y llama `IncomeTaxes`/`InterestExpense` tanto al gasto del P&L como
a lo pagado en caja. La jerarquía de ingresos sigue la de edgartools `RevenueDeduplicator`
(ASC 606 > Revenues > SalesRevenueNet > Revenue).

Las fuentes de hechos son intercambiables: un XBRL concreto (`FuenteXBRL`, p. ej. el 10-K de
referencia de los tests), el histórico completo de la empresa (`FuenteEntityFacts`) o los últimos
doce meses (`FuenteLTM`). Todas pasan por las mismas partidas y prioridades.
"""

import logging
import warnings
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True)
class Derivada:
    """Partida calculada con conceptos declarados cuando la empresa no declara el total.

    valor = base + Σ (signo · término). `obligatorios`: términos sin los que no se calcula (el resto, si
    no se declaran, cuentan 0). El concepto que queda en la trazabilidad dice la fórmula exacta.
    """

    base: str
    terminos: tuple[tuple[int, str], ...]  # (signo, concepto)
    obligatorios: tuple[str, ...] = ()


@dataclass(frozen=True)
class Partida:
    id: str
    nombre: str
    conceptos: tuple[str, ...] = ()  # alternativas por prioridad (sin prefijo us-gaap:)
    suma: tuple[tuple[str, ...], ...] = ()  # si no hay concepto total: suma de componentes (cada uno con alternativas)
    opcional: bool = False  # si no se declara, no es un error (queda sin dato; nunca se inventa un 0)
    suma_completa: bool = False  # la suma solo vale si están todos los componentes (si falta uno, la partida queda n.d.)
    derivadas: tuple[Derivada, ...] = ()  # último recurso, por orden: fórmulas con conceptos declarados


BAI = ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
       "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments")
# (Sin `…BeforeIncomeTaxesDomestic`: es solo el beneficio en EEUU, no el total.)

PARTIDAS: tuple[Partida, ...] = (
    # Cuenta de resultados
    Partida("ingresos", "Ingresos", ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
                                     "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenue")),
    Partida("coste_ventas", "Coste de ventas", ("CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfServices"),
            opcional=True),  # p. ej. las petroleras (XOM) no lo presentan: margen bruto n.d., nunca estimado
    Partida("beneficio_bruto", "Beneficio bruto", ("GrossProfit",), opcional=True),  # si falta, se calcula y se contrasta
    Partida("id", "I+D", ("ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"),
            opcional=True),
    Partida("gastos_generales", "Gastos generales y de venta", ("SellingGeneralAndAdministrativeExpense",),
            suma=(("SellingAndMarketingExpense",), ("GeneralAndAdministrativeExpense",)), opcional=True,
            suma_completa=True),  # MSFT, GOOGL: ventas y marketing + generales por separado
    # JNJ, XOM y otras no presentan resultado operativo: EBIT = BAI + gasto por intereses (convención habitual), con un
    # solo concepto de intereses (el primero declarado) para no sumarlo dos veces; sin intereses declarados, EBIT = BAI.
    Partida("resultado_operativo", "Resultado operativo (EBIT)", ("OperatingIncomeLoss",), derivadas=tuple(
        Derivada(bai, ((1, interes),) if interes else (), (interes,) if interes else ())
        for bai in BAI for interes in ("InterestExpense", "InterestExpenseNonoperating", None))),
    Partida("gasto_intereses", "Gasto por intereses", ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"),
            opcional=True),
    Partida("bai", "Beneficio antes de impuestos", BAI,
            # ORCL solo declara los dos componentes: EEUU + extranjero (exige los dos; uno solo sería parcial)
            suma=(("IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",),
                  ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign",)), suma_completa=True),
    Partida("impuestos", "Impuesto sobre beneficios", ("IncomeTaxExpenseBenefit",)),
    Partida("beneficio_neto", "Beneficio neto atribuible", ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic",
                                                            "ProfitLoss")),
    Partida("bpa_diluido", "BPA diluido (USD)", ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted")),
    Partida("acciones_diluidas", "Acciones medias diluidas", ("WeightedAverageNumberOfDilutedSharesOutstanding",
                                                              "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
                                                              # sin dilución declarada (XOM): diluidas = básicas
                                                              "WeightedAverageNumberOfSharesOutstandingBasic")),
    # Balance
    Partida("caja", "Caja y equivalentes", ("CashAndCashEquivalentsAtCarryingValue",
                                            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")),
    Partida("inversiones_cp", "Inversiones financieras a corto plazo", ("MarketableSecuritiesCurrent", "ShortTermInvestments",
                                                                         "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
            opcional=True),
    Partida("clientes", "Clientes (cuentas a cobrar)", ("AccountsReceivableNetCurrent", "ReceivablesNetCurrent"), opcional=True),
    Partida("existencias", "Existencias", ("InventoryNet", "InventoryFinishedGoodsNetOfReserves"), opcional=True),
    Partida("activo_corriente", "Activo corriente", ("AssetsCurrent",)),
    Partida("inmovilizado", "Inmovilizado material neto", (
        "PropertyPlantAndEquipmentNet",
        "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization"), opcional=True),
    Partida("activos", "Activo total", ("Assets",)),
    Partida("pasivo_corriente", "Pasivo corriente", ("LiabilitiesCurrent",)),
    Partida("pasivos", "Pasivo total", ("Liabilities",), derivadas=(
        # KO no declara el total: pasivo = pasivo y patrimonio − patrimonio (con minoritarios) − patrimonio temporal
        Derivada("LiabilitiesAndStockholdersEquity",
                 ((-1, "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
                  (-1, "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests")),
                 ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",)),
        Derivada("LiabilitiesAndStockholdersEquity",
                 ((-1, "StockholdersEquity"), (-1, "MinorityInterest"),
                  (-1, "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests")),
                 ("StockholdersEquity",)),
    )),
    Partida("deuda_cp", "Deuda financiera a corto plazo", ("DebtCurrent",),
            suma=(("CommercialPaper",), ("ShortTermBorrowings",), ("LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent")),
            opcional=True),
    Partida("deuda_lp", "Deuda financiera a largo plazo", ("LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"),
            opcional=True),
    Partida("patrimonio", "Patrimonio neto atribuible", ("StockholdersEquity",), derivadas=(
        # JNJ, RIVN solo declaran el patrimonio con minoritarios: se restan los minoritarios si los hay
        Derivada("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", ((-1, "MinorityInterest"),)),
    )),
    Partida("patrimonio_temporal", "Patrimonio temporal (rescatable)", (
        "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        "RedeemableNoncontrollingInterestEquityCarryingAmount", "TemporaryEquityCarryingAmountAttributableToParent"),
            opcional=True),  # TSLA 2020: necesario para que cuadre activo = pasivo + patrimonio
    Partida("reservas", "Beneficios retenidos (reservas)", ("RetainedEarningsAccumulatedDeficit",), opcional=True),
    Partida("minoritarios", "Intereses minoritarios", ("MinorityInterest",), opcional=True),
    # Flujos de caja
    Partida("flujo_operativo", "Flujo de caja operativo", ("NetCashProvidedByUsedInOperatingActivities",
                                                          "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")),
    Partida("capex", "Inversión en inmovilizado (capex)", ("PaymentsToAcquirePropertyPlantAndEquipment",
                                                          "PaymentsToAcquireProductiveAssets")),
    Partida("amortizacion", "Amortizaciones (D&A)", ("DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
                                                    "DepreciationAndAmortization"),
            suma=(("Depreciation",), ("AmortizationOfIntangibleAssets",)),  # MSFT, GOOGL: depreciación + intangibles
            opcional=True),  # sin ella: aviso, EBITDA n.d.
    Partida("pagos_basados_acciones", "Remuneración en acciones", ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
            opcional=True),
    Partida("dividendos", "Dividendos pagados", ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock"), opcional=True),
    Partida("recompras", "Recompra de acciones", ("PaymentsForRepurchaseOfCommonStock",), opcional=True),
)
POR_ID = {p.id: p for p in PARTIDAS}


@dataclass(frozen=True)
class Dato:
    valor: float
    concepto: str  # tag us-gaap usado (o suma de tags)
    ejercicio: int
    origen: str  # accession del filing u otra referencia


@dataclass
class EstadosNormalizados:
    empresa: str
    ejercicios: list[int]
    datos: dict[str, dict[int, Dato]] = field(default_factory=dict)  # partida → ejercicio → dato
    faltan: dict[int, list[str]] = field(default_factory=dict)  # ejercicio → partidas obligatorias sin dato

    def valor(self, partida: str, ejercicio: int) -> float | None:
        dato = self.datos.get(partida, {}).get(ejercicio)
        return None if dato is None else dato.valor


class FuenteXBRL:
    """Hechos de un único filing XBRL (los que trae para su ejercicio y los comparativos)."""

    def __init__(self, xbrl, accession: str):
        df = xbrl.facts.query().to_dataframe()
        df = df[(~df["is_dimensioned"].astype(bool)) & df["numeric_value"].notna()].copy()
        df["concepto"] = df["concept"].str.split(":").str[-1]
        dias = (df["period_end"].astype("datetime64[ns]") - df["period_start"].astype("datetime64[ns]")).dt.days
        saldo = df["period_type"].eq("instant")  # los saldos no traen fiscal_period
        flujo_anual = dias.between(350, 380) & df["fiscal_period"].eq("FY")
        df["fecha"] = df["period_instant"].fillna(df["period_end"])
        self._df = df[saldo | flujo_anual]
        self.accession = accession

    def hecho(self, concepto: str, ejercicio: int) -> float | None:
        filas = self._df[(self._df["concepto"] == concepto) & (self._df["fiscal_year"] == ejercicio)]
        if filas.empty:
            return None
        return float(filas.sort_values("fecha")["numeric_value"].iloc[-1])  # el cierre del ejercicio es la última fecha

    def origen(self, concepto: str, ejercicio: int) -> str:
        return self.accession


@contextmanager
def _silencio():
    """edgartools avisa (warnings y logging) de cada concepto no declarado: aquí es lo esperado."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        previo = logging.root.manager.disable
        logging.disable(logging.WARNING)
        try:
            yield
        finally:
            logging.disable(previo)


AJUSTABLES_SPLIT = {"WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
                    "WeightedAverageNumberOfSharesOutstandingBasic", "EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"}


def desdoblamientos(facts) -> list[dict]:
    """Desdoblamientos de acciones declarados (edgartools `ttm.splits.detect_splits`: fecha y ratio)."""
    from edgar.ttm.splits import detect_splits

    if not hasattr(facts, "get_all_facts"):  # fuentes de prueba sin el histórico completo
        return []
    with _silencio():
        return detect_splits(facts.get_all_facts())


def factor_split(hecho, splits: list[dict]) -> float:
    """Ratio acumulado de los desdoblamientos posteriores al dato que no estaban en el filing que lo declaró
    (misma regla que edgartools `apply_split_adjustments`). 1 = sin ajuste."""
    factor = 1.0
    for s in splits:
        if s["date"] > hecho.period_end and (not hecho.filing_date or hecho.filing_date <= s["date"]):
            factor *= s["ratio"]
    return factor


def _ajustar_split(concepto: str, hecho, splits: list[dict]) -> tuple[float, str]:
    """(valor ajustado, nota para la trazabilidad): acciones × ratio, BPA ÷ ratio."""
    factor = factor_split(hecho, splits) if concepto in AJUSTABLES_SPLIT else 1.0
    if factor == 1.0:
        return float(hecho.numeric_value), ""
    valor = hecho.numeric_value / factor if concepto.startswith("EarningsPerShare") else hecho.numeric_value * factor
    return float(valor), f" (ajustado por desdoblamiento {factor:g}:1)"


class FuenteEntityFacts:
    """Histórico completo de la empresa (companyfacts de la SEC vía edgartools `Company.get_facts()`).

    Las acciones y el BPA se ajustan por los desdoblamientos posteriores (p. ej. NFLX 10:1 en noviembre
    de 2025): sin el ajuste, la serie mezclaría cifras antes y después del desdoblamiento.
    """

    def __init__(self, facts):
        self._facts, self._cache = facts, {}
        self._splits = desdoblamientos(facts)

    def fact(self, concepto: str, ejercicio: int | None):
        """FinancialFact anual de edgartools (con fiscal_year y accession); None = el último ejercicio."""
        clave = (concepto, ejercicio)
        if clave not in self._cache:
            with _silencio():
                self._cache[clave] = self._facts.get_annual_fact(concepto, ejercicio)
        return self._cache[clave]

    def hecho(self, concepto: str, ejercicio: int) -> float | None:
        h = self.fact(concepto, ejercicio)
        if h is None or getattr(h, "numeric_value", None) is None:
            return None
        return _ajustar_split(concepto, h, self._splits)[0]

    def origen(self, concepto: str, ejercicio: int) -> str:
        h = self.fact(concepto, ejercicio)
        if h is None:
            return ""
        nota = _ajustar_split(concepto, h, self._splits)[1] if getattr(h, "numeric_value", None) is not None else ""
        return str(getattr(h, "accession", "") or "") + nota


LTM, LTM_PREVIO = 1, 0  # claves de los últimos doce meses y de los doce anteriores en EstadosNormalizados
TOLERANCIA_DIAS = 10  # margen entre la fecha pedida y el cierre declarado (semanas fiscales de 52/53)
PROMEDIOS = {"WeightedAverageNumberOfDilutedSharesOutstanding"}  # no se suman: se toma el último trimestre
POR_ACCION = {"EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"}  # LTM = BN LTM / acciones diluidas del trimestre


class FuenteLTM:
    """Últimos doce meses (LTM) desde companyfacts, con las mismas partidas y prioridades que el anual.

    - Flujos (cuenta de resultados y caja): suma de los 4 últimos trimestres con edgartools
      `ttm.TTMCalculator` (deriva el Q4 = FY − 9M y los trimestres a partir de los acumulados). Solo se
      acepta si la ventana termina en la fecha pedida y no tiene huecos: así un tag abandonado (en AAPL,
      `Revenues` tiene su último dato en 2018) nunca entra (la misma trampa que edgartools GH #893).
    - Saldos (balance): el del cierre del último trimestre.
    - Promedios (acciones diluidas): el del último trimestre.
    Claves: LTM = cierre del último 10-Q/10-K; LTM_PREVIO = un año antes (para el crecimiento).
    """

    def __init__(self, facts, fecha: date):
        from edgar.ttm.splits import apply_split_adjustments

        self._por_concepto = defaultdict(list)
        splits = desdoblamientos(facts)
        todos = facts.get_all_facts()
        if splits:  # acciones y BPA comparables a lo largo del tiempo (edgartools `apply_split_adjustments`)
            todos = apply_split_adjustments(todos, splits)
        for h in todos:
            if h.numeric_value is not None and h.period_end is not None:
                self._por_concepto[h.concept.split(":")[-1]].append(h)
        self.fechas = {LTM: fecha, LTM_PREVIO: fecha - timedelta(days=364)}
        self._cache = {}

    def _calcular(self, concepto: str, clave: int):
        from edgar.ttm import TTMCalculator

        objetivo = self.fechas[clave]

        def cerca(d):
            return d is not None and abs((d - objetivo).days) <= TOLERANCIA_DIAS

        def dias(h):
            return (h.period_end - h.period_start).days if h.period_start else 0

        def ultimo(candidatos):  # el último presentado (recoge las reexpresiones)
            return max(candidatos, key=lambda h: h.filing_date or date.min)

        if concepto in POR_ACCION:  # el BPA no se suma por trimestres (cada uno usa sus acciones): se recalcula
            bn = self._valor("NetIncomeLoss", clave)
            acciones = self._valor("WeightedAverageNumberOfDilutedSharesOutstanding", clave)
            if bn is None or acciones is None or not acciones[0]:
                return None
            return bn[0] / acciones[0], f"{bn[1]}; BN LTM / acciones diluidas"
        hechos = self._por_concepto.get(concepto, [])
        saldos = [h for h in hechos if str(h.period_type) == "instant" and cerca(h.period_end)]
        if saldos:
            h = ultimo(saldos)
            return h.numeric_value, h.accession
        if concepto in PROMEDIOS:
            trimestre = [h for h in hechos if cerca(h.period_end) and 80 <= dias(h) <= 100]
            anual = [h for h in hechos if cerca(h.period_end) and 350 <= dias(h) <= 380]
            if trimestre or anual:
                h = ultimo(trimestre or anual)
                return h.numeric_value, h.accession
            return None
        flujos = [h for h in hechos if str(h.period_type) != "instant"]
        if not flujos:
            return None
        try:
            with _silencio():
                m = TTMCalculator(flujos).calculate_ttm(as_of=objetivo + timedelta(days=TOLERANCIA_DIAS))
        except (ValueError, KeyError, TypeError, ZeroDivisionError):
            return None
        if m.has_gaps or not cerca(m.as_of_date):
            return None
        accession = next((h.accession for h in reversed(m.period_facts) if getattr(h, "accession", None)), "")
        return m.value, accession

    def _valor(self, concepto: str, clave: int):
        if (concepto, clave) not in self._cache:
            self._cache[(concepto, clave)] = self._calcular(concepto, clave)
        return self._cache[(concepto, clave)]

    def hecho(self, concepto: str, clave: int) -> float | None:
        r = self._valor(concepto, clave)
        return None if r is None else float(r[0])

    def origen(self, concepto: str, clave: int) -> str:
        r = self._valor(concepto, clave)
        return "" if r is None else f"{r[1]} (LTM a {self.fechas[clave].isoformat()})"


ANTIGUEDAD_MAX_ACCIONES = 200  # días: la portada de cada 10-Q/10-K declara las acciones; más antiguo = desfasado


def acciones_en_circulacion(facts, fecha_ltm: date, respaldo: float | None) -> tuple[float | None, str]:
    """Acciones en circulación (dei de la portada del último filing) con control de antigüedad.

    edgartools `EntityFacts.shares_outstanding` puede devolver un dato viejo (BRK-B: 941.481 acciones de
    2011) o no traer fecha (empresas con varias clases): si el dato es antiguo se usa el `respaldo`
    (acciones diluidas del último trimestre) y se dice en el origen.
    """
    with _silencio():
        hecho = facts.shares_outstanding_fact
        valor = facts.shares_outstanding
    fin = getattr(hecho, "period_end", None)
    if hecho is not None and fin is not None and (fecha_ltm - fin).days <= ANTIGUEDAD_MAX_ACCIONES and valor:
        return float(valor), f"dei:EntityCommonStockSharesOutstanding a {fin} ({getattr(hecho, 'accession', '')})"
    if hecho is None and valor:  # varias clases: edgartools las agrega sin fecha
        return float(valor), "edgartools shares_outstanding (suma de clases, sin fecha)"
    if respaldo:
        return float(respaldo), f"acciones diluidas del último trimestre (portada desfasada: {fin})"
    return None, "sin dato"


def ltm_desde_anual(estados: "EstadosNormalizados", ejercicio: int) -> "EstadosNormalizados":
    """Si el último informe periódico es el anual (o no hay trimestres, como en los 20-F), el LTM es ese ejercicio."""
    ltm = EstadosNormalizados(estados.empresa, [LTM_PREVIO, LTM])
    for clave, ej in ((LTM, ejercicio), (LTM_PREVIO, ejercicio - 1)):
        for pid, por_ejercicio in estados.datos.items():
            if ej in por_ejercicio:
                ltm.datos.setdefault(pid, {})[clave] = por_ejercicio[ej]
        if ej in estados.faltan:
            ltm.faltan[clave] = estados.faltan[ej]
    return ltm


def _resolver(fuente, partida: Partida, ejercicio: int) -> Dato | None:
    for concepto in partida.conceptos:
        valor = fuente.hecho(concepto, ejercicio)
        if valor is not None:
            return Dato(valor, concepto, ejercicio, fuente.origen(concepto, ejercicio))
    componentes = []
    for alternativas in partida.suma:
        for concepto in alternativas:
            valor = fuente.hecho(concepto, ejercicio)
            if valor is not None:
                componentes.append((concepto, valor))
                break
    if partida.suma_completa and len(componentes) < len(partida.suma):
        return None
    if componentes:
        return Dato(sum(v for _, v in componentes), " + ".join(c for c, _ in componentes), ejercicio,
                    fuente.origen(componentes[0][0], ejercicio))
    for d in partida.derivadas:
        base = fuente.hecho(d.base, ejercicio)
        if base is None or any(fuente.hecho(c, ejercicio) is None for c in d.obligatorios):
            continue
        valor, formula = base, d.base
        for signo, concepto in d.terminos:
            termino = fuente.hecho(concepto, ejercicio)
            if termino is not None:
                valor += signo * termino
                formula += f" {'+' if signo > 0 else '−'} {concepto}"
        return Dato(valor, formula, ejercicio, fuente.origen(d.base, ejercicio))
    return None


def normalizar(fuente, ejercicios: list[int], empresa: str = "") -> EstadosNormalizados:
    """Partidas canónicas de cada ejercicio con su tag y su origen."""
    estados = EstadosNormalizados(empresa, sorted(ejercicios))
    for ejercicio in estados.ejercicios:
        for partida in PARTIDAS:
            dato = _resolver(fuente, partida, ejercicio)
            if dato is None and not partida.opcional:
                estados.faltan.setdefault(ejercicio, []).append(partida.id)
            elif dato is not None:
                estados.datos.setdefault(partida.id, {})[ejercicio] = dato
    return estados
