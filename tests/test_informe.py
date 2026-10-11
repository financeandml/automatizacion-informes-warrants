from pathlib import Path

import pytest

from informes_warrants.informe.bloque_fijo import AjusteComparable, AjustesBloqueFijo, PartidaNoRecurrente, aplicar_comparables
from informes_warrants.informe.cobertura import PENDIENTE_VALIDAR, PLANTILLA_GENERAL, clasificar
from informes_warrants.informe.estimaciones import Estimaciones, recomendacion_propuesta
from informes_warrants.informe.plantillas import DIR_PLANTILLAS, _num, _var, pendientes, rellenar
from informes_warrants.informe.secciones import BLOQUES, Tipo, bloques_por_tipo

DATOS = {
    "empresa": "Apple Inc.", "ticker": "AAPL", "ejercicio": "FY2025",
    "recomendacion_propuesta": "Mantener", "precio_objetivo": 250.0, "precio": 230.5, "potencial": 0.085, "potencial_dcf": 0.041,
    "ventas": 416161.0, "crecimiento_ventas": 0.064, "margen_ebitda": 0.345, "dfn_ebitda": -0.2,
    "anio_ini": 2021, "anio_fin": 2025, "ventas_ini": 365817.0, "ventas_fin": 416161.0, "cagr_ventas": 0.033,
    "margen_ebitda_ini": 0.33, "margen_ebitda_fin": 0.345, "dfn": -30000.0,
    "ventas_est": 470000.0, "anio_fin_est": 2028, "cagr_ventas_est": 0.04, "margen_ebitda_est": 0.35,
    "riesgos": [{"resumen": "Dependencia de la economía global.", "cita": "The Company's operations depend on conditions."}],
    "cita_negocio": "The Company designs, manufactures and markets smartphones.",
    "segmentos": [{"nombre": "iPhone", "peso": 0.5}, {"nombre": "Servicios", "peso": 0.26}],
    "margen_bruto": 0.47, "margen_operativo": 0.32, "roic": 0.55, "roe": 1.5, "fcf": 98000.0, "conversion_fcf": 0.88,
    "precio_objetivo_dcf": 240.0, "precio_objetivo_multiplos": 260.0, "wacc": 0.09, "g": 0.025,
    "auditor": "Ernst & Young LLP",
}


def test_cubre_todas_las_secciones_del_indice():
    assert {b.seccion for b in BLOQUES} == {"1", "2", "3", "4", "5", "6", "7", "8", "9", "A1", "A2", "A3", "A4", "A5", "L"}
    assert len({b.id for b in BLOQUES}) == len(BLOQUES)


def test_la_ia_se_usa_en_solo_dos_bloques():
    assert [b.id for b in bloques_por_tipo(Tipo.IA)] == ["riesgos.resumen", "riesgos.catalizadores"]


def test_cada_bloque_con_plantilla_la_tiene_y_se_rellena():
    con_plantilla = [b for b in BLOQUES if b.tipo in (Tipo.PLANTILLA, Tipo.ANALISTA)]
    assert all(b.plantilla and (DIR_PLANTILLAS / b.plantilla).is_file() for b in con_plantilla)
    for b in con_plantilla:
        texto = rellenar(b.id, DATOS)
        assert texto.strip()
        assert bool(pendientes(texto)) == (b.tipo == Tipo.ANALISTA), b.id


def test_no_sobran_plantillas():
    usadas = {b.plantilla for b in BLOQUES if b.plantilla}
    assert {p.name for p in Path(DIR_PLANTILLAS).glob("*.md.j2")} == usadas


def test_un_dato_que_falta_es_un_error():
    with pytest.raises(Exception, match="is undefined"):
        rellenar("conclusiones.situacion", {"empresa": "X"})


def test_formato_numerico_espanol():
    assert _num(1234567.891) == "1.234.567,9"
    assert _num(-30000.0) == "(30.000,0)"
    assert _num(None) == "n.d."


def test_marcadores_pendientes():
    assert pendientes("Hola [[ANALISTA: escribe la tesis]] y [[ANALISTA:\notro]]") == ["escribe la tesis", "otro"]
    assert pendientes("Texto completo.") == []


def test_estimaciones_por_defecto_validas_y_errores():
    assert Estimaciones().validar() == []
    errores = Estimaciones(margen_ebitda=[0.2], g=0.5).validar()
    assert len(errores) == 2


@pytest.mark.parametrize("potencial, esperado", [(0.2, "Comprar"), (0.15, "Comprar"), (0.0, "Mantener"), (-0.1, "Vender")])
def test_recomendacion_propuesta(potencial, esperado):
    assert recomendacion_propuesta(potencial) == esperado


def test_ajustes_del_bloque_fijo():
    ajustes = [AjusteComparable("HPQ", "quitar", "Negocio distinto"), AjusteComparable("GOOGL", "añadir", "Ecosistema")]
    assert aplicar_comparables(["MSFT", "HPQ"], ajustes) == ["MSFT", "GOOGL"]
    malos = AjustesBloqueFijo([AjusteComparable("X", "cambiar", "")], [PartidaNoRecurrente("Restructuring", "FY2025", -10, " ")])
    assert len(malos.validar()) == 3


@pytest.mark.parametrize("categoria, extranjera, plantilla", [
    ("Operating Company", False, PLANTILLA_GENERAL), ("Holding Company", False, PLANTILLA_GENERAL),
    ("Investment Manager", False, PLANTILLA_GENERAL), ("Operating Company", True, PLANTILLA_GENERAL),
    ("Bank", False, "banco"), ("Insurance Company", False, "aseguradora"), ("REIT", False, "reit"),
    ("BDC", False, "inversion"), ("Closed-End Fund", False, "inversion"),
    ("SPAC", False, PENDIENTE_VALIDAR), ("ETF", False, PENDIENTE_VALIDAR), ("Unknown", False, PENDIENTE_VALIDAR),
])
def test_cobertura(categoria, extranjera, plantilla):
    c = clasificar(categoria, extranjera)
    assert c.plantilla == plantilla and c.extranjera == extranjera
    assert c.validada == (plantilla != PENDIENTE_VALIDAR)


class _Hecho:
    def __init__(self, v):
        self.numeric_value, self.fiscal_year, self.accession = v, 2025, "0000000000-25-000001"


class _Facts:
    def __init__(self, valores):
        self.valores = valores

    def get_annual_fact(self, concepto, ejercicio=None):
        return _Hecho(self.valores[concepto]) if concepto in self.valores else None


def test_metricas_de_banco_con_trazabilidad():
    from informes_warrants.calculo.sectoriales import calcular
    from informes_warrants.informe.perfiles import BANCO

    facts = _Facts({"NetIncomeLoss": 10, "StockholdersEquity": 100, "Assets": 1000, "InterestIncomeExpenseNet": 30,
                    "NoninterestIncome": 20, "NoninterestExpense": 25, "Deposits": 800, "Goodwill": 20})
    r = calcular(BANCO, facts)
    assert r.completo and r.ejercicio == 2025
    assert r.metricas["eficiencia"] == 0.5 and r.metricas["rote"] == 10 / 80
    assert set(r.para_el_analista) == {"coste_riesgo", "prestamos_depositos"}  # secundarias no declaradas
    assert r.datos["patrimonio"].concepto == "StockholdersEquity" and r.datos["intangibles"].concepto is None


def test_metrica_esencial_que_falta_invalida():
    from informes_warrants.calculo.sectoriales import calcular
    from informes_warrants.informe.perfiles import REIT

    r = calcular(REIT, _Facts({"NetIncomeLoss": 10, "StockholdersEquity": 100, "Assets": 1000}))
    assert not r.completo and "amortizacion" in r.faltan


def test_conversion_a_usd(monkeypatch):
    from informes_warrants.ingesta import divisas

    assert divisas.a_usd(5.0, "usd", 2025).valor_usd == 5.0
    monkeypatch.setattr(divisas, "tipo_medio_yfinance", lambda moneda, anio: 0.03)
    r = divisas.a_usd(100.0, "TWD", 2024)
    assert (r.valor_usd, r.tipo) == (3.0, 0.03) and "yfinance" in r.fuente


def test_variacion_con_signo_para_el_texto():
    assert (_var(-0.7253), _var(0.152), _var(0.0), _var(None)) == ("−72,5 %", "+15,2 %", "0,0 %", "n.d.")
