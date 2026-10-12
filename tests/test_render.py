"""Informe completo (composición + HTML + PDF) sin conexión, con el 10-K FY2023 de Apple de referencia."""

from pathlib import Path

import pandas as pd
import pytest

from informes_warrants.calculo.calidad import revisar
from informes_warrants.calculo.normalizador import FuenteXBRL, normalizar
from informes_warrants.informe.cobertura import clasificar
from informes_warrants.informe.construir import componer
from informes_warrants.ingesta.mercado import Cotizacion

FIXTURE = Path(__file__).parent / "fixtures" / "aapl_10k_2023"


def _componer(**extra):
    from edgar.xbrl import XBRL

    estados = normalizar(FuenteXBRL(XBRL.from_directory(FIXTURE), "0000320193-23-000106"), [2022, 2023], "AAPL")
    fechas = pd.date_range("2021-01-01", "2023-12-29", freq="B")
    serie = pd.Series(range(100, 100 + len(fechas)), index=fechas, dtype=float)
    return componer(
        ticker="AAPL", empresa="Apple Inc.", sic=3571, cobertura=clasificar("Operating Company", False),
        filing={"accession": "0000320193-23-000106", "fecha": "2023-11-03", "ejercicio": 2023},
        estados=estados, calidad=revisar(estados),
        cotizacion=Cotizacion("AAPL", 190.0, "2023-12-29", 199.0, 165.0, 180.0, 1.0e10),
        acciones=15.55e9, beta_estimada=1.2,
        comportamiento={"absoluta": {"1m": 0.01, "3m": 0.02, "12m": 0.45, "3a": None, "5a": None, "ytd": 0.48}},
        series_bolsa={"AAPL": serie, "S&P 500": serie * 0.9, "XLK": serie * 1.1},
        riesgos=[{"resumen": "Dependencia de la economía global.", "cita": "The Company's operations depend on conditions.",
                  "modelo": "prueba"}],
        riesgos_lista=["The Company's operations depend on conditions."], texto_negocio="", fecha="2023-12-30", **extra,
    )


@pytest.fixture(scope="module")
def contexto():
    return _componer()


def test_contexto_coherente(contexto):
    assert contexto["calidad"].nivel == "verde"
    assert contexto["fundamentales"][2023]["fcf"] == 99584e6
    assert contexto["recomendacion"] in ("Comprar", "Mantener", "Vender")
    assert contexto["pendientes"]  # el borrador marca lo que debe completar el analista


def test_html_del_informe(contexto):
    from informes_warrants.informe import render

    html = render.html(contexto)
    for esperado in ("Apple Inc.", "383.285", "99.584", 'class="pendiente"',
                     "RevenueFromContractWithCustomerExcludingAssessedTax", "DESCARGO DE RESPONSABILIDAD", "<svg"):
        assert esperado in html, esperado
    import re

    assert not re.search(r"\b(None|nan|inf)\b", html)  # ningún hueco sin formatear


def test_precio_objetivo_del_analista(contexto):
    """El analista fija el precio objetivo: el potencial y la propuesta se recalculan; el DCF no cambia."""
    from dataclasses import replace

    from informes_warrants.informe import render

    c = _componer(estimaciones=replace(contexto["estimaciones"], precio_objetivo_analista=250.0))
    assert c["precio_objetivo"] == 250.0
    assert c["potencial"] == pytest.approx(250.0 / 190.0 - 1)
    assert c["recomendacion"] == "Comprar"
    assert c["dcf"].valor_por_accion == contexto["dcf"].valor_por_accion
    assert c["potencial_dcf"] == contexto["potencial_dcf"]
    assert "Precio objetivo (analista)" in render.html(c)
    with pytest.raises(ValueError):
        _componer(estimaciones=replace(contexto["estimaciones"], precio_objetivo_analista=-1.0))


def test_pdf_del_informe(contexto, tmp_path):
    from informes_warrants.visual.pdf import _preparar_gtk

    _preparar_gtk()
    pytest.importorskip("weasyprint", reason="Instala el extra [pdf] para generar el PDF")
    from informes_warrants.informe import render

    destino = render.pdf(contexto, tmp_path / "AAPL.pdf")
    assert destino.read_bytes().startswith(b"%PDF") and destino.with_suffix(".html").exists()


def test_comparables_automaticos_no_entran_en_el_precio(contexto):
    """Sin lista del analista, el precio objetivo es solo el DCF y el informe lo avisa."""
    from informes_warrants.informe import render

    assert not contexto["comparables_del_analista"] and contexto["valor_multiplos"] is None
    assert contexto["precio_objetivo"] == pytest.approx(contexto["valor_dcf"])
    assert any("lista de comparables" in p for p in contexto["pendientes"])
    assert "El analista debe introducir su lista de comparables" in render.html(contexto)
