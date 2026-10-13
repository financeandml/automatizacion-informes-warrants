"""Perfiles sectoriales: qué métricas y qué valoración usa el informe según el tipo de empresa.

Qué resuelven los repos base y qué se construye aquí (docs/editor-y-versiones.md, «Alcance»):
  - Datos: edgartools ya extrae los estados propios de banca, seguros, inmobiliario y sociedades de
    inversión (`entity/data/industry_extensions/*.json`), fondos y BDC (`funds/`, `bdc/`) y 20-F con
    IFRS (`TwentyF`, `xbrl/currency.CurrencyConverter.to_usd`).
  - Métricas sectoriales (NIM, eficiencia, ratio combinado, FFO, P/TBV, NAV…): no existen en ningún
    repo (verificado con grep en los 9). edgar_analytics, con `is_financial=True`, solo desactiva el
    circulante y el Altman Z. Se definen aquí sobre conceptos us-gaap, con alternativas.

Métrica esencial: sin ella el perfil no vale. Secundaria: si la empresa no la declara en XBRL estándar
(p. ej., WFC no da el total de préstamos sin desglose; ALL declara sus siniestros con concepto propio),
sale «n.d.» y el informe pone un marcador para que el analista la tome del 10-K.

Cada métrica es una fórmula sobre «entradas»; cada entrada lista los conceptos XBRL que la pueden
contener (se usa el primero que la empresa declare). `opcional=True` vale 0 si no se declara.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Entrada:
    conceptos: tuple[str, ...]
    opcional: bool = False


@dataclass(frozen=True)
class Metrica:
    id: str
    nombre: str
    formula: Callable[[dict], float]
    descripcion: str
    esencial: bool = True  # sin ella el perfil no se da por validado; si no, «n.d.» + marcador para el analista


@dataclass(frozen=True)
class Perfil:
    id: str
    nombre: str
    categorias: frozenset[str]  # BusinessCategory de edgartools
    entradas: dict[str, Entrada]
    metricas: tuple[Metrica, ...]
    valoracion: str
    no_aplica: tuple[str, ...]  # bloques o métricas de la plantilla general que se sustituyen
    referencias: tuple[str, ...]  # tickers con los que se ha validado contra la SEC real (tests/test_red.py)


def _div(a: float, b: float) -> float:
    return a / b if b else float("nan")


COMUNES = {
    "beneficio": Entrada(("NetIncomeLoss", "ProfitLoss")),
    "patrimonio": Entrada(("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")),
    "activos": Entrada(("Assets",)),
}

BANCO = Perfil(
    id="banco",
    nombre="Banca",
    categorias=frozenset({"Bank", "Credit Agency"}),
    entradas={
        **COMUNES,
        "margen_intereses": Entrada(("InterestIncomeExpenseNet", "InterestIncomeExpenseAfterProvisionForLoanLoss")),
        "ingresos_no_intereses": Entrada(("NoninterestIncome",)),
        "gastos_no_intereses": Entrada(("NoninterestExpense",)),
        "provisiones": Entrada(
            (
                "ProvisionForLoanLeaseAndOtherLosses",
                "ProvisionForCreditLosses",
                "ProvisionForLoanAndLeaseLosses",
                "CreditLossExpenseReversal",
            )
        ),
        "prestamos": Entrada(
            (
                "LoansAndLeasesReceivableNetReportedAmount",
                "FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss",
                "LoansAndLeasesReceivableNetOfDeferredIncome",
            )
        ),
        "depositos": Entrada(("Deposits",)),
        "fondo_comercio": Entrada(("Goodwill",), opcional=True),
        "intangibles": Entrada(("IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet"), opcional=True),
    },
    metricas=(
        Metrica(
            "nim",
            "Margen de intereses sobre activos",
            lambda d: _div(d["margen_intereses"], d["activos"]),
            "Margen de intereses / activos totales (aproximación al NIM: la SEC no da los activos remuneradores)",
        ),
        Metrica(
            "eficiencia",
            "Ratio de eficiencia",
            lambda d: _div(d["gastos_no_intereses"], d["margen_intereses"] + d["ingresos_no_intereses"]),
            "Gastos no financieros / (margen de intereses + otros ingresos)",
        ),
        Metrica(
            "coste_riesgo", "Coste del riesgo", lambda d: _div(d["provisiones"], d["prestamos"]), "Provisiones / préstamos", esencial=False
        ),
        Metrica("prestamos_depositos", "Préstamos / depósitos", lambda d: _div(d["prestamos"], d["depositos"]), "", esencial=False),
        Metrica("roe", "ROE", lambda d: _div(d["beneficio"], d["patrimonio"]), "Beneficio neto / patrimonio"),
        Metrica("roa", "ROA", lambda d: _div(d["beneficio"], d["activos"]), "Beneficio neto / activos"),
        Metrica(
            "rote",
            "ROTE",
            lambda d: _div(d["beneficio"], d["patrimonio"] - d["fondo_comercio"] - d["intangibles"]),
            "Beneficio neto / patrimonio tangible",
        ),
        Metrica(
            "patrimonio_tangible",
            "Patrimonio tangible (USD)",
            lambda d: d["patrimonio"] - d["fondo_comercio"] - d["intangibles"],
            "Para el P/TBV",
        ),
    ),
    valoracion="P/BV y P/TBV frente a ROE/ROTE; P/BV justo = (ROE − g) / (Ke − g); PER. Sin EV, EBITDA ni DCF de FCFF.",
    no_aplica=("EBITDA", "EV y múltiplos EV", "Deuda financiera neta", "FCF y su conversión", "DCF de FCFF", "Circulante"),
    referencias=("JPM", "BAC", "WFC"),
)

ASEGURADORA = Perfil(
    id="aseguradora",
    nombre="Seguros",
    categorias=frozenset({"Insurance Company"}),
    entradas={
        **COMUNES,
        "primas": Entrada(("PremiumsEarnedNet",)),
        # BenefitsLossesAndExpenses NO vale: es el total de gastos, no los siniestros
        "siniestros": Entrada(("PolicyholderBenefitsAndClaimsIncurredNet", "IncurredClaimsPropertyCasualtyAndLiability")),
        "gastos_adquisicion": Entrada(("DeferredPolicyAcquisitionCostAmortizationExpense",), opcional=True),
        "otros_gastos_suscripcion": Entrada(
            ("OtherUnderwritingExpense", "SupplementaryInsuranceInformationOtherOperatingExpense", "OtherCostAndExpenseOperating"),
            opcional=True,
        ),
        "ingresos_inversion": Entrada(("NetInvestmentIncome",)),
    },
    metricas=(
        Metrica(
            "siniestralidad",
            "Ratio de siniestralidad",
            lambda d: _div(d["siniestros"], d["primas"]),
            "Siniestros / primas imputadas",
            esencial=False,
        ),
        Metrica(
            "gastos",
            "Ratio de gastos",
            lambda d: _div(d["gastos_adquisicion"] + d["otros_gastos_suscripcion"], d["primas"]),
            "Gastos de adquisición y suscripción / primas",
            esencial=False,
        ),
        Metrica(
            "combinado",
            "Ratio combinado",
            lambda d: _div(d["siniestros"] + d["gastos_adquisicion"] + d["otros_gastos_suscripcion"], d["primas"]),
            "Siniestralidad + gastos (< 100 % = beneficio técnico)",
            esencial=False,
        ),
        Metrica("rendimiento_inversiones", "Ingresos de inversiones / activos", lambda d: _div(d["ingresos_inversion"], d["activos"]), ""),
        Metrica("roe", "ROE", lambda d: _div(d["beneficio"], d["patrimonio"]), "Beneficio neto / patrimonio"),
    ),
    valoracion="P/BV frente a ROE y PER. Sin EV, EBITDA ni DCF de FCFF.",
    no_aplica=("EBITDA", "EV y múltiplos EV", "Deuda financiera neta", "FCF y su conversión", "DCF de FCFF", "Circulante"),
    referencias=("TRV", "ALL", "PGR"),
)

REIT = Perfil(
    id="reit",
    nombre="Inmobiliario (REIT)",
    categorias=frozenset({"REIT"}),
    entradas={
        **COMUNES,
        "amortizacion": Entrada(
            ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet")
        ),
        "ganancias_venta": Entrada(
            ("GainLossOnSaleOfRealEstateInvestmentProperty", "GainsLossesOnSalesOfInvestmentRealEstate", "GainLossOnDispositionOfAssets1"),
            opcional=True,
        ),
        "dividendos": Entrada(("PaymentsOfDividendsCommonStock", "PaymentsOfDividends", "PaymentsOfOrdinaryDividends")),
        "deuda": Entrada(("LongTermDebt", "SeniorNotes", "UnsecuredDebt", "NotesPayable", "DebtInstrumentCarryingAmount")),
    },
    metricas=(
        Metrica(
            "ffo",
            "FFO (USD)",
            lambda d: d["beneficio"] + d["amortizacion"] - d["ganancias_venta"],
            "Beneficio neto + amortizaciones − ganancias por venta de inmuebles (aproximación NAREIT)",
        ),
        Metrica(
            "payout_ffo",
            "Dividendos / FFO",
            lambda d: _div(d["dividendos"], d["beneficio"] + d["amortizacion"] - d["ganancias_venta"]),
            "",
            esencial=False,
        ),
        Metrica("ltv", "Deuda / activos (LTV)", lambda d: _div(d["deuda"], d["activos"]), ""),
        Metrica("roe", "ROE", lambda d: _div(d["beneficio"], d["patrimonio"]), "Beneficio neto / patrimonio"),
    ),
    valoracion="P/FFO, rentabilidad por dividendo y LTV. El DCF de FCFF se sustituye por P/FFO.",
    no_aplica=("PER como múltiplo principal", "DCF de FCFF", "Circulante"),
    referencias=("O", "PLD", "SPG"),
)

INVERSION = Perfil(
    id="inversion",
    nombre="BDC y fondos cerrados",
    categorias=frozenset({"BDC", "Closed-End Fund"}),
    entradas={
        **COMUNES,
        "ingreso_neto_inversion": Entrada(("NetInvestmentIncome", "InvestmentIncomeNet")),
        "nav_por_accion": Entrada(("NetAssetValuePerShare",)),
        "dividendos": Entrada(
            ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock", "DistributionMadeToLimitedPartnerCashDistributionsPaid")
        ),
        "deuda": Entrada(("LongTermDebt", "DebtInstrumentCarryingAmount", "SeniorNotes", "UnsecuredDebt")),
    },
    metricas=(
        Metrica("nav_por_accion", "NAV por acción (USD)", lambda d: d["nav_por_accion"], "Valor liquidativo por acción declarado"),
        Metrica(
            "cobertura_dividendo",
            "Cobertura del dividendo",
            lambda d: _div(d["ingreso_neto_inversion"], d["dividendos"]),
            "Ingreso neto de inversiones / dividendos pagados",
        ),
        Metrica("apalancamiento", "Deuda / patrimonio", lambda d: _div(d["deuda"], d["patrimonio"]), ""),
        Metrica(
            "rentabilidad_nii", "Ingreso neto de inversiones / patrimonio", lambda d: _div(d["ingreso_neto_inversion"], d["patrimonio"]), ""
        ),
    ),
    valoracion="P/NAV y rentabilidad por dividendo con su cobertura. Sin EV, EBITDA ni DCF.",
    no_aplica=("EBITDA", "EV y múltiplos EV", "DCF de FCFF", "Circulante", "PER"),
    referencias=("ARCC", "MAIN", "FSK"),
)

PERFILES_SECTORIALES = (BANCO, ASEGURADORA, REIT, INVERSION)


def perfil_de(categoria: str) -> Perfil | None:
    return next((p for p in PERFILES_SECTORIALES if categoria in p.categorias), None)
