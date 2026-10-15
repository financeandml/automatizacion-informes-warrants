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
                 "caja": 100, "deuda_lp": 300, "flujo_operativo": 180, "capex": 30, "dividendos": 40,
                 "pagos_basados_acciones": 20}.items():
        e.datos[p] = {2025: Dato(v, p, 2025, "")}
    m = valoracion(e, 2025, Mercado(precio=20, acciones=100, fecha="2026-10-11"))
    assert m["capitalizacion"] == 2000 and m["ev"] == 2200
    # P/FCF sobre el FCF tras remuneración en acciones: 180 − 30 − 20 = 130
    assert (m["per"], m["ev_ebitda"], m["ev_ebit"], m["p_fcf"]) == (20, 2200 / 250, 11, 2000 / 130)
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
                       beta=1.2, coste_deuda=0.05, g=0.02, anios_convergencia=2)
    r = dcf(est, ingresos_base=1000, dfn=200, deuda=300, minoritarios=10, acciones=100, capitalizacion=1700)
    # A mano. Crecimientos: 10 %, 10 % y convergencia lineal a g: 6 %, 2 % → ventas 1100; 1210; 1282,6; 1308,252
    # FCFF = EBIT·0,8 + D&A − capex − Δventas·0,10 (EBITDA 30 %, D&A 5 %, capex 6 %):
    #   220 + 55 − 66 − 10 = 199 ; 242 + 60,5 − 72,6 − 11 = 218,9
    #   256,52 + 64,13 − 76,956 − 7,26 = 236,434 ; 261,6504 + 65,4126 − 78,49512 − 2,5652 = 246,00268
    # FCF terminal normalizado (capex de mantenimiento = min(D&A, capex) = D&A, crecido a g; circulante solo por g):
    #   327,063·0,8 + 65,4126 − 65,4126·1,02 − 1308,252·0,02·0,10 = 257,725644
    ke = 0.04 + 1.2 * 0.05
    wacc = ke * 1700 / 2000 + 0.05 * 0.8 * 300 / 2000
    flujos = [199, 218.9, 236.434, 246.00268]
    va = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(flujos))
    ev = va + 257.725644 * 1.02 / (wacc - 0.02) / (1 + wacc) ** 4
    assert r.flujos == pytest.approx(flujos)
    assert r.explicitos == 2 and r.ingresos[-1] == pytest.approx(1308.252)
    assert (r.ke, r.wacc) == (pytest.approx(ke), pytest.approx(wacc))
    assert r.ev == pytest.approx(ev) and r.valor_por_accion == pytest.approx((ev - 210) / 100)
    assert r.va_flujos == pytest.approx(va)
    assert all(w > g for w, g in r.sensibilidad)  # nunca g ≥ WACC
    assert r.sensibilidad_operativa[(0.0, 0.0)] == pytest.approx(r.valor_por_accion)


def _est_prueba(**cambios):
    from informes_warrants.informe.estimaciones import Estimaciones

    base = dict(crecimiento_ventas=[0.08] * 3, margen_ebitda=[0.30] * 3, da_sobre_ventas=0.05, capex_sobre_ventas=0.06,
                circulante_sobre_ventas=0.10, tasa_fiscal=0.20, rf=0.04, erp=0.05, beta=1.0, coste_deuda=0.05, g=0.02,
                anios_convergencia=3)
    return Estimaciones(**{**base, **cambios})


def test_escenarios_ponderados_y_editables():
    from dataclasses import replace

    from informes_warrants.calculo.dcf import dcf, valorar_escenarios
    from informes_warrants.informe.estimaciones import escenarios_por_defecto

    base = _est_prueba()
    esc = escenarios_por_defecto(base, sigma_crecimiento=0.03, sigma_margen=0.004)  # margen: se aplica el mínimo (1 pp)
    assert esc.pesimista.crecimiento_ventas == [0.05] * 3 and esc.optimista.margen_ebitda == [0.31] * 3
    kw = dict(ingresos_base=1000, dfn=200, deuda=300, minoritarios=0, acciones=100, capitalizacion=1700)
    r = valorar_escenarios(esc, **kw)
    valores = [dcf(e, **kw).valor_por_accion for e in (esc.pesimista, esc.base, esc.optimista)]
    assert valores[0] < valores[1] < valores[2]
    assert r.valor_ponderado == pytest.approx(0.25 * valores[0] + 0.5 * valores[1] + 0.25 * valores[2])
    editado = replace(esc, probabilidades=(0.0, 1.0, 0.0))  # el analista puede cambiar probabilidades y supuestos
    assert valorar_escenarios(editado, **kw).valor_ponderado == pytest.approx(valores[1])
    with pytest.raises(ValueError):
        valorar_escenarios(replace(esc, probabilidades=(0.5, 0.5, 0.5)), **kw)


def test_dcf_inverso_reproduce_el_precio():
    from informes_warrants.calculo.dcf import crecimiento_implicito, dcf, wacc_implicito

    kw = dict(ingresos_base=1000, dfn=200, deuda=300, minoritarios=0, acciones=100, capitalizacion=1700)
    base = _est_prueba()
    precio = dcf(_est_prueba(crecimiento_ventas=[0.15] * 3), **kw).valor_por_accion
    implicito = crecimiento_implicito(base, precio=precio, **kw)
    assert implicito.codigo == "resuelto" and implicito.valor == pytest.approx(0.15, abs=1e-4)
    r = dcf(base, **kw)
    w = wacc_implicito(base, kw["ingresos_base"], kw["dfn"], kw["minoritarios"], kw["acciones"], precio=r.valor_por_accion)
    assert w.codigo == "resuelto" and w.valor == pytest.approx(r.wacc, abs=1e-4)
    imposible = crecimiento_implicito(base, precio=r.valor_por_accion * 1000, **kw)
    assert imposible.codigo == "por_encima" and imposible.valor is None


def test_proyeccion_hasta_el_bpa_a_mano():
    from informes_warrants.calculo.proyeccion import proyectar

    est = _est_prueba(resultado_financiero_sobre_ventas=-0.01, cuota_minoritarios=0.05, variacion_acciones=-0.02, payout=0.4)
    a1 = proyectar(est, ingresos_base=1000, acciones_base=100)[0]
    # Ventas 1080; EBITDA 324; D&A 54; EBIT 270; financiero −10,8; BAI 259,2; impuestos 51,84; minoritarios 10,368
    assert (a1.ventas, a1.ebit, a1.bai, a1.impuestos) == pytest.approx((1080, 270, 259.2, 51.84))
    assert a1.beneficio_neto == pytest.approx(196.992) and a1.acciones == pytest.approx(98)
    assert a1.bpa == pytest.approx(196.992 / 98) and a1.dpa == pytest.approx(0.4 * 196.992 / 98)
    # FCFF = 270·0,8 + 54 − 64,8 − 8 = 197,2 ; FCF del accionista = 197,2 − 10,8·0,8 = 188,56
    assert a1.fcff == pytest.approx(197.2) and a1.fcf_accionista == pytest.approx(188.56)
    assert len(proyectar(est, 1000, 100)) == 3  # solo los años explícitos


def test_valoracion_relativa_excluye_no_significativos():
    from informes_warrants.calculo.valoracion_relativa import estadisticas, valor_implicito, valor_por_multiplos

    comps = [{"multiplos": {"ev_ebitda": v, "per": p, "ev_ventas": 2.0, "p_fcf": 20.0}}
             for v, p in ((10.0, 15.0), (12.0, 20.0), (14.0, 25.0), (80.0, -5.0), (None, 200.0))]
    s = estadisticas(comps)
    assert (s["ev_ebitda"]["mediana"], s["ev_ebitda"]["n"]) == (12.0, 3)  # 80x (> 50x) y n.d. fuera de la mediana
    assert (s["per"]["mediana"], s["per"]["n"]) == (20.0, 3)  # PER negativo y 200x (> 75x) fuera
    imp = valor_implicito(s, {"ebitda": 100.0, "beneficio_neto": 50.0, "ingresos": 500.0, "fcf_tras_sbc": 40.0},
                          dfn=200.0, minoritarios=0.0, acciones=10.0)
    assert imp["ev_ebitda"] == pytest.approx((12 * 100 - 200) / 10) and imp["per"] == pytest.approx(20 * 50 / 10)
    assert valor_por_multiplos(imp) == pytest.approx((100 + 100) / 2)
    pocos = estadisticas(comps[:2])
    assert valor_implicito(pocos, {"ebitda": 100.0, "beneficio_neto": 50.0}, 0, 0, 10)["ev_ebitda"] is None


def test_tipo_libre_riesgo_del_csv_de_fred():
    from informes_warrants.ingesta.mercado import ultimo_dgs10

    assert ultimo_dgs10("observation_date,DGS10\n2026-10-07,5.28\n2026-10-08,5.22\n2026-10-09,\n") == (pytest.approx(0.0522), "2026-10-08")


def test_beta():
    from informes_warrants.calculo.dcf import beta

    indice = [0.01, -0.02, 0.015, 0.005, -0.01] * 5
    assert beta([2 * x for x in indice], indice) == pytest.approx(2.0)


def test_etf_sectorial():
    from informes_warrants.ingesta.mercado import etf_sectorial

    casos = {3571: "XLK", 7372: "XLK", 3711: "XLY", 6021: "XLF", 2834: "XLV", 2836: "XLV", 2080: "XLP", 2911: "XLE",
             4911: "XLU", 6798: "XLRE", 4813: "XLC", 3721: "XLI", 2821: "XLB", None: "SPY", 9999: "SPY"}
    assert {s: etf_sectorial(s) for s in casos} == casos


# ---------------------------------------------------------------------------
# Partidas nuevas, puntuaciones, analítica, notas y metodología (10-K FY2023 de AAPL)
# ---------------------------------------------------------------------------
NUEVAS_GOLDEN = {  # balance publicado del 10-K FY2023 (USD mn): 2023, 2022
    "clientes": (29508, 28184), "existencias": (6331, 4946), "inmovilizado": (43715, 42117), "reservas": (-214, -3068),
}


def test_partidas_nuevas_golden(aapl):
    for partida, (v2023, v2022) in NUEVAS_GOLDEN.items():
        assert (aapl.valor(partida, 2023), aapl.valor(partida, 2022)) == (v2023 * M, v2022 * M), partida


def test_altman_a_mano(aapl):
    from informes_warrants.calculo.puntuaciones import altman

    cap = 3_000_000 * M
    p = altman(aapl, 2023, cap)
    # Rotación 383.285 / 352.583 = 1,087 > 0,5 → modelo de fabricación
    a, b, c = (143566 - 145308) / 352583, -214 / 352583, 114301 / 352583
    d, e = 3_000_000 / 290437, 383285 / 352583
    assert p.modelo == "Z (fabricación)" and p.valor == pytest.approx(1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e)
    assert p.lectura == "segura"


def test_beneish_a_mano(aapl):
    from informes_warrants.calculo.puntuaciones import beneish

    p = beneish(aapl, 2023, 2022)
    v, v0 = 383285, 394328
    dsri = (29508 / v) / (28184 / v0)
    gmi = ((v0 - 223546) / v0) / ((v - 214137) / v)
    aqi = (1 - (143566 + 43715) / 352583) / (1 - (135405 + 42117) / 352755)
    sgi = v / v0
    depi = (11104 / (11104 + 42117)) / (11519 / (11519 + 43715))
    sgai = (24932 / v) / (25094 / v0)
    lvgi = ((145308 + 95281) / 352583) / ((153982 + 98959) / 352755)
    tata = (96995 - 110543) / 352583
    m = -4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi
    assert p.valor == pytest.approx(m) and p.lectura.startswith("sin indicios")


def test_piotroski_a_mano(aapl):
    from informes_warrants.calculo.puntuaciones import piotroski

    p = piotroski(aapl, 2023, 2022)
    # Fallan: ROA creciente (27,5 % < 28,3 %) y rotación creciente (1,087 < 1,118). Pasan las otras 7.
    assert p.valor == 7 and p.detalle["ROA creciente"] is False and p.detalle["Rotación de activos creciente"] is False
    assert p.detalle["Sin dilución"] and p.detalle["Liquidez creciente"] and p.detalle["Margen bruto creciente"]


def test_puntuaciones_sin_datos_no_inventan():
    from informes_warrants.calculo.normalizador import Dato, EstadosNormalizados
    from informes_warrants.calculo.puntuaciones import altman, beneish

    e = EstadosNormalizados("X", [2025])
    e.datos["activos"] = {2025: Dato(100.0, "Assets", 2025, "")}
    assert altman(e, 2025, 50.0).valor is None and "reservas" in altman(e, 2025, 50.0).faltan
    assert beneish(e, 2025, 2024).valor is None


def test_puente_de_margen_cuadra(aapl):
    from informes_warrants.calculo.analitica import apalancamiento_operativo, puente_margen

    f22, f23 = fundamentales(aapl, 2022), fundamentales(aapl, 2023)
    gastos = {a: {"id": aapl.valor("id", a), "gastos_generales": aapl.valor("gastos_generales", a)} for a in (2022, 2023)}
    p = puente_margen(f22, f23, gastos[2022], gastos[2023])
    assert sum(p["contribuciones"].values()) == pytest.approx(p["total"])  # el puente cuadra siempre
    assert p["contribuciones"]["margen bruto"] == pytest.approx(((383285 - 214137) / 383285 - (394328 - 223546) / 394328) * 1e4)
    assert p["contribuciones"]["I+D"] == pytest.approx(-(29915 / 383285 - 26251 / 394328) * 1e4)
    assert p["principal"] == "I+D"  # la I+D (−114 pb) pesa más que la mejora del margen bruto (+82 pb)
    assert apalancamiento_operativo(f22, f23) == pytest.approx((114301 / 119437 - 1) / (383285 / 394328 - 1))


def test_notas_de_ratios():
    from informes_warrants.calculo.normalizador import Dato, EstadosNormalizados
    from informes_warrants.calculo.notas import notas_de_ratios

    e = EstadosNormalizados("X", [1])
    for p, v in {"patrimonio": 60.0, "activos": 350.0}.items():
        e.datos[p] = {1: Dato(v, p, 1, "")}
    notas = dict(notas_de_ratios({"roe": 1.5, "roic": 0.9, "dfn": -10.0, "dfn_ebitda": -0.1, "tipo_efectivo": 0.15}, e, 1,
                                 {"per": 40.0}, 500.0))
    assert "recompras" in notas["ROE"] and "ROIC" in notas and "caja neta" in notas["Deuda neta / EBITDA"]
    # con EBITDA ≤ 0 el ratio no se calcula (None) y no hay nota que explicar
    sin_ratio = dict(notas_de_ratios({"roe": 0.2, "roic": 0.1, "dfn": -10.0, "dfn_ebitda": None, "tipo_efectivo": 0.2}, e, 1,
                                     {"per": 20.0}, None))
    assert "Deuda neta / EBITDA" not in sin_ratio
    assert notas_de_ratios({"roe": 0.2, "roic": 0.1, "dfn": 5.0, "tipo_efectivo": 0.2}, e, 1, {"per": 20.0}, None) == []


def test_metodologia_cubre_las_metricas_del_informe():
    from informes_warrants.calculo.definiciones import DEFINICIONES

    terminos = " ".join(t for _, t, _ in DEFINICIONES)
    for clave in ("LTM", "EBITDA", "FCF tras SBC", "DFN", "ROE", "ROIC", "ROCE", "EV", "DCF", "WACC", "Escenarios", "DCF inverso",
                  "Comparables", "Precio objetivo", "Altman Z", "Beneish M", "Piotroski F", "factores de riesgo"):
        assert clave in terminos, clave


def test_ajuste_por_desdoblamiento():
    """Regla de edgartools: solo se ajustan los datos presentados antes del desdoblamiento (NFLX 10:1, nov. 2025)."""
    from datetime import date
    from types import SimpleNamespace

    from informes_warrants.calculo.normalizador import _ajustar_split, factor_split

    splits = [{"date": date(2015, 6, 23), "ratio": 7.0}, {"date": date(2025, 11, 14), "ratio": 10.0}]
    fy2024 = SimpleNamespace(numeric_value=439_261_000.0, period_end=date(2024, 12, 31), filing_date=date(2025, 1, 27))
    fy2025 = SimpleNamespace(numeric_value=4_343_863_000.0, period_end=date(2025, 12, 31), filing_date=date(2026, 1, 26))
    reexpresado = SimpleNamespace(numeric_value=4_392_610_000.0, period_end=date(2024, 12, 31), filing_date=date(2026, 1, 26))
    assert (factor_split(fy2024, splits), factor_split(fy2025, splits), factor_split(reexpresado, splits)) == (10.0, 1.0, 1.0)
    assert _ajustar_split("WeightedAverageNumberOfDilutedSharesOutstanding", fy2024, splits)[0] == 4_392_610_000.0
    bpa = SimpleNamespace(numeric_value=19.83, period_end=date(2024, 12, 31), filing_date=date(2025, 1, 27))
    assert _ajustar_split("EarningsPerShareDiluted", bpa, splits)[0] == pytest.approx(1.983)
    assert _ajustar_split("NetIncomeLoss", fy2024, splits)[1] == ""  # las cifras en USD no se tocan


def test_cascada_ebitda_fcf_golden(aapl):
    """AAPL FY2023: EBITDA 125.820 → impuestos 18.679 e intereses 3.803 pagados, +SBC 10.833 → flujo operativo 110.543."""
    from informes_warrants.calculo.analitica import cascada_ebitda_fcf

    pasos = cascada_ebitda_fcf(aapl, 2023, fundamentales(aapl, 2023))
    d = {n: v for n, v, _ in pasos}
    assert d["Impuestos pagados"] == -18679 * M and d["Intereses pagados"] == -3803 * M
    assert d["Flujo operativo"] == 110543 * M and d["FCF"] == 99584 * M and d["FCF tras SBC"] == (99584 - 10833) * M
    # la cascada cuadra: EBITDA + variaciones hasta el flujo operativo = flujo operativo declarado
    hasta_flujo = pasos[:[n for n, _, _ in pasos].index("Flujo operativo")]
    assert sum(v for _, v, _ in hasta_flujo) == pytest.approx(110543 * M)


def test_puente_del_margen_no_significativo_con_ventas_casi_nulas():
    from informes_warrants.calculo.analitica import puente_margen

    inicio = {"margen_operativo": -387.35, "margen_bruto": -50.0, "ingresos": 1e6}
    fin = {"margen_operativo": -0.927, "margen_bruto": 0.3, "ingresos": 325e6}
    assert puente_margen(inicio, fin, {"id": 1.0, "gastos_generales": 1.0}, {"id": 1.0, "gastos_generales": 1.0}) is None


def test_dupont_golden(aapl):
    """AAPL FY2023: BN 96.995 / ventas 383.285 · ventas / activo 352.583 · activo / patrimonio 62.146 = ROE."""
    from informes_warrants.calculo.analitica import dupont

    d = dupont(aapl, 2023)
    assert d["margen_neto"] == pytest.approx(96995 / 383285) and d["apalancamiento"] == pytest.approx(352583 / 62146)
    assert d["margen_neto"] * d["rotacion"] * d["apalancamiento"] == pytest.approx(d["roe"])
    cinco = d["carga_fiscal"] * d["carga_financiera"] * d["margen_operativo"] * d["rotacion"] * d["apalancamiento"]
    assert cinco == pytest.approx(d["roe"]) and d["roe"] == pytest.approx(96995 / 62146)


def test_participacion_institucional_13f():
    """P11: % del capital de cada tenedor del 13F y de la suma, sobre las acciones en circulación."""
    from datetime import date

    from informes_warrants.calculo.insiders import participacion_institucional

    trece_f = {"periodo": date(2026, 6, 30), "conjunto": "x", "cusips": ["191216100"], "gestoras": 2, "acciones_totales": 722.7e6,
               "filas": [{"gestora": "Berkshire Hathaway Inc", "acciones": 400e6, "valor": 32.5e9, "accession": "a", "presentado": "x"},
                         {"gestora": "BlackRock, Inc.", "acciones": 322.7e6, "valor": 26.2e9, "accession": "b", "presentado": "x"}]}
    r = participacion_institucional(trece_f, 4.3e9)
    assert [round(f["porcentaje"], 4) for f in r["filas"]] == [0.093, 0.075]
    assert r["porcentaje_total"] == pytest.approx(722.7 / 4300)
    assert participacion_institucional(None, 4.3e9) is None


def test_actividad_inusual_con_posiciones_vacias():
    """yfinance deja vacías (NaN) las posiciones abiertas de algunos strikes: cuentan como 0, sin romper el informe."""
    import math

    import pandas as pd

    from informes_warrants.calculo.derivados import actividad_inusual

    calls = pd.DataFrame({"strike": [80.0], "volume": [900.0], "openInterest": [math.nan], "lastPrice": [math.nan]})
    filas = actividad_inusual(calls, pd.DataFrame(), 81.0)
    assert filas[0]["posiciones"] == 0 and filas[0]["volumen"] == 900 and filas[0]["prima_estimada"] == 0.0


def test_ddm_por_etapas_e_ingreso_residual():
    """P19 (FinRobot adaptado): DDM de los dividendos proyectados + Gordon; ingreso residual = VC × (ROE − g)/(Ke − g)."""
    from informes_warrants.calculo.accionista import ddm_por_etapas, ingreso_residual

    r = ddm_por_etapas([1.0, 1.1], ke=0.10, g=0.02)
    esperado = 1.0 / 1.1 + 1.1 / 1.1 ** 2 + (1.1 * 1.02 / 0.08) / 1.1 ** 2
    assert r["valor"] == pytest.approx(esperado)
    assert ddm_por_etapas([0.0], 0.10, 0.02) is None and ddm_por_etapas([1.0], 0.03, 0.02) is None  # sin dividendo · Ke − g < 1,5 pp
    ri = ingreso_residual(20.0, 0.15, 0.10, 0.02)
    assert ri["valor"] == pytest.approx(20.0 * (1 + (0.15 - 0.10) / (0.10 - 0.02)))  # FinRobot: BVPS × [1 + (ROE − Ke)/(Ke − g)]
    assert ingreso_residual(-5.0, 0.15, 0.10, 0.02) is None and ingreso_residual(20.0, 0.01, 0.10, 0.02) is None
