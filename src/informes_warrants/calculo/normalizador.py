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
referencia de los tests) o el histórico completo de la empresa (`FuenteEntityFacts`).
"""

import logging
import warnings
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Partida:
    id: str
    nombre: str
    conceptos: tuple[str, ...] = ()  # alternativas por prioridad (sin prefijo us-gaap:)
    suma: tuple[tuple[str, ...], ...] = ()  # si no hay concepto total: suma de componentes (cada uno con alternativas)
    opcional: bool = False  # si no se declara, no es un error (queda sin dato; nunca se inventa un 0)


PARTIDAS: tuple[Partida, ...] = (
    # Cuenta de resultados
    Partida("ingresos", "Ingresos", ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
                                     "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenue")),
    Partida("coste_ventas", "Coste de ventas", ("CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfServices")),
    Partida("beneficio_bruto", "Beneficio bruto", ("GrossProfit",), opcional=True),  # si falta, se calcula y se contrasta
    Partida("id", "I+D", ("ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"),
            opcional=True),
    Partida("gastos_generales", "Gastos generales y de venta", ("SellingGeneralAndAdministrativeExpense",), opcional=True),
    Partida("resultado_operativo", "Resultado operativo (EBIT)", ("OperatingIncomeLoss",)),
    Partida("gasto_intereses", "Gasto por intereses", ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"),
            opcional=True),
    Partida("bai", "Beneficio antes de impuestos", (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic")),
    Partida("impuestos", "Impuesto sobre beneficios", ("IncomeTaxExpenseBenefit",)),
    Partida("beneficio_neto", "Beneficio neto atribuible", ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic",
                                                            "ProfitLoss")),
    Partida("bpa_diluido", "BPA diluido (USD)", ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted")),
    Partida("acciones_diluidas", "Acciones medias diluidas", ("WeightedAverageNumberOfDilutedSharesOutstanding",)),
    # Balance
    Partida("caja", "Caja y equivalentes", ("CashAndCashEquivalentsAtCarryingValue",
                                            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")),
    Partida("inversiones_cp", "Inversiones financieras a corto plazo", ("MarketableSecuritiesCurrent", "ShortTermInvestments",
                                                                         "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
            opcional=True),
    Partida("activo_corriente", "Activo corriente", ("AssetsCurrent",)),
    Partida("activos", "Activo total", ("Assets",)),
    Partida("pasivo_corriente", "Pasivo corriente", ("LiabilitiesCurrent",)),
    Partida("pasivos", "Pasivo total", ("Liabilities",)),
    Partida("deuda_cp", "Deuda financiera a corto plazo", ("DebtCurrent",),
            suma=(("CommercialPaper",), ("ShortTermBorrowings",), ("LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent")),
            opcional=True),
    Partida("deuda_lp", "Deuda financiera a largo plazo", ("LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"),
            opcional=True),
    Partida("patrimonio", "Patrimonio neto atribuible", ("StockholdersEquity",)),
    Partida("minoritarios", "Intereses minoritarios", ("MinorityInterest",), opcional=True),
    # Flujos de caja
    Partida("flujo_operativo", "Flujo de caja operativo", ("NetCashProvidedByUsedInOperatingActivities",
                                                          "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")),
    Partida("capex", "Inversión en inmovilizado (capex)", ("PaymentsToAcquirePropertyPlantAndEquipment",
                                                          "PaymentsToAcquireProductiveAssets")),
    Partida("amortizacion", "Amortizaciones (D&A)", ("DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
                                                    "DepreciationAndAmortization"), opcional=True),  # sin ella: aviso, EBITDA n.d.
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


class FuenteEntityFacts:
    """Histórico completo de la empresa (companyfacts de la SEC vía edgartools `Company.get_facts()`)."""

    def __init__(self, facts):
        self._facts, self._cache = facts, {}

    def fact(self, concepto: str, ejercicio: int | None):
        """FinancialFact anual de edgartools (con fiscal_year y accession); None = el último ejercicio."""
        clave = (concepto, ejercicio)
        if clave not in self._cache:
            with warnings.catch_warnings():  # edgartools avisa de cada concepto no declarado
                warnings.simplefilter("ignore")
                previo = logging.root.manager.disable
                logging.disable(logging.WARNING)
                try:
                    self._cache[clave] = self._facts.get_annual_fact(concepto, ejercicio)
                finally:
                    logging.disable(previo)
        return self._cache[clave]

    def hecho(self, concepto: str, ejercicio: int) -> float | None:
        h = self.fact(concepto, ejercicio)
        return None if h is None or getattr(h, "numeric_value", None) is None else float(h.numeric_value)

    def origen(self, concepto: str, ejercicio: int) -> str:
        return str(getattr(self.fact(concepto, ejercicio), "accession", "") or "")


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
    if componentes:
        return Dato(sum(v for _, v in componentes), " + ".join(c for c, _ in componentes), ejercicio,
                    fuente.origen(componentes[0][0], ejercicio))
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
