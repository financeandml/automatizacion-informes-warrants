"""Pruebas contra la SEC real. Se excluyen con `pytest -m "not red"` (así corre la CI)."""

import pytest

pytestmark = pytest.mark.red


@pytest.fixture(scope="module", autouse=True)
def identidad():
    from informes_warrants.config import configurar_identidad

    configurar_identidad()


def test_cobertura_aapl_y_jpm():
    from informes_warrants.informe.cobertura import cobertura_de

    assert cobertura_de("AAPL").validada
    assert not cobertura_de("JPM").validada


@pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "TSLA"])
def test_titulos_de_riesgo_reales(ticker):
    from informes_warrants.ingesta.riesgos import riesgos_del_10k

    titulos, texto, _ = riesgos_del_10k(ticker)
    assert len(titulos) >= 10
    assert all(t.endswith((".", ":")) for t in titulos)
