"""Motor matemático contra el 10-K FY2023 de Apple (tests/fixtures/aapl_10k_2023, sin conexión).

Valores golden: AAPL_METRICS de edgartools (tests/issues/regression/test_y4yp4_metrics_render_reuse.py)
y cifras del propio 10-K. Las métricas derivadas se han calculado a mano a partir de esas cifras.
"""

from pathlib import Path

import pytest

from informes_warrants.calculo.calidad import Nivel, revisar
from informes_warrants.calculo.metricas import Mercado, cagr, fundamentales, valoracion
from informes_warrants.calculo.normalizador import FuenteXBRL, normalizar

FIXTURE = Path(__file__).parent / "fixtures" / "aapl_10k_2023"
M = 1e6

GOLDEN = {  # AAPL_METRICS de edgartools
    "ingresos": 383285000000.0, "resultado_operativo": 114301000000.0, "beneficio_neto": 96995000000.0,
    "activos": 352583000000.0, "pasivos": 290437000000.0, "patrimonio": 62146000000.0,
    "activo_corriente": 143566000000.0, "pasivo_corriente": 145308000000.0,
    "flujo_operativo": 110543000000.0, "capex": 10959000000.0,
}


@pytest.fixture(scope="module")
def aapl():
    from edgar.xbrl import XBRL

    return normalizar(FuenteXBRL(XBRL.from_directory(FIXTURE), "0000320193-23-000106"), [2022, 2023], "AAPL")


def test_partidas_golden(aapl):
    assert aapl.faltan == {}
    for partida, valor in GOLDEN.items():
        assert aapl.valor(partida, 2023) == valor, partida


def test_partidas_del_10k_y_trazabilidad(aapl):
    assert aapl.valor("deuda_cp", 2023) == (5985 + 9822) * M  # papel comercial + deuda LP con vencimiento < 1 año
    assert aapl.datos["deuda_cp"][2023].concepto == "CommercialPaper + LongTermDebtCurrent"
    assert aapl.valor("deuda_lp", 2023) == 95281 * M
    assert aapl.valor("dividendos", 2023) == 15025 * M  # edgartools lo etiqueta como DistributionsToMinorityInterests
    assert aapl.valor("bpa_diluido", 2023) == 6.13
    assert aapl.valor("ingresos", 2022) == 394328 * M
    assert aapl.datos["ingresos"][2023].concepto == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert aapl.datos["ingresos"][2023].origen == "0000320193-23-000106"
    assert "minoritarios" not in aapl.datos  # no declarada: sin dato, nunca un 0 inventado


def test_metricas_calculadas_a_mano(aapl):
    f = fundamentales(aapl, 2023)
    esperado = {
        "ebitda": 125820 * M, "fcf": 99584 * M, "dfn": 49533 * M,
        "margen_operativo": 114301 / 383285, "margen_ebitda": 125820 / 383285, "conversion_fcf": 99584 / 96995,
        "dfn_ebitda": 49533 / 125820, "tipo_efectivo": 16741 / 113736, "roe": 96995 / 62146,
        "roce": 114301 / (352583 - 145308), "roic": 114301 * (1 - 16741 / 113736) / (62146 + 49533),
        "crecimiento_ingresos": 383285 / 394328 - 1, "payout": 15025 / 96995, "liquidez": 143566 / 145308,
    }
    for clave, valor in esperado.items():
        assert f[clave] == pytest.approx(valor, rel=1e-9), clave


def test_valoracion():
    from informes_warrants.calculo.normalizador import Dato, EstadosNormalizados

    e = EstadosNormalizados("X", [2025])
    for p, v in {"ingresos": 1000, "resultado_operativo": 200, "amortizacion": 50, "beneficio_neto": 100, "patrimonio": 400,
                 "caja": 100, "deuda_lp": 300, "flujo_operativo": 180, "capex": 30, "dividendos": 40}.items():
        e.datos[p] = {2025: Dato(v, p, 2025, "")}
    m = valoracion(e, 2025, Mercado(precio=20, acciones=100, fecha="2026-10-11"))
    assert m["capitalizacion"] == 2000 and m["ev"] == 2200
    assert (m["per"], m["ev_ebitda"], m["ev_ebit"], m["p_fcf"]) == (20, 2200 / 250, 11, 2000 / 150)
    assert m["rentabilidad_dividendo"] == 0.02 and m["p_bv"] == 5


def test_cagr():
    assert cagr(100, 121, 2) == pytest.approx(0.10)
    assert cagr(None, 1, 1) is None and cagr(-1, 1, 1) is None


def test_semaforo_aapl_verde(aapl):
    assert revisar(aapl).nivel == Nivel.VERDE


def test_semaforo_rojo_si_el_balance_no_cuadra(aapl):
    import copy

    from informes_warrants.calculo.normalizador import Dato

    roto = copy.deepcopy(aapl)
    roto.datos["activos"][2023] = Dato(400000 * M, "Assets", 2023, "")
    informe = revisar(roto)
    assert informe.nivel == Nivel.ROJO and "activo" in informe.errores[0]


def test_dcf_contra_calculo_independiente():
    from informes_warrants.calculo.dcf import dcf
    from informes_warrants.informe.estimaciones import Estimaciones

    est = Estimaciones(crecimiento_ventas=[0.10, 0.10], margen_ebitda=[0.30, 0.30], da_sobre_ventas=0.05,
                       capex_sobre_ventas=0.06, circulante_sobre_ventas=0.10, tasa_fiscal=0.20, rf=0.04, erp=0.05,
                       beta=1.2, coste_deuda=0.05, g=0.02)
    r = dcf(est, ingresos_base=1000, dfn=200, deuda=300, minoritarios=10, acciones=100, capitalizacion=1700)
    # A mano: ventas 1100 y 1210; EBITDA 330 y 363; D&A 55 y 60,5; EBIT 275 y 302,5
    # FCFF = EBIT·0,8 + D&A − capex − Δventas·0,10 → 220+55−66−10 = 199 ; 242+60,5−72,6−11 = 218,9
    ke = 0.04 + 1.2 * 0.05
    wacc = ke * 1700 / 2000 + 0.05 * 0.8 * 300 / 2000
    ev = 199 / (1 + wacc) + 218.9 / (1 + wacc) ** 2 + 218.9 * 1.02 / (wacc - 0.02) / (1 + wacc) ** 2
    assert r.flujos == pytest.approx([199, 218.9])
    assert (r.ke, r.wacc) == (pytest.approx(ke), pytest.approx(wacc))
    assert r.ev == pytest.approx(ev) and r.valor_por_accion == pytest.approx((ev - 210) / 100)
    assert all(w > g for w, g in r.sensibilidad)  # nunca g ≥ WACC


def test_beta():
    from informes_warrants.calculo.dcf import beta

    indice = [0.01, -0.02, 0.015, 0.005, -0.01] * 5
    assert beta([2 * x for x in indice], indice) == pytest.approx(2.0)


def test_etf_sectorial():
    from informes_warrants.ingesta.mercado import etf_sectorial

    casos = {3571: "XLK", 7372: "XLK", 3711: "XLY", 6021: "XLF", 2834: "XLV", 2836: "XLV", 2080: "XLP", 2911: "XLE",
             4911: "XLU", 6798: "XLRE", 4813: "XLC", 3721: "XLI", 2821: "XLB", None: "SPY", 9999: "SPY"}
    assert {s: etf_sectorial(s) for s in casos} == casos
