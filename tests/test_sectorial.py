"""Plantillas sectoriales (B2) sin conexión: valoración, composición, HTML, versión, regresión e interfaz.

Banco de prueba (cifras en USD bn): beneficio 15, dividendos de las preferentes 0,5, patrimonio 110 (10 de preferentes),
fondo de comercio 20 → patrimonio tangible de los ordinarios 80 y ROTE = 14,5 / 80 = 18,125 %. 1.000 millones de acciones
a 150 USD → capitalización 150, P/TBV 1,875x. Ke = 4,5 % + 1,1 × 5,5 % = 10,55 %, g = 2,5 % → P/TBV justificado =
(18,125 − 2,5) / (10,55 − 2,5) = 1,941x → 155,28 USD. Comparables P/TBV 1,5 / 2,0 / 2,5 → mediana 2,0x → 160 USD.
"""

import re

import pandas as pd
import pytest

from informes_warrants.calculo.calidad import Informe as Calidad
from informes_warrants.calculo.valoracion_sectorial import (
    descuento_dividendos,
    multiplo_justo,
    patrimonio_comun,
    valor_por_comparables,
)
from informes_warrants.informe.cobertura import clasificar
from informes_warrants.ingesta.mercado import Cotizacion

BANCO_PRUEBA = {"NetIncomeLoss": 15e9, "StockholdersEquity": 110e9, "PreferredStockValue": 10e9,
                "PreferredStockDividendsIncomeStatementImpact": 0.5e9, "Goodwill": 20e9, "Assets": 1500e9,
                "InterestIncomeExpenseNet": 40e9, "NoninterestIncome": 30e9, "NoninterestExpense": 38.5e9,
                "ProvisionForCreditLosses": 4e9, "LoansAndLeasesReceivableNetReportedAmount": 800e9, "Deposits": 1200e9,
                "PaymentsOfDividendsCommonStock": 5e9}


class _Hecho:
    def __init__(self, v):
        self.numeric_value, self.fiscal_year, self.accession = v, 2025, "0000000000-25-000001"


class _Facts:
    def __init__(self, valores):
        self.valores = valores

    def get_annual_fact(self, concepto, ejercicio=None):
        return _Hecho(self.valores[concepto]) if concepto in self.valores else None


def _comparable(ticker, p_tbv):
    return {"ticker": ticker, "nombre": f"Banco {ticker}", "ejercicio": 2025, "metricas": {"rote": 0.15},
            "multiplos": {"capitalizacion": 100e9, "p_tbv": p_tbv, "p_bv": p_tbv * 0.8, "per": 11.0, "rentabilidad_dividendo": 0.03}}


def _datos(**extra) -> dict:
    from informes_warrants.calculo.perfiles import BANCO
    from informes_warrants.calculo.sectoriales import calcular

    r = calcular(BANCO, _Facts(BANCO_PRUEBA))
    fechas = pd.date_range("2021-01-01", "2025-12-31", freq="B")
    serie = pd.Series(range(100, 100 + len(fechas)), index=fechas, dtype=float)
    datos = dict(
        ticker="BKP", empresa="Banco de Prueba", sic=6021, cobertura=clasificar("Bank", False), perfil="banco",
        filing={"accession": "0000000000-25-000001", "fecha": "2026-02-15", "ejercicio": 2025}, historico={2024: r, 2025: r},
        ltm=None, fecha_ltm=None, calidad=Calidad(), cotizacion=Cotizacion("BKP", 150.0, "2026-10-13", 160.0, 120.0, 140.0, 5e8),
        acciones=1e9, acciones_origen="prueba", beta_estimada=1.1,
        comportamiento={"absoluta": {"1m": 0.01, "3m": 0.02, "12m": 0.2, "3a": None, "5a": None, "ytd": 0.1}},
        series_bolsa={"BKP": serie, "S&P 500": serie * 0.9, "KBE": serie * 1.1},
        riesgos=[{"resumen": "Riesgo de crédito.", "cita": "Credit risk could hurt us.", "modelo": "prueba"}],
        riesgos_lista=["Credit risk could hurt us."], texto_negocio="", competencia_texto=None, rf=None, gobierno=None,
        insiders=None, eventos=[], alarmas=[], riesgos_cambios=None, catalizadores=None, filiales=None, opciones_cadena=None,
        cortos=None, autoria=None, parametros=None, capital_flotante=None,
        comparables=[_comparable("AAA", 1.5), _comparable("BBB", 2.0), _comparable("CCC", 2.5)], comparables_criterio="lista del analista",
        comparables_del_analista=True, fecha="2026-10-14",
    )
    return {**datos, **extra}


@pytest.fixture(scope="module")
def contexto():
    from informes_warrants.informe.construir import componer

    return componer(**_datos())


def test_formulas_de_valoracion():
    assert multiplo_justo(0.15, 0.10, 0.025) == pytest.approx(0.125 / 0.075)
    assert multiplo_justo(0.02, 0.10, 0.025) is None and multiplo_justo(0.15, 0.02, 0.025) is None  # sin valor
    assert descuento_dividendos(2.0, 0.08, 0.02) == pytest.approx(2.0 * 1.02 / 0.06)
    assert descuento_dividendos(0.0, 0.08, 0.02) is None
    assert patrimonio_comun({"patrimonio": 110.0, "preferentes": 10.0}) == 100.0 and patrimonio_comun({"patrimonio": 5.0}) == 5.0
    comps = [{"multiplos": {"p_ffo": x}} for x in (10.0, 12.0, 14.0, -3.0)]
    v = valor_por_comparables("reit", comps, 2.0)
    assert (v["mediana"], v["n"], v["valor"], v["bajo"], v["alto"]) == (12.0, 3, 24.0, 22.0, 26.0)  # sin el negativo
    assert valor_por_comparables("reit", comps[:2], 2.0) is None  # menos de 3 comparables


def test_metricas_de_los_ordinarios():
    """Las preferentes y sus dividendos no cuentan para el ROE, el ROTE ni el valor contable tangible."""
    from informes_warrants.calculo.perfiles import BANCO
    from informes_warrants.calculo.sectoriales import calcular

    r = calcular(BANCO, _Facts(BANCO_PRUEBA))
    assert r.metricas["patrimonio_tangible"] == 80e9
    assert r.metricas["rote"] == pytest.approx(14.5 / 80) and r.metricas["roe"] == pytest.approx(14.5 / 100)
    assert r.metricas["eficiencia"] == pytest.approx(0.55)


def test_ffo_del_reit_como_nareit():
    """FFO = beneficio + amortizaciones + deterioros de inmuebles − ganancias por venta (O FY2025: 1.059 + 2.524 + 471 − 178)."""
    from informes_warrants.calculo.perfiles import REIT
    from informes_warrants.calculo.sectoriales import calcular

    r = calcular(REIT, _Facts({"NetIncomeLoss": 1059e6, "StockholdersEquity": 39439e6, "Assets": 72796e6,
                               "DepreciationDepletionAndAmortization": 2524e6, "ImpairmentOfRealEstate": 471e6,
                               "GainLossOnSaleOfProperties": 178e6, "PaymentsOfDividendsCommonStock": 2921e6,
                               "LongTermDebt": 25032e6}))
    assert r.metricas["ffo"] == pytest.approx(3876e6) and r.metricas["payout_ffo"] == pytest.approx(2921 / 3876)
    assert r.datos["ganancias_venta"].concepto == "GainLossOnSaleOfProperties"


def test_valoracion_del_banco(contexto):
    c = contexto
    assert c["perfil"] == "banco" and c["dcf"] is None and c["escenarios"] is None
    m = c["multiplos"]
    assert (m["p_tbv"], m["p_bv"]) == (pytest.approx(1.875), pytest.approx(1.5))
    assert m["per"] == pytest.approx(150 / 14.5) and m["rentabilidad_dividendo"] == pytest.approx(5 / 150)
    ke = 0.045 + 1.1 * 0.055
    justo = (14.5 / 80 - 0.025) / (ke - 0.025)
    metodos = {x.nombre: x for x in c["metodos"]}
    assert metodos["Valor contable justificado"].valor == pytest.approx(justo * 80)
    assert metodos["Comparables"].valor == pytest.approx(160.0)
    assert (metodos["Comparables"].bajo, metodos["Comparables"].alto) == (pytest.approx(140.0), pytest.approx(180.0))
    assert c["precio_objetivo"] == pytest.approx((justo * 80 + 160) / 2)  # pesos 50/50 por defecto
    assert c["recomendacion"] == "Mantener"  # potencial ≈ 5 %
    claves = [h["clave"] for h in c["hechos"]]
    assert "rentabilidad" in claves and "potencial" in claves


def test_rentabilidad_sostenible_del_ciclo_o_del_analista():
    """El valor contable justificado usa la media de los ejercicios (no el año pico) o la del analista."""
    from dataclasses import replace

    from informes_warrants.calculo.perfiles import BANCO
    from informes_warrants.calculo.sectoriales import calcular
    from informes_warrants.informe.construir import componer
    from informes_warrants.informe.estimaciones import Estimaciones

    pico = calcular(BANCO, _Facts({**BANCO_PRUEBA, "NetIncomeLoss": 24.5e9}))  # ROTE (24,5 − 0,5) / 80 = 30 %
    base = calcular(BANCO, _Facts(BANCO_PRUEBA))  # 18,125 %
    ke = 0.045 + 1.1 * 0.055
    c = componer(**_datos(historico={2024: base, 2025: pico}))
    vcj = c["valoracion"]["metodos"]["Valor contable justificado"]
    assert vcj["rentabilidad"] == pytest.approx((0.18125 + 0.30) / 2)  # media FY2024-FY2025, no el 30 % del último año
    assert vcj["valor"] == pytest.approx(((0.18125 + 0.30) / 2 - 0.025) / (ke - 0.025) * 80)
    assert c["valoracion"]["rentabilidad"] == pytest.approx(0.30)  # el hecho clave compara la del periodo con Ke
    assert "media FY2024-FY2025" in c["textos"]["valoracion.comentario"]
    propia = componer(**_datos(estimaciones=replace(Estimaciones(), rentabilidad_sostenible=0.12)))
    assert propia["valoracion"]["metodos"]["Valor contable justificado"]["rentabilidad"] == 0.12
    assert "del analista" in propia["textos"]["valoracion.comentario"]


def test_html_y_pdf_sectorial(contexto, tmp_path):
    from informes_warrants.informe import render

    html = render.html(contexto)
    for esperado in ("Banco de Prueba", "Valor contable justificado", "P / Valor contable tangible", "Métricas del perfil «Banca»",
                     "PreferredStockValue", "Alarmas de la SEC", "DESCARGO DE RESPONSABILIDAD", 'class="pendiente"', "<svg"):
        assert esperado in html, esperado
    for ausente in ("DCF del escenario base", "Valor de empresa, EV", "Proyección hasta el BPA"):
        assert ausente not in html, ausente
    assert not re.search(r"\b(None|nan|inf)\b", html)  # ningún hueco sin formatear
    from informes_warrants.visual.pdf import _preparar_gtk

    _preparar_gtk()
    pytest.importorskip("weasyprint", reason="Instala el extra [pdf] para generar el PDF")
    assert render.pdf(contexto, tmp_path / "BKP.pdf").read_bytes().startswith(b"%PDF")


def test_sin_lista_del_analista_los_comparables_son_orientativos():
    from informes_warrants.informe.construir import AVISO_COMPARABLES, componer

    c = componer(**_datos(comparables_del_analista=False, comparables_criterio="referencias"))
    assert c["valor_multiplos"] is None and AVISO_COMPARABLES in c["avisos_emision"]
    assert c["valoracion"]["metodos"]["Comparables"]["orientativo"]["valor"] == pytest.approx(160.0)
    assert [m.nombre for m in c["metodos"] if m.peso_efectivo] == ["Valor contable justificado"]


def test_version_regresion_e_interfaz_sectoriales(tmp_path, monkeypatch):
    import json

    from informes_warrants.almacenamiento.almacen import Almacen
    from informes_warrants.almacenamiento.versiones import Version
    from informes_warrants.informe import regresion, render, versionado
    from informes_warrants.ui import logica

    monkeypatch.setattr(render, "pdf", lambda c, destino: destino)
    almacen = Almacen(tmp_path / "v.sqlite")
    almacen.guardar(Version("BKP", 2025, "FY", 1, "0000000000-25-000001", "2026-02-15",
                            contenido={"textos": {"conclusiones.perspectivas": "Mi tesis."}, "estimaciones": {"g": 0.03}}))
    preparada, c = versionado.preparar(versionado.ultima_abierta(almacen, "BKP"), almacen, con_ia=False, carpeta=tmp_path,
                                       datos=_datos())
    assert c["estimaciones"].g == 0.03 and set(c["estimaciones"].pesos) == {"Valor contable justificado", "Comparables"}
    assert preparada.contenido["textos"]["conclusiones.perspectivas"] == "Mi tesis."
    instantanea = regresion.cifras_clave(c)
    assert instantanea["sec"]["perfil"] == "banco" and instantanea["sec"]["anuales"]["2025"]["metricas"]["patrimonio_tangible"] == 80e9
    assert json.loads(json.dumps(instantanea)) == instantanea and not regresion.comparar(instantanea, instantanea)["diferencias"]
    assert logica.escalares(c) == logica.ESCALARES_SECTORIALES
    assert logica.recomponer(_datos(), None, {}, {"probabilidades": (0.2, 0.6, 0.2)})["escenarios"] is None  # sin DCF


def test_hechos_y_definiciones_sectoriales():
    from informes_warrants.calculo.definiciones import COMUNES_SECTORIALES, DEFINICIONES
    from informes_warrants.calculo.hechos_clave import observaciones_sectoriales

    assert COMUNES_SECTORIALES <= {(g, t) for g, t, _ in DEFINICIONES}  # las reutilizadas existen en el anexo general
    obs = observaciones_sectoriales({"diferencial": -0.02, "rentabilidad": 0.08, "rentabilidad_nombre": "ROE", "ke": 0.10,
                                     "rentabilidad_dividendo": 0.06, "payout_ffo": 1.2})
    por_clave = {o["clave"]: o for o in obs}
    assert por_clave["rentabilidad"]["relevancia"] == "alta" and por_clave["dividendo"]["relevancia"] == "alta"  # no cubierto


def test_libro_del_motor_sectorial_cuadra_con_b2(contexto, tmp_path):
    """El libro sectorial (D4) reproduce con fórmulas la valoración B2 y se guarda como .xlsx sin celdas en error."""
    m = contexto["motor"]["modelo"]
    assert m.avisos == []  # ninguna discrepancia entre el libro y el cálculo del informe
    assert m.salidas["metodo_Comparables"] == pytest.approx(160.0)
    assert m.salidas["precio_modelo"] == pytest.approx(contexto["precio_objetivo"])
    from informes_warrants.calculo.motor.excel import Error

    assert not [v for v in m.valores.values() if isinstance(v, Error)]
    destino = tmp_path / "modelo.xlsx"
    m.libro.guardar(destino)
    assert destino.stat().st_size > 0


def test_indice_a_i_en_la_plantilla_sectorial(contexto):
    """B6: la plantilla sectorial sigue la misma numeración A-I que la general."""
    import re

    from informes_warrants.informe import render

    html = render.html(contexto)
    assert [int(n) for n in re.findall(r'class="apartado" id="ap-(\d+)"', html)] == list(range(2, 27))
    assert re.findall(r'<h2 id="sec-([A-I])">', html) == list("ABCDEFGHI")


def test_tesis_sectorial_atada_al_modelo(contexto):
    """P8: en el perfil sectorial, Ke, g, rentabilidad sostenible y el valor de cada método."""
    supuestos = [f["supuesto"] for f in contexto["tesis_cifras"]]
    assert "Coste del capital (Ke)" in supuestos and "Valor por valor contable justificado" in supuestos and "Precio objetivo" in supuestos
