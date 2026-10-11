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
    from informes_warrants.informe.perfiles import PERFILES_SECTORIALES

    return [(p.id, t) for p in PERFILES_SECTORIALES for t in p.referencias]


@pytest.mark.parametrize("perfil_id, ticker", _referencias())
def test_perfil_sectorial_validado(perfil_id, ticker):
    from edgar import Company

    from informes_warrants.calculo.sectoriales import calcular
    from informes_warrants.informe.perfiles import PERFILES_SECTORIALES

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
