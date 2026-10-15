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
import re
import warnings
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from statistics import median


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
    Partida("ingresos_intereses", "Ingresos por intereses", ("InvestmentIncomeInterest", "InvestmentIncomeInterestAndDividend",
                                                            "InterestIncomeOther"), opcional=True),
    Partida("bai", "Beneficio antes de impuestos", BAI,
            # ORCL solo declara los dos componentes: EEUU + extranjero (exige los dos; uno solo sería parcial)
            suma=(("IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",),
                  ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign",)), suma_completa=True,
            # ORCL no los declara en los 10-Q: BAI = resultado + impuesto (identidad contable; en FY2026 da exactamente
            # EEUU + extranjero). Primero el de operaciones continuadas, que no arrastra las discontinuadas.
            derivadas=tuple(Derivada(base, ((1, "IncomeTaxExpenseBenefit"),), ("IncomeTaxExpenseBenefit",))
                            for base in ("IncomeLossFromContinuingOperations", "NetIncomeLoss"))),
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
    # Motor de valoración (B1): partidas de las plantillas de LBO y del balance (opcionales: sin dato, la hoja lo marca)
    Partida("fondo_comercio", "Fondo de comercio", ("Goodwill",), opcional=True),
    Partida("intangibles", "Otros intangibles", ("IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet"),
            opcional=True),
    Partida("activos", "Activo total", ("Assets",)),
    Partida("proveedores", "Proveedores (cuentas a pagar)", ("AccountsPayableCurrent", "AccountsPayableTradeCurrent"), opcional=True),
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
            # ORCL en los 10-Q: NotesPayableCurrent (en el 10-K FY2026 = DebtCurrent = 7.199 M); solo si no hay las anteriores
            suma=(("CommercialPaper",), ("ShortTermBorrowings",),
                  ("LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent", "NotesPayableCurrent")),
            opcional=True),
    # ORCL: LongTermNotesAndLoans (no corriente; FY2026: 122.342 + 7.199 corriente = 129.541 = DebtLongtermAndShorttermCombinedAmount).
    # Sin LongTermNotesPayable: incluye la parte corriente. Derivadas: total − corriente (la corriente ya está en deuda_cp).
    Partida("deuda_lp", "Deuda financiera a largo plazo", ("LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations",
                                                          "LongTermNotesAndLoans"),
            opcional=True, derivadas=(
                Derivada("LongTermDebt", ((-1, "LongTermDebtCurrent"),), ("LongTermDebtCurrent",)),
                Derivada("DebtLongtermAndShorttermCombinedAmount", ((-1, "DebtCurrent"),), ("DebtCurrent",)),
                # TSLA: el balance usa un concepto propio; LongTermDebt (nota de deuda, total) − DebtCurrent. Si DebtCurrent
                # incluyera papel comercial, la deuda total quedaría corta en ese importe (nunca inflada); queda avisado.
                Derivada("LongTermDebt", ((-1, "DebtCurrent"),), ("DebtCurrent",)),
            )),
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
    # Otros componentes del EV (calculo/metricas.py). Los arrendamientos OPERATIVOS no entran: en US GAAP su coste ya
    # está dentro del EBITDA, y sumarlos al EV descuadraría el EV/EBITDA (error habitual).
    Partida("preferentes", "Acciones preferentes", ("PreferredStockValue", "PreferredStockValueOutstanding",
                                                    "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount"), opcional=True),
    Partida("pensiones", "Pasivo neto por pensiones", (
        "PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent", "DefinedBenefitPensionPlanLiabilitiesNoncurrent",
        "PensionAndOtherPostretirementAndPostemploymentBenefitPlansLiabilitiesNoncurrent"), opcional=True),
    Partida("arrendamientos_financieros", "Arrendamientos financieros", ("FinanceLeaseLiability",),
            suma=(("FinanceLeaseLiabilityCurrent",), ("FinanceLeaseLiabilityNoncurrent",)), opcional=True),
    # Acciones diluidas del motor (hoja Shares, método del autocartera): opciones ejercitables, RSU y convertibles
    Partida("opciones_ejercitables", "Opciones ejercitables", (
        "ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsExercisableNumber",), opcional=True),
    Partida("precio_ejercicio_opciones", "Precio medio de ejercicio de las opciones ejercitables (USD)", (
        "ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsExercisableWeightedAverageExercisePrice",), opcional=True),
    Partida("rsu_pendientes", "Acciones restringidas (RSU) pendientes de consolidar", (
        "ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsNonvestedNumber",), opcional=True),
    Partida("convertibles", "Bonos convertibles (principal)", ("ConvertibleNotesPayable", "ConvertibleDebtNoncurrent",
                                                                "ConvertibleLongTermNotesPayable"), opcional=True),
    Partida("ratio_conversion", "Ratio de conversión (acciones por 1.000 USD)", ("DebtInstrumentConvertibleConversionRatio1",),
            opcional=True),
    # Flujos de caja
    Partida("flujo_operativo", "Flujo de caja operativo", ("NetCashProvidedByUsedInOperatingActivities",
                                                          "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")),
    Partida("capex", "Inversión en inmovilizado (capex)", ("PaymentsToAcquirePropertyPlantAndEquipment",
                                                          "PaymentsToAcquireProductiveAssets")),
    Partida("amortizacion_intangibles", "Amortización de intangibles", ("AmortizationOfIntangibleAssets",), opcional=True),
    Partida("amortizacion", "Amortizaciones (D&A)", ("DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
                                                    "DepreciationAndAmortization"),
            suma=(("Depreciation",), ("AmortizationOfIntangibleAssets",)),  # MSFT, GOOGL: depreciación + intangibles
            opcional=True),  # sin ella: aviso, EBITDA n.d.
    Partida("pagos_basados_acciones", "Remuneración en acciones", ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
            opcional=True),
    Partida("dividendos", "Dividendos pagados", ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock"), opcional=True),
    Partida("recompras", "Recompra de acciones", ("PaymentsForRepurchaseOfCommonStock",), opcional=True),
    # Información complementaria del estado de flujos (cascada EBITDA → FCF, A9)
    Partida("impuestos_pagados", "Impuestos pagados", ("IncomeTaxesPaidNet", "IncomeTaxesPaid"), opcional=True),
    Partida("intereses_pagados", "Intereses pagados", ("InterestPaidNet", "InterestPaid"), opcional=True),
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


ACCIONES_MEDIAS = ("WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
                   "WeightedAverageNumberOfSharesOutstandingBasic")
ESCALA_MILES = (900.0, 1100.0)  # BN / BPA / acciones declaradas en este rango: acciones etiquetadas en miles


def escalas_acciones(facts) -> dict[str, float]:
    """Filings (accession) que declaran las acciones medias en miles por error de etiquetado: {accession: 1000}.

    IOVA etiqueta 328.721 acciones en lugar de 328,7 millones desde 2019 (el BPA y el beneficio sí son
    correctos). Comprobación determinista con cifras del mismo filing y periodo: beneficio neto / BPA = acciones;
    si las declaradas son ~1.000 veces menores (mediana del filing), se multiplican por 1.000.
    """
    if not hasattr(facts, "get_all_facts"):
        return {}
    grupos = defaultdict(dict)
    for h in facts.get_all_facts():
        c = h.concept.split(":")[-1]
        if h.numeric_value is not None and h.period_start is not None and (
                c == "NetIncomeLoss" or c in ACCIONES_MEDIAS or c in ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted")):
            grupos[(h.accession, h.period_start, h.period_end)].setdefault(c, float(h.numeric_value))
    ratios = defaultdict(list)
    for (accession, _, _), v in grupos.items():
        bpa = v.get("EarningsPerShareDiluted", v.get("EarningsPerShareBasicAndDiluted"))
        acciones = next((v[c] for c in ACCIONES_MEDIAS if v.get(c)), None)
        if v.get("NetIncomeLoss") and bpa and abs(bpa) >= 0.01 and acciones:
            ratios[accession].append(v["NetIncomeLoss"] / bpa / acciones)
    return {a: 1000.0 for a, r in ratios.items() if ESCALA_MILES[0] <= median(r) <= ESCALA_MILES[1]}


def corregir_escala(hechos: list, escalas: dict[str, float]) -> list:
    """Aplica `escalas_acciones` a una lista de FinancialFact de edgartools (solo acciones medias)."""
    if not escalas:
        return hechos
    return [replace(h, value=h.numeric_value * escalas[h.accession], numeric_value=h.numeric_value * escalas[h.accession])
            if h.accession in escalas and h.concept.split(":")[-1] in ACCIONES_MEDIAS and h.numeric_value is not None else h
            for h in hechos]


NOTA_ESCALA = " (declarado en miles en el XBRL: ×1000, comprobado con beneficio neto / BPA)"


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
        self._escalas = escalas_acciones(facts)

    def _escala(self, concepto: str, h) -> float:
        return self._escalas.get(getattr(h, "accession", None), 1.0) if concepto in ACCIONES_MEDIAS else 1.0

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
        return _ajustar_split(concepto, h, self._splits)[0] * self._escala(concepto, h)

    def presentacion(self, concepto: str, ejercicio: int):
        """(cierre del periodo, fecha de presentación) del dato anual: desde cuándo era público."""
        h = self.fact(concepto, ejercicio)
        return (None, None) if h is None else (getattr(h, "period_end", None), getattr(h, "filing_date", None))

    def origen(self, concepto: str, ejercicio: int) -> str:
        h = self.fact(concepto, ejercicio)
        if h is None:
            return ""
        nota = _ajustar_split(concepto, h, self._splits)[1] if getattr(h, "numeric_value", None) is not None else ""
        nota += NOTA_ESCALA if self._escala(concepto, h) != 1.0 else ""
        return str(getattr(h, "accession", "") or "") + nota


LTM, LTM_PREVIO = 1, 0  # claves de los últimos doce meses y de los doce anteriores en EstadosNormalizados
TOLERANCIA_DIAS = 10  # margen entre la fecha pedida y el cierre declarado (semanas fiscales de 52/53)
# Acciones medias: no se suman, se toma el último trimestre. Las mismas alternativas que el anual (XOM solo declara básicas).
PROMEDIOS = set(POR_ID["acciones_diluidas"].conceptos)
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
        self._escalas = escalas_acciones(facts)
        todos = corregir_escala(facts.get_all_facts(), self._escalas)
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
            acciones = next((r for r in (self._valor(c, clave) for c in POR_ID["acciones_diluidas"].conceptos) if r), None)
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
                return h.numeric_value, h.accession + (NOTA_ESCALA if h.accession in self._escalas else "")
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
        componentes = []  # suma parcial: no vale, pero aún puede valer una derivada
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


# ---------------------------------------------------------------------------
# Trimestres (R3): las mismas partidas y prioridades, trimestre a trimestre
# ---------------------------------------------------------------------------
PARTIDAS_TRIMESTRALES = ("ingresos", "resultado_operativo", "beneficio_neto", "acciones_diluidas")


def trimestres(facts, fecha_ltm: date, n: int = 8) -> list[dict]:
    """Últimos `n` trimestres discretos hasta `fecha_ltm` (ingresos, EBIT, beneficio, acciones y BPA).

    Flujos: edgartools `TTMCalculator.quarterize()` (deriva Q2-Q4 de los acumulados y del anual), con las
    mismas partidas derivadas que el anual (p. ej. EBIT = BAI + intereses en JNJ).
    BPA: el diluido declarado del trimestre; el del Q4 (que no se declara) con edgartools
    `derive_eps_for_quarter` (resta exacta si las acciones son estables; si no, BN / acciones).
    Todo ajustado por desdoblamientos. Variación interanual frente al mismo trimestre del año anterior.
    Un concepto solo vale si llega hasta `fecha_ltm` (sin tags abandonados).
    """
    from edgar.ttm import TTMCalculator
    from edgar.ttm.splits import apply_split_adjustments

    splits = desdoblamientos(facts)
    todos = corregir_escala(facts.get_all_facts(), escalas_acciones(facts))
    if splits:
        todos = apply_split_adjustments(todos, splits)
    por_concepto = defaultdict(list)
    for h in todos:
        if h.numeric_value is not None and h.period_end is not None:
            por_concepto[h.concept.split(":")[-1]].append(h)

    def trimestral(concepto: str) -> dict[date, float]:
        hechos = por_concepto.get(concepto, [])
        if concepto in PROMEDIOS or concepto.startswith("EarningsPerShare"):  # no se suman: el declarado del trimestre
            trimestrales = [h for h in hechos if h.period_start and 80 <= (h.period_end - h.period_start).days <= 100]
        else:
            try:
                with _silencio():
                    trimestrales = TTMCalculator([h for h in hechos if str(h.period_type) != "instant"]).quarterize()
            except (ValueError, KeyError, TypeError, ZeroDivisionError):
                return {}
        valores = {}
        for h in sorted(trimestrales, key=lambda x: x.filing_date or date.min):  # el último presentado manda
            valores[h.period_end] = float(h.numeric_value)
        return valores

    def al_dia(valores: dict) -> bool:
        return bool(valores) and abs((max(valores) - fecha_ltm).days) <= TOLERANCIA_DIAS

    def serie(partida: Partida) -> dict[date, float]:
        for concepto in partida.conceptos:
            valores = trimestral(concepto)
            if al_dia(valores):
                return valores
        for d in partida.derivadas:  # misma fórmula que el anual (trazada en el semáforo del anual)
            base = trimestral(d.base)
            if not al_dia(base) or any(not al_dia(trimestral(c)) for c in d.obligatorios):
                continue
            terminos = [(signo, trimestral(c)) for signo, c in d.terminos]
            return {f: v + sum(signo * t.get(f, 0.0) for signo, t in terminos) for f, v in base.items()}
        return {}

    series = {pid: serie(POR_ID[pid]) for pid in PARTIDAS_TRIMESTRALES}
    bpa = {}
    for concepto in POR_ID["bpa_diluido"].conceptos:
        bpa = trimestral(concepto)
        if bpa:
            try:  # Q4: no se declara; edgartools lo deriva (resta exacta o BN / acciones)
                with _silencio():
                    derivados = TTMCalculator(por_concepto.get(concepto, [])).derive_eps_for_quarter(
                        por_concepto.get("NetIncomeLoss", []), por_concepto.get("WeightedAverageNumberOfDilutedSharesOutstanding", []),
                        eps_concept=f"us-gaap:{concepto}")
                for h in derivados:
                    bpa.setdefault(h.period_end, float(h.numeric_value))
            except (ValueError, KeyError, TypeError, ZeroDivisionError, AttributeError):
                pass
            break
    fines = sorted(series["ingresos"])[-(n + 4):]
    filas = []
    for fin in fines:
        def v(pid, f=fin):
            cercanos = [d for d in series[pid] if abs((d - f).days) <= TOLERANCIA_DIAS]
            return series[pid][cercanos[0]] if cercanos else None

        anterior = next((d for d in fines if 350 <= (fin - d).days <= 380), None)
        bpa_trimestre = next((b for d, b in bpa.items() if abs((d - fin).days) <= TOLERANCIA_DIAS), None)
        if bpa_trimestre is None and v("beneficio_neto") is not None and v("acciones_diluidas"):
            bpa_trimestre = v("beneficio_neto") / v("acciones_diluidas")  # como el LTM: BN / acciones diluidas
        filas.append({
            "fin": fin, "ingresos": v("ingresos"), "ebit": v("resultado_operativo"), "beneficio_neto": v("beneficio_neto"),
            "acciones": v("acciones_diluidas"), "bpa": bpa_trimestre,
            "ingresos_anio_anterior": v("ingresos", anterior) if anterior else None,
        })
    for f in filas:
        f["crecimiento_interanual"] = (f["ingresos"] / f["ingresos_anio_anterior"] - 1
                                       if f["ingresos"] and f["ingresos_anio_anterior"] else None)
        f["margen_operativo"] = f["ebit"] / f["ingresos"] if f["ebit"] is not None and f["ingresos"] else None
    return filas[-n:]


# ---------------------------------------------------------------------------
# Segmentos (R14 y tarea A1): desgloses validados de negocio, producto y geografía
# ---------------------------------------------------------------------------
EJES_SEGMENTOS = {"negocio": "StatementBusinessSegmentsAxis", "producto": "ProductOrServiceAxis",
                  "geografia": "StatementGeographicalAxis"}
EJE_CONSOLIDACION, MIEMBRO_SEGMENTOS = "ConsolidationItemsAxis", "OperatingSegmentsMember"
TOLERANCIA_SEGMENTOS = 0.01  # los miembros deben sumar el total consolidado (±1 %)
# D&A y capex por segmento de negocio (ASC 280 los exige si los revisa la dirección; ASU 2023-07 amplía el desglose):
# tags por prioridad; solo los miembros y ejercicios ya validados por los ingresos
SEGMENTO_AMORTIZACION = ("DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
                         "DepreciationAndAmortization", "Depreciation")
SEGMENTO_CAPEX = ("SegmentExpenditureAdditionToLongLivedAssets", "PaymentsToAcquirePropertyPlantAndEquipment",
                  "PaymentsToAcquireProductiveAssets")
PAISES = {"US": "EE. UU.", "CN": "China", "JP": "Japón", "GB": "Reino Unido", "DE": "Alemania", "FR": "Francia", "IN": "India",
          "CA": "Canadá", "MX": "México", "BR": "Brasil", "KR": "Corea del Sur", "TW": "Taiwán", "IE": "Irlanda", "NL": "Países Bajos",
          "CH": "Suiza", "IT": "Italia", "ES": "España", "AU": "Australia", "SG": "Singapur", "IL": "Israel"}


@dataclass
class Desglose:
    eje: str  # "negocio", "producto" o "geografia"
    concepto: str  # tag de ingresos usado
    miembros: dict[str, dict[int, float]] = field(default_factory=dict)  # nombre → ejercicio → ingresos
    resultado_operativo: dict[str, dict[int, float]] = field(default_factory=dict)  # solo negocio
    amortizacion: dict[str, dict[int, float]] = field(default_factory=dict)  # solo negocio (si la empresa lo publica)
    capex: dict[str, dict[int, float]] = field(default_factory=dict)  # solo negocio (si la empresa lo publica)
    ejercicios: list[int] = field(default_factory=list)  # ejercicios que cuadran con el total
    rechazados: dict[int, str] = field(default_factory=dict)  # ejercicio → motivo
    origen: str = ""
    # LTM provisional (decisión F7, abierta): la empresa no lo publica; se calcula con el último 10-Q
    ltm: dict[str, float] = field(default_factory=dict)  # nombre → ingresos LTM
    ltm_origen: str = ""
    ltm_motivo: str = ""  # por qué no hay LTM (vacío si lo hay)


def _nombre_miembro(miembro: str, etiqueta: str | None) -> str:
    """Nombre legible: los países por su código ISO (evita etiquetas erróneas como «U.S. Plans» en JNJ)."""
    if miembro and miembro.startswith("country:"):
        return PAISES.get(miembro.split(":")[1], miembro.split(":")[1])
    if etiqueta:
        return re.sub(r"\s*\[Member\]$", "", str(etiqueta)).strip()
    base = re.sub(r"Member$", "", (miembro or "").split(":")[-1])
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base).strip()


def _local(miembro: str) -> str:
    """Nombre local de un miembro: «aapl:IPhoneMember» y «aapl_IPhoneMember» → «IPhoneMember»."""
    return re.split(r"[:_]", miembro, maxsplit=1)[-1] if miembro else ""


def dominios_declarados(xbrl) -> list[set[str]]:
    """Agrupaciones de miembros que la propia empresa declara (dominio → miembros, linkbase de definición)."""
    try:
        roles = xbrl.parser.domains_by_role
    except AttributeError:
        return []
    grupos = []
    for dominios in roles.values():
        for d in dominios.values():
            miembros = {_local(m) for m in getattr(d, "members", []) or []}
            if len(miembros) >= 2 and miembros not in grupos:
                grupos.append(miembros)
    return grupos


def seleccion_validada(valores: dict[str, float], total: float, grupos: list[set[str]]) -> dict[str, float] | None:
    """Los miembros que forman el desglose: una agrupación DECLARADA por la empresa (o todos los miembros) cuyos
    valores suman el total consolidado (±1 %). Si cuadran varias, la más detallada; si empatan dos distintas, es
    ambiguo y se devuelve None. Nunca se combinan miembros por coincidencia numérica: las empresas declaran a la
    vez subtotales y detalle en el mismo eje (AAPL: «Products» = iPhone + Mac + iPad + Wearables; ORCL:
    «Software Revenues» = licencias + soporte), y una búsqueda combinatoria puede cuadrar por casualidad.
    `valores`: nombre local del miembro → importe.
    """
    if not total or len(valores) < 2:
        return None
    candidatos = [set(valores)] + [g & set(valores) for g in grupos]
    validos = []
    for c in candidatos:
        if len(c) >= 2 and abs(sum(valores[k] for k in c) - total) <= TOLERANCIA_SEGMENTOS * abs(total) and c not in validos:
            validos.append(c)
    if not validos:
        return None
    mayor = max(len(c) for c in validos)
    mejores = [c for c in validos if len(c) == mayor]
    return {k: valores[k] for k in mejores[0]} if len(mejores) == 1 else None


def _hechos_eje(xbrl, concepto: str, eje: str, dias: tuple[int, int] = (350, 380)) -> list[dict]:
    """Hechos de `concepto` desglosados SOLO por `eje` (o por eje + segmentos operativos de consolidación) cuyo
    periodo dura entre `dias` (por defecto, anuales)."""
    try:
        with _silencio():
            df = xbrl.facts.query().by_concept(concepto).by_dimension(eje).to_dataframe()
    except Exception:  # noqa: BLE001  (consultas dimensionales que edgartools no resuelve: sin desglose)
        return []
    if df is None or df.empty or "concept" not in df:
        return []
    df = df[df["concept"] == f"us-gaap:{concepto}"]
    columnas = [c for c in df.columns if c.startswith("dim_")]
    filas = []
    for _, r in df.iterrows():
        dims = {c: r[c] for c in columnas if isinstance(r[c], str) and r[c]}
        propio = [c for c in dims if c.endswith(eje)]
        resto = [c for c in dims if not c.endswith(eje)]
        valido_resto = all(c.endswith(EJE_CONSOLIDACION) and str(dims[c]).endswith(MIEMBRO_SEGMENTOS) for c in resto)
        fechas_ok = all(str(r.get(c) or "")[:4].isdigit() for c in ("period_start", "period_end"))  # sin «nan» ni vacíos
        if len(propio) != 1 or not valido_resto or not fechas_ok:
            continue
        inicio, fin = (date.fromisoformat(str(r[c])[:10]) for c in ("period_start", "period_end"))
        if not dias[0] <= (fin - inicio).days <= dias[1] or r.get("numeric_value") is None:
            continue
        filas.append({"miembro": dims[propio[0]], "etiqueta": r.get("dimension_member_label"), "inicio": inicio, "fin": fin,
                      "valor": float(r["numeric_value"])})
    return filas


def segmentos(xbrls: list[tuple], totales: dict[int, float], fines: dict[int, date]) -> dict[str, Desglose]:
    """Desgloses de ingresos por eje para los ejercicios de `totales`, solo con los años que cuadran.

    `xbrls`: [(xbrl, accession), …] del 10-K más reciente al más antiguo (los años solapados los da el más
    reciente, que recoge las reexpresiones). `fines`: cierre de cada ejercicio, para fechar cada hecho.
    Nunca se muestra un desglose que no sume el total: ese año queda en `rechazados` con el motivo.
    """
    def ejercicio_de(fin) -> int | None:
        fin = fin if isinstance(fin, date) else date.fromisoformat(str(fin)[:10])
        return next((ej for ej, f in fines.items() if f and abs((fin - f).days) <= TOLERANCIA_DIAS), None)

    salida = {}
    for clave, eje in EJES_SEGMENTOS.items():
        d = Desglose(clave, "")
        crudo: dict[int, dict[str, tuple[str, float]]] = {}
        grupos_de: dict[int, list[set[str]]] = {}
        for xbrl, accession in xbrls:
            for concepto in POR_ID["ingresos"].conceptos:
                filas = _hechos_eje(xbrl, concepto, eje)
                if filas:
                    d.concepto = d.concepto or concepto
                    grupos = dominios_declarados(xbrl)
                    nuevos = {}
                    for f in filas:
                        ej = ejercicio_de(f["fin"])
                        if ej in totales and ej not in crudo:  # cada año, del 10-K más reciente que lo trae
                            nuevos.setdefault(ej, {}).setdefault(_local(f["miembro"]),
                                                                 (_nombre_miembro(f["miembro"], f["etiqueta"]), f["valor"]))
                    for ej, miembros in nuevos.items():
                        crudo[ej], grupos_de[ej] = miembros, grupos
                    d.origen = d.origen or accession
                    break
            if clave == "negocio":
                for f in _hechos_eje(xbrl, "OperatingIncomeLoss", eje):
                    ej = ejercicio_de(f["fin"])
                    if ej in totales:
                        nombre = _nombre_miembro(f["miembro"], f["etiqueta"])
                        d.resultado_operativo.setdefault(nombre, {}).setdefault(ej, f["valor"])
                for destino, conceptos in ((d.amortizacion, SEGMENTO_AMORTIZACION), (d.capex, SEGMENTO_CAPEX)):
                    for concepto in conceptos:  # el primer tag con datos en este 10-K
                        filas = _hechos_eje(xbrl, concepto, eje)
                        for f in filas:
                            ej = ejercicio_de(f["fin"])
                            if ej in totales:
                                destino.setdefault(_nombre_miembro(f["miembro"], f["etiqueta"]), {}).setdefault(ej, abs(f["valor"]))
                        if filas:
                            break
        for ej, miembros in sorted(crudo.items()):
            valores = {local: valor for local, (_, valor) in miembros.items()}
            elegidos = seleccion_validada(valores, totales[ej], grupos_de.get(ej, []))
            if elegidos:
                d.ejercicios.append(ej)
                for local in elegidos:
                    nombre, valor = miembros[local]
                    d.miembros.setdefault(nombre, {})[ej] = valor
            else:
                d.rechazados[ej] = (f"ninguna agrupación declarada suma los ingresos ({totales[ej] / 1e6:,.0f} USD mn; "
                                    f"suma de todos los miembros: {sum(valores.values()) / 1e6:,.0f})")
        # Resultado por segmento solo donde sus ingresos están validados ese año (evita mezclar nombres antiguos y nuevos)
        d.resultado_operativo = {k: {ej: x for ej, x in v.items() if ej in d.miembros.get(k, {})}
                                 for k, v in d.resultado_operativo.items() if k in d.miembros}
        d.resultado_operativo = {k: v for k, v in d.resultado_operativo.items() if v}
        for atributo in ("amortizacion", "capex"):
            valores = {k: {ej: x for ej, x in v.items() if ej in d.miembros.get(k, {})} for k, v in getattr(d, atributo).items()
                       if k in d.miembros}
            setattr(d, atributo, {k: v for k, v in valores.items() if v})
        if d.ejercicios:
            salida[clave] = d
    return salida


def segmentos_ltm(desgloses: dict[str, Desglose], xbrl_10q, accession: str, ejercicio: int, fin_ejercicio: date,
                  fecha_ltm: date, total_ltm: float | None) -> None:
    """LTM provisional por segmento (decisión F7 del usuario, abierta): las empresas no lo publican.

    LTM = último ejercicio + acumulado del año en curso − acumulado del mismo periodo del año anterior, con los
    hechos del último 10-Q (que trae los dos acumulados). Solo se publica si están todos los miembros del último
    ejercicio y la suma cuadra con los ingresos LTM consolidados (±1 %); si no, queda el motivo en `ltm_motivo`.
    Rellena `ltm`, `ltm_origen` y `ltm_motivo` de cada desglose.
    """
    inicio_actual = fin_ejercicio + timedelta(days=1)
    for d in desgloses.values():
        if ejercicio not in d.ejercicios:
            d.ltm_motivo = f"el último ejercicio (FY{ejercicio}) no tiene desglose validado"
            continue
        actual, anterior = {}, {}
        for f in _hechos_eje(xbrl_10q, d.concepto, EJES_SEGMENTOS[d.eje], dias=(80, 290)):
            nombre = _nombre_miembro(f["miembro"], f["etiqueta"])
            if abs((f["fin"] - fecha_ltm).days) <= TOLERANCIA_DIAS and abs((f["inicio"] - inicio_actual).days) <= TOLERANCIA_DIAS:
                actual.setdefault(nombre, f["valor"])
            elif (abs((f["fin"] - (fecha_ltm - timedelta(days=364))).days) <= TOLERANCIA_DIAS
                  and abs((f["inicio"] - (inicio_actual - timedelta(days=364))).days) <= TOLERANCIA_DIAS):
                anterior.setdefault(nombre, f["valor"])
        nombres = [n for n, s in d.miembros.items() if ejercicio in s]
        faltan = [n for n in nombres if n not in actual or n not in anterior]
        if faltan:
            d.ltm_motivo = f"el 10-Q no trae los dos acumulados de: {', '.join(faltan)}"
            continue
        ltm = {n: d.miembros[n][ejercicio] + actual[n] - anterior[n] for n in nombres}
        if not total_ltm or abs(sum(ltm.values()) - total_ltm) > TOLERANCIA_SEGMENTOS * abs(total_ltm):
            d.ltm_motivo = (f"la suma ({sum(ltm.values()) / 1e6:,.0f} USD mn) no cuadra con los ingresos LTM"
                            + (f" ({total_ltm / 1e6:,.0f})" if total_ltm else ""))
            continue
        d.ltm, d.ltm_origen = ltm, accession


# --- Concentración de clientes (A3) ------------------------------------------------------------------------------
EJE_CLIENTES = "MajorCustomersAxis"
BASES_CONCENTRACION = {  # miembro de ConcentrationRiskByBenchmarkAxis → base del porcentaje (literal de la empresa)
    "RevenueFromContractWithCustomerMember": "Ingresos", "SalesRevenueNetMember": "Ingresos", "RevenueBenchmarkMember": "Ingresos",
    "RevenueFromContractWithCustomerProductAndServiceBenchmarkMember": "Ingresos",
    "AccountsReceivableMember": "Cuentas a cobrar", "TradeAccountsReceivableMember": "Cuentas a cobrar",
}
TIPOS_CONCENTRACION = {"CustomerConcentrationRiskMember", "CreditConcentrationRiskMember"}
EJES_CONCENTRACION = ("MajorCustomersAxis", "ConcentrationRiskByBenchmarkAxis", "ConcentrationRiskByTypeAxis")


def concentracion_clientes(xbrl, fines: dict[int, date]) -> list[dict]:
    """Clientes que la empresa declara como concentración de riesgo (`ConcentrationRiskPercentage1` del 10-K).

    Solo bases de ingresos o de cuentas a cobrar (los proveedores y otras bases quedan fuera) y sin los miembros
    residuales («Other customers»). Si el porcentaje viene además atribuido a un segmento o región, se muestra ese
    detalle tal cual lo declara la empresa, sin reinterpretar la base. Filas: cliente, base, detalle y
    {ejercicio: porcentaje}.
    """
    try:
        with _silencio():
            df = xbrl.facts.query().by_concept("ConcentrationRiskPercentage1").by_dimension(f"srt:{EJE_CLIENTES}").to_dataframe()
    except Exception:  # noqa: BLE001  (sin el concepto: la empresa no declara concentraciones)
        return []
    if df is None or df.empty:
        return []
    columnas = [c for c in df.columns if c.startswith("dim_")]
    filas: dict[tuple, dict] = {}
    for _, r in df.iterrows():
        dims = {c.split("_", 2)[-1]: str(r[c]) for c in columnas if isinstance(r[c], str) and r[c]}
        cliente = next((v for k, v in dims.items() if k.endswith(EJE_CLIENTES)), "")
        base = next((BASES_CONCENTRACION.get(_local(v)) for k, v in dims.items() if k.endswith("ConcentrationRiskByBenchmarkAxis")), None)
        tipo = next((_local(v) for k, v in dims.items() if k.endswith("ConcentrationRiskByTypeAxis")), "")
        if not cliente or base is None or tipo not in TIPOS_CONCENTRACION or "Other" in _local(cliente):
            continue
        fin = date.fromisoformat(str(r["period_end"])[:10]) if r.get("period_end") else None
        ej = next((a for a, f in fines.items() if f and fin and abs((fin - f).days) <= TOLERANCIA_DIAS), None)
        if ej is None or r.get("numeric_value") is None:
            continue
        extra = [_nombre_miembro(v, None) for k, v in dims.items() if not k.endswith(EJES_CONCENTRACION)]
        clave = (_nombre_miembro(cliente, r.get("dimension_member_label")), base, " · ".join(extra))
        filas.setdefault(clave, {"cliente": clave[0], "base": base, "detalle": clave[2], "valores": {}})["valores"].setdefault(
            ej, float(r["numeric_value"]))
    return sorted(filas.values(), key=lambda f: (f["base"] != "Ingresos", -max(f["valores"].values())))


# --- Perfil de vencimientos de deuda (A9) --------------------------------------------------------------------------
VENCIMIENTOS = ("LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
                "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",
                "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive", "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive")
# Total con el que se contrastan (principal de la deuda): el primero declarado
REFERENCIAS_VENCIMIENTOS = ("DebtInstrumentCarryingAmount", "DebtInstrumentFaceAmount", "LongTermDebt")
TOLERANCIA_VENCIMIENTOS = 0.02  # principal frente a valor contable (descuentos, costes de emisión)


def vencimientos_deuda(fuente, ejercicio: int) -> dict:
    """Vencimientos de principal declarados en el 10-K (ASC 470) y su contraste con la deuda declarada.

    Solo se publican si su suma cuadra (±2 %) con el principal o el valor contable de la deuda que declara la
    empresa: si no, `importes` queda vacío y `motivo` dice por qué. Un año sin dato queda en None (no se pone 0).
    """
    importes = [fuente.hecho(c, ejercicio) for c in VENCIMIENTOS]
    if not any(importes):
        return {"importes": [], "motivo": "la empresa no declara vencimientos de deuda en el XBRL"}
    suma = sum(x for x in importes if x)
    referencia = next(((c, v) for c in REFERENCIAS_VENCIMIENTOS if (v := fuente.hecho(c, ejercicio))), None)
    if referencia is None:
        ref_cp, ref_lp = fuente.hecho("LongTermDebtCurrent", ejercicio), fuente.hecho("LongTermDebtNoncurrent", ejercicio)
        referencia = ("LongTermDebtCurrent + LongTermDebtNoncurrent", (ref_cp or 0) + ref_lp) if ref_lp else None
    if referencia is None or abs(suma - referencia[1]) > TOLERANCIA_VENCIMIENTOS * referencia[1]:
        return {"importes": [], "motivo": "los vencimientos declarados no cuadran con la deuda declarada"}
    return {"importes": importes, "suma": suma, "referencia": referencia[0], "valor_referencia": referencia[1], "motivo": ""}
