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
    "precio_objetivo_dcf": 240.0, "motor_precio": 245.0, "motor_segmentos": 3, "motor_perpetuidad": 0.8,
    "motor_convencion": "mitad de año", "valor_escenarios": 240.0, "wacc_escenarios": 0.092,
    "precio_objetivo_multiplos": 260.0, "wacc": 0.09, "g": 0.025,
    "auditor": "Ernst & Young LLP",
    "hechos": [{"clave": "crecimiento", "tema": "crecimiento", "relevancia": "media", "ingresos": 416161e6, "crecimiento": 0.064}],
    "gobierno": None, "puente": {"total": 120.0, "contribuciones": {"margen bruto": 150.0, "I+D": -40.0, "otros": 10.0},
                                 "principal": "margen bruto"},
    "apalancamiento": 1.4, "uso": {"anios": 5, "retribucion": 500000e6, "retribucion_sobre_fcf": 1.02, "variacion_acciones": -0.12,
                                   "capex_sobre_da": 0.9, "fcf": 490000e6},
    "fecha_ltm": "2026-06-27", "crecimiento_ltm": 0.142, "margen_operativo_ltm": 0.33, "margen_operativo_ini": 0.30,
    "escenarios": {"Pesimista": 200.0, "Base": 240.0, "Optimista": 290.0}, "crecimiento_implicito": None, "wacc_implicito": None,
    "crecimiento_base": 0.04, "es_biotecnologia": True,
    "contribucion": {"inicio": 2024, "fin": 2025, "total": 0.064, "principal": "Services",
                     "contribuciones": {"iPhone": 0.022, "Services": 0.033, "Mac": 0.009}},
}


def test_cubre_todas_las_secciones_del_indice():
    assert {b.seccion for b in BLOQUES} == {"1", "2", "3", "4", "5", "6", "7", "8", "9", "A1", "A2", "A3", "A4", "A5", "A6", "L"}
    assert len({b.id for b in BLOQUES}) == len(BLOQUES)


def test_la_ia_se_usa_en_solo_tres_bloques():
    """Regla 7: riesgos y catalizadores (eligen y resumen) y competencia (solo traduce; decisión del 2026-10-13)."""
    assert [b.id for b in bloques_por_tipo(Tipo.IA)] == ["negocio.competencia", "riesgos.resumen", "riesgos.catalizadores"]


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
    from informes_warrants.calculo.perfiles import BANCO
    from informes_warrants.calculo.sectoriales import calcular

    facts = _Facts({"NetIncomeLoss": 10, "StockholdersEquity": 100, "Assets": 1000, "InterestIncomeExpenseNet": 30,
                    "NoninterestIncome": 20, "NoninterestExpense": 25, "Deposits": 800, "Goodwill": 20})
    r = calcular(BANCO, facts)
    assert r.completo and r.ejercicio == 2025
    assert r.metricas["eficiencia"] == 0.5 and r.metricas["rote"] == 10 / 80
    assert set(r.para_el_analista) == {"coste_riesgo", "prestamos_depositos"}  # secundarias no declaradas
    assert r.datos["patrimonio"].concepto == "StockholdersEquity" and r.datos["intangibles"].concepto is None


def test_metrica_esencial_que_falta_invalida():
    from informes_warrants.calculo.perfiles import REIT
    from informes_warrants.calculo.sectoriales import calcular

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


def test_comparar_riesgos_nuevos_eliminados_y_modificados():
    from informes_warrants.ingesta.riesgos import comparar_riesgos

    anterior = ["Investment in new business strategies and acquisitions could disrupt the Company's ongoing business.",
                "The Company's retail stores are subject to numerous risks and uncertainties.",
                "The price of the Company's stock is subject to volatility."]
    actual = ["Investment in new business strategies, commercial relationships and acquisitions could disrupt the Company's "
              "ongoing business.",
              "The price of the Company's stock is subject to volatility.",
              "Climate change and extreme weather events could disrupt the Company's supply chain."]
    r = comparar_riesgos(actual, anterior)
    assert [x["titulo"][:13] for x in r["nuevos"]] == ["Climate chang"]
    assert r["eliminados"] == [anterior[1]] and r["sin_cambios"] == 1
    assert r["modificados"][0]["anterior"] == anterior[0]  # ampliado, no nuevo


def test_gobierno_con_varios_primeros_ejecutivos():
    from dataclasses import replace

    from informes_warrants.informe.plantillas import rellenar
    from informes_warrants.informe.secciones import BLOQUES
    from informes_warrants.ingesta.gobierno import Gobierno

    bloque = next(b.id for b in BLOQUES if b.plantilla == "gobierno.md.j2")
    base = Gobierno(auditor="EY", proxy_fecha="2026-09-25", ejercicio_retribucion="2026-05-31", retribucion_ceo=627.5e6,
                    retribucion_ceo_efectiva=413e6)
    uno = rellenar(bloque, {"auditor": "EY", "gobierno": base})
    assert "el primer ejecutivo percibió 627,5 USD Mn" in uno
    varios = rellenar(bloque, {"auditor": "EY", "gobierno": replace(base, retribuciones_ceo=[627.5e6, 256.6e6, 10.1e6])})
    assert "3 primeros ejecutivos" in varios and "entre 10,1 y 627,5 USD Mn" in varios and "percibió" not in varios


def test_13g_solo_de_la_propia_empresa():
    """Las declaraciones 13D/13G en las que la empresa es la inversora (JPM declara miles) no son accionistas suyos."""
    from datetime import date, timedelta
    from types import SimpleNamespace

    from informes_warrants.ingesta.insiders import accionistas_principales

    hoy = date(2026, 10, 15)

    def declaracion(emisor, nombre, pct):
        s = SimpleNamespace(total_percent=pct, reporting_persons=[SimpleNamespace(name=nombre)], event_date="09/30/2026",
                            issuer_info=SimpleNamespace(cik=emisor))
        return SimpleNamespace(filing_date=hoy - timedelta(days=10), accession_no="x", form="SC 13G", obj=lambda: s)

    def filings(form):
        if form == "DEF 14A":
            raise ValueError("sin proxy")
        return [declaracion("0000019617", "Vanguard Capital Management", 7.1), declaracion("0000065984", "JPMORGAN CHASE & CO", 5.3)]

    r = accionistas_principales(SimpleNamespace(cik=19617, get_filings=filings), hoy)
    assert [(d["nombre"], d["porcentaje"]) for d in r["declaraciones"]] == [("Vanguard Capital Management", pytest.approx(0.071))]


def test_ficha_empleados_bolsa_y_cierre():
    """P6: empleados de la frase literal del Item 1 (la primera cifra que no es un año), cierre del ejercicio en español."""
    from datetime import date

    from informes_warrants.ingesta.ficha import cierre_fiscal, empleados

    aapl = "Human Capital\n\nAs of September 27, 2025, the Company had approximately 166,000 full-time equivalent employees. Other."
    ko = ("As of December 31, 2025 and 2024, our Company had approximately 65,900 and 69,700 employees, respectively, "
          "of which approximately 8,900 were located in the United States.")
    iova = "As of December 31, 2025, we had 975 employees, 775 of whom were engaged in research and development."
    assert [empleados(x).numero for x in (aapl, ko, iova)] == [166_000, 65_900, 975]
    assert empleados(aapl).frase.startswith("Human Capital As of September 27, 2025")
    assert empleados("We design and sell smartphones.") is None
    assert cierre_fiscal(date(2025, 9, 27)) == "27 de septiembre" and cierre_fiscal("2025-12-31") == "31 de diciembre"


def test_dividendos_del_8k_en_el_calendario():
    """P7: el dividendo declarado en el 8-K (frase literal) entra en el calendario; si ya se pagó, el siguiente estimado."""
    from datetime import date

    from informes_warrants.calculo.calendario import borrador
    from informes_warrants.ingesta.eventos import dividendos_en_texto

    texto = ("“…” Apple’s board of directors has declared a cash dividend of $0.27 per share of the Company’s common stock. "
             "The dividend is payable on August 13, 2026, to shareholders of record as of the close of business on August 10, 2026.")
    d = dividendos_en_texto(texto, date(2026, 7, 30))
    assert [(x["importe"], x["registro"], x["pago"]) for x in d] == [(0.27, date(2026, 8, 10), date(2026, 8, 13))]
    declarado = [{**d[0], "accession": "0000320193-26-000001", "presentado": date(2026, 7, 30)}]
    eventos = borrador(date(2026, 8, 1), [], [], None, None, None, None, 2025, declarado)
    assert [e["evento"] for e in eventos] == ["Fecha de registro y ex-dividendo", "Pago de dividendo de 0,27 USD por acción (declarado)"]
    assert borrador(date(2026, 10, 15), [], [], None, None, None, None, 2025, declarado) == []  # un solo pago: sin cadencia
    anterior = [{**declarado[0], "pago": date(2026, 5, 14), "registro": date(2026, 5, 11)}]
    pasado = borrador(date(2026, 10, 15), [], [], None, None, None, None, 2025, anterior + declarado)
    assert pasado[0]["fecha"] == date(2026, 11, 12) and "estimado" in pasado[0]["evento"]  # 13/08 + 91 días


def test_ratio_del_ads_del_20f():
    """P4: acciones ordinarias por ADS tal como las declara el 20-F (número en cifra o en letra)."""
    from informes_warrants.ingesta.ficha import acciones_por_ads

    assert acciones_por_ads("(each ADS represents five (5) common shares)")[0] == 5
    assert acciones_por_ads("Each ADR represents one deposited Novo Nordisk B share")[0] == 1
    assert acciones_por_ads("No depositary arrangement.") is None


def test_citas_del_mercado_en_el_10k():
    """P15: frases literales del Item 1 que cifran el mercado (en dinero o en pacientes)."""
    from informes_warrants.ingesta.ficha import citas_mercado

    texto = ("We design products. We estimate a global addressable market of more than 70,000 frontline advanced melanoma "
             "patients per year. The cloud data market is expected to reach $300 billion by 2030. Our revenue grew 29%.")
    citas = citas_mercado(texto)
    assert len(citas) == 2 and citas[0].startswith("We estimate") and citas[1].startswith("The cloud data")
