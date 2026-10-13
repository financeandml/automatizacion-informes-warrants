"""Pruebas contra la SEC real. Se excluyen con `pytest -m "not red"` (así corre la CI)."""

import pytest

pytestmark = pytest.mark.red


@pytest.fixture(scope="module", autouse=True)
def identidad():
    from informes_warrants.config import configurar_identidad

    configurar_identidad()


def test_cobertura_aapl_y_jpm():
    from informes_warrants.informe.cobertura import cobertura_de

    assert cobertura_de("AAPL").plantilla == "general"
    assert cobertura_de("JPM").plantilla == "banco"
    tsm = cobertura_de("TSM")
    assert tsm.validada and tsm.extranjera


@pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "TSLA"])
def test_titulos_de_riesgo_reales(ticker):
    from informes_warrants.ingesta.riesgos import riesgos_anuales

    titulos, texto, _ = riesgos_anuales(ticker)
    assert len(titulos) >= 10
    assert all(t.endswith((".", ":")) for t in titulos)


def _referencias():
    from informes_warrants.calculo.perfiles import PERFILES_SECTORIALES

    return [(p.id, t) for p in PERFILES_SECTORIALES for t in p.referencias]


@pytest.mark.parametrize("perfil_id, ticker", _referencias())
def test_perfil_sectorial_validado(perfil_id, ticker):
    from edgar import Company

    from informes_warrants.calculo.perfiles import PERFILES_SECTORIALES
    from informes_warrants.calculo.sectoriales import calcular

    perfil = next(p for p in PERFILES_SECTORIALES if p.id == perfil_id)
    r = calcular(perfil, Company(ticker).get_facts())
    assert r.completo, (ticker, r.faltan)


def test_emisor_extranjero_riesgos_y_usd():
    from edgar import Company

    from informes_warrants.ingesta.divisas import a_usd
    from informes_warrants.ingesta.riesgos import riesgos_anuales

    titulos, _, _ = riesgos_anuales("TSM")
    assert len(titulos) >= 10
    hecho = Company("TSM").get_facts().get_annual_fact("Revenue", 2024)
    usd = a_usd(hecho.numeric_value, hecho.unit, 2024).valor_usd
    assert 80e9 < usd < 100e9  # TSMC ingresó unos 90.000 M USD en 2024


def test_ltm_aapl_cuadra_con_los_10q():
    """LTM a 2026-06-27 = FY2025 + 9M FY2026 − 9M FY2025 (416.161 + 364.357 − 313.695 = 466.823 USD Mn)."""
    from datetime import date

    from edgar import Company

    from informes_warrants.calculo.calidad import revisar
    from informes_warrants.calculo.normalizador import LTM, LTM_PREVIO, FuenteLTM, normalizar

    e = normalizar(FuenteLTM(Company("AAPL").get_facts(), date(2026, 6, 27)), [LTM_PREVIO, LTM], "AAPL")
    assert e.valor("ingresos", LTM) == 466_823e6
    assert (e.valor("beneficio_neto", LTM), e.valor("resultado_operativo", LTM)) == (128_930e6, 154_859e6)
    assert (e.valor("flujo_operativo", LTM), e.valor("activos", LTM)) == (146_724e6, 383_266e6)
    assert e.valor("bpa_diluido", LTM) == pytest.approx(128_930e6 / e.valor("acciones_diluidas", LTM))
    assert e.datos["ingresos"][LTM].concepto == "RevenueFromContractWithCustomerExcludingAssessedTax"  # nunca el tag de 2018
    assert revisar(e, [LTM]).nivel == "verde"


def test_ltm_msft_suma_de_componentes():
    """MSFT declara D&A y gastos generales por componentes: el normalizador los suma (y exige todos en G&A)."""
    from datetime import date

    from edgar import Company

    from informes_warrants.calculo.normalizador import LTM, LTM_PREVIO, FuenteLTM, normalizar

    e = normalizar(FuenteLTM(Company("MSFT").get_facts(), date(2026, 6, 30)), [LTM_PREVIO, LTM], "MSFT")
    assert e.datos["amortizacion"][LTM].concepto == "Depreciation + AmortizationOfIntangibleAssets"
    assert e.datos["gastos_generales"][LTM].concepto == "SellingAndMarketingExpense + GeneralAndAdministrativeExpense"


def test_acciones_en_circulacion_desfasadas():
    """BRK-B: la portada que da edgartools es de 2011; se usa el respaldo."""
    from datetime import date

    from edgar import Company

    from informes_warrants.calculo.normalizador import acciones_en_circulacion

    valor, origen = acciones_en_circulacion(Company("BRK-B").get_facts(), date(2026, 6, 30), 2_150_000.0)
    assert valor == 2_150_000.0 and "desfasada" in origen
    valor, origen = acciones_en_circulacion(Company("AAPL").get_facts(), date(2026, 6, 27), None)
    assert valor and origen.startswith("dei:EntityCommonStockSharesOutstanding")


def test_gobierno_aapl():
    from edgar import Company

    from informes_warrants.ingesta.gobierno import gobierno

    c = Company("AAPL")
    g = gobierno(c, c.get_filings(form="10-K", amendments=False).latest().xbrl())
    assert g.auditor == "Ernst & Young LLP" and g.auditor_pcaob == 42 and g.certifica_control_interno
    assert g.pay_ratio and g.pay_ratio > 100 and g.retribucion_ceo and g.tsr


def test_comparables_por_sic():
    from edgar import Company

    from informes_warrants.ingesta.comparables import proponer

    jnj = Company("JNJ")
    lista, criterio = proponer(jnj.sic, jnj.cik, 94e9)
    assert {"ABBV", "BMY"} <= set(lista) and "JNJ" not in lista and "SIC 2834" in criterio


def test_cambios_en_los_riesgos_aapl_2025_frente_a_2024():
    """Calibración de los umbrales: 1 nuevo, 2 eliminados, 5 modificados (bien emparejados) y 21 sin cambios."""
    from edgar import Company

    from informes_warrants.ingesta.riesgos import comparar_riesgos, titulos_de_riesgo

    filings = {f.accession_no: f for f in Company("AAPL").get_filings(form="10-K", amendments=False).head(3)}
    titulos = {a: titulos_de_riesgo(f.html(), f.obj().risk_factors or "") for a, f in filings.items()
               if a in ("0000320193-25-000079", "0000320193-24-000123")}
    r = comparar_riesgos(titulos["0000320193-25-000079"], titulos["0000320193-24-000123"])
    assert (len(r["nuevos"]), len(r["eliminados"]), len(r["modificados"]), r["sin_cambios"]) == (1, 2, 5, 21)
    pares = {m["titulo"][:20]: m["anterior"][:20] for m in r["modificados"]}
    assert pares["Varied stakeholder e"] == "Expectations relatin"


def test_nflx_serie_de_acciones_coherente_tras_el_desdoblamiento():
    from edgar import Company

    from informes_warrants.calculo.normalizador import FuenteEntityFacts, normalizar

    e = normalizar(FuenteEntityFacts(Company("NFLX").get_facts()), [2024, 2025], "NFLX")
    a24, a25 = e.valor("acciones_diluidas", 2024), e.valor("acciones_diluidas", 2025)
    assert 0.9 < a25 / a24 < 1.1  # sin ajuste serían 10x
    assert e.valor("bpa_diluido", 2024) == pytest.approx(e.valor("beneficio_neto", 2024) / a24, rel=0.01)
    assert "desdoblamiento 10:1" in e.datos["acciones_diluidas"][2024].origen


def test_orcl_bai_por_componentes():
    from edgar import Company

    from informes_warrants.calculo.normalizador import FuenteEntityFacts, normalizar

    e = normalizar(FuenteEntityFacts(Company("ORCL").get_facts()), [2025], "ORCL")
    assert 2025 not in e.faltan
    assert e.datos["bai"][2025].concepto == ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic + "
                                              "IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign")


def test_trimestres_aapl_y_jnj():
    """Q4 FY2025 de AAPL (cierre 2025-09-27) = anual − nueve meses: 102.466 USD Mn; BPA derivado 1,83."""
    from datetime import date

    from edgar import Company

    from informes_warrants.calculo.normalizador import trimestres

    t = trimestres(Company("AAPL").get_facts(), date(2026, 6, 27))
    assert len(t) == 8
    q4 = next(x for x in t if x["fin"] == date(2025, 9, 27))
    assert q4["ingresos"] == 102_466e6 and q4["bpa"] == pytest.approx(1.83, abs=0.005)
    assert all(x["ebit"] is not None for x in trimestres(Company("JNJ").get_facts(), date(2026, 6, 28)))  # EBIT derivado


def test_segmentos_aapl_cinco_anios_sin_subtotales():
    from edgar import Company

    from informes_warrants.calculo.normalizador import FuenteEntityFacts, normalizar, segmentos

    empresa = Company("AAPL")
    anuales = empresa.get_filings(form="10-K", amendments=False).head(3)
    fuente = FuenteEntityFacts(empresa.get_facts())
    e = normalizar(fuente, list(range(2021, 2026)), "AAPL")
    cierres = {a: fuente.presentacion(e.datos["ingresos"][a].concepto, a)[0] for a in e.ejercicios}
    totales = {a: e.valor("ingresos", a) for a in range(2021, 2026)}
    d = segmentos([(anuales[0].xbrl(), anuales[0].accession_no), (anuales[2].xbrl(), anuales[2].accession_no)], totales, cierres)
    assert set(d) == {"negocio", "producto", "geografia"}
    assert d["producto"].ejercicios == [2021, 2022, 2023, 2024, 2025] and "Products" not in d["producto"].miembros
    for desglose in d.values():
        for a in desglose.ejercicios:
            assert sum(s[a] for s in desglose.miembros.values() if a in s) == pytest.approx(totales[a], rel=0.01)


def test_orcl_deuda_y_ltm_sin_bai_trimestral():
    """ORCL: deuda a largo como LongTermNotesAndLoans y, en los 10-Q, NotesPayableCurrent; sin BAI trimestral."""
    from datetime import date

    from edgar import Company

    from informes_warrants.calculo.normalizador import LTM, LTM_PREVIO, FuenteEntityFacts, FuenteLTM, normalizar

    facts = Company("ORCL").get_facts()
    e = normalizar(FuenteEntityFacts(facts), [2026], "ORCL")
    assert e.valor("deuda_lp", 2026) + e.valor("deuda_cp", 2026) == 129_541e6  # = DebtLongtermAndShorttermCombinedAmount
    ltm = normalizar(FuenteLTM(facts, date(2026, 8, 31)), [LTM_PREVIO, LTM], "ORCL")
    assert LTM not in ltm.faltan and ltm.datos["bai"][LTM].concepto == "NetIncomeLoss + IncomeTaxExpenseBenefit"
    assert ltm.valor("deuda_cp", LTM) == 7_625e6


def test_iova_acciones_declaradas_en_miles():
    from edgar import Company

    from informes_warrants.calculo.normalizador import FuenteEntityFacts, normalizar

    e = normalizar(FuenteEntityFacts(Company("IOVA").get_facts()), [2025], "IOVA")
    assert e.valor("acciones_diluidas", 2025) == 357_345_000.0
    assert "miles" in e.datos["acciones_diluidas"][2025].origen


def test_xom_ltm_con_acciones_basicas():
    from datetime import date

    from edgar import Company

    from informes_warrants.calculo.normalizador import LTM, LTM_PREVIO, FuenteLTM, normalizar

    e = normalizar(FuenteLTM(Company("XOM").get_facts(), date(2026, 3, 31)), [LTM_PREVIO, LTM], "XOM")
    assert LTM not in e.faltan and e.valor("acciones_diluidas", LTM) == 4_202e6


def test_gobierno_orcl_varios_primeros_ejecutivos():
    """ORCL FY2026: el proxy declara tres primeros ejecutivos (con dimensión); no se atribuye a uno solo."""
    from edgar import Company

    from informes_warrants.ingesta.gobierno import gobierno

    c = Company("ORCL")
    g = gobierno(c, c.get_filings(form="10-K", amendments=False).latest().xbrl())
    assert g.ejercicio_retribucion.startswith("2026-05-31")
    assert g.retribuciones_ceo == [627_472_419.0, 256_606_752.0, 10_141_063.0]
    aapl = gobierno(Company("AAPL"), Company("AAPL").get_filings(form="10-K", amendments=False).latest().xbrl())
    assert len(aapl.retribuciones_ceo) <= 1  # un solo primer ejecutivo: la frase de siempre
