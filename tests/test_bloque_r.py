"""Bloque R (propuestas aprobadas R2-R18): cada fórmula con valores calculados a mano, sin conexión."""

from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta

import pytest

from informes_warrants.calculo.normalizador import Dato, EstadosNormalizados


def _estados(valores: dict[str, float | tuple[float, str]], clave: int = 1) -> EstadosNormalizados:
    """Estados de prueba: partida → valor (o (valor, concepto) para la trazabilidad)."""
    e = EstadosNormalizados("X", [clave])
    for p, v in valores.items():
        valor, concepto = v if isinstance(v, tuple) else (v, p)
        e.datos[p] = {clave: Dato(valor, concepto, clave, "")}
    return e


def _est(**cambios):
    from informes_warrants.informe.estimaciones import Estimaciones

    base = dict(crecimiento_ventas=[0.08] * 3, margen_ebitda=[0.30] * 3, da_sobre_ventas=0.05, capex_sobre_ventas=0.06,
                circulante_sobre_ventas=0.10, tasa_fiscal=0.20, rf=0.04, erp=0.05, beta=1.0, coste_deuda=0.05, g=0.02,
                anios_convergencia=3)
    return Estimaciones(**{**base, **cambios})


# --- R11: múltiplos frente a su propia historia ---------------------------------------------------------------

def test_banda_historica_sin_anticipacion_y_con_acciones_de_cada_ejercicio():
    from informes_warrants.calculo.historico import Anual, banda, valor_implicito

    a1 = Anual(date(2021, 1, 10), bpa=2.0, ebitda=100.0, fcf=50.0, deuda_neta_ajustada=50.0, acciones=10.0)
    a2 = Anual(date(2022, 1, 10), bpa=4.0, ebitda=100.0, fcf=50.0, deuda_neta_ajustada=50.0, acciones=5.0)
    precios = [(date(2021, 1, 3), 100.0),  # antes del primer 10-K: sin dato, se descarta
               (date(2021, 6, 1), 40.0),   # PER 40 / 2 = 20
               (date(2022, 1, 5), 60.0),   # el 10-K de 2022 aún no se había presentado: 60 / 2 = 30 (no 60 / 4)
               (date(2022, 6, 1), 100.0)]  # 100 / 4 = 25
    b = banda("per", precios, [a2, a1])
    assert [v for _, v in b.serie] == [20.0, 30.0, 25.0] and b.n == 3
    assert b.mediana == 25.0 and b.actual == 25.0 and b.percentil_actual == pytest.approx(2 / 3)
    # EV/EBITDA con las acciones de cada ejercicio: (100·10 + 50) / 100 = 10,5 ; (100·5 + 50) / 100 = 5,5
    ev = banda("ev_ebitda", [(date(2021, 6, 1), 100.0), (date(2022, 6, 1), 100.0)], [a1, a2])
    assert [v for _, v in ev.serie] == [10.5, 5.5]
    assert valor_implicito(b, {"bpa_diluido": 3.0}, 0.0, 10.0) == 75.0  # mediana 25 × BPA LTM 3
    assert banda("per", [(date(2020, 1, 1), 10.0)], [a1]).n == 0


# --- R8: derivación del precio objetivo ------------------------------------------------------------------------

def test_sintesis_reparte_los_pesos_entre_los_metodos_con_valor():
    from informes_warrants.calculo.sintesis import Metodo, sintetizar

    metodos = [Metodo("DCF", 100.0, 80, 120, "", 0.5), Metodo("Comparables", None, None, None, "", 0.5),
               Metodo("Múltiplos históricos", 80.0, 70, 90, "", 0.0), Metodo("Suma de partes", 120.0, None, None, "", 0.5)]
    precio, salida = sintetizar(metodos)
    assert precio == pytest.approx(110.0)  # (100·0,5 + 120·0,5) / 1
    assert [m.peso_efectivo for m in salida] == [0.5, 0.0, 0.0, 0.5]
    assert sintetizar([Metodo("DCF", None, None, None, "", 1.0)])[0] is None


# --- R14: suma de partes, rango y mediana de comparables --------------------------------------------------------

def test_suma_de_partes_con_costes_no_asignados():
    from informes_warrants.calculo.valoracion_relativa import suma_de_partes

    r = suma_de_partes({"A": 100.0, "B": 50.0}, 120.0, {"A": 10.0}, 8.0, deuda_neta_ajustada=160.0, minoritarios=0.0, acciones=10.0)
    # EV = 100·10 + 50·8 + (120 − 150)·8 = 1.160 ; patrimonio = 1.160 − 160 = 1.000 ; 100 por acción
    assert r["no_asignado"] == -30.0 and r["ev"] == 1160.0 and r["por_accion"] == 100.0
    assert suma_de_partes({"A": 100.0, "B": 50.0}, None, {"A": 10.0}, None, 0.0, 0.0, 10.0) is None  # B sin múltiplo


def test_rango_y_mediana_de_comparables():
    from informes_warrants.calculo.valoracion_relativa import mediana_comparables, rango_por_multiplos

    comps = [{"multiplos": {"ev_ebitda": m, "per": m}} for m in (10.0, 20.0, 30.0)]
    bajo, alto = rango_por_multiplos(comps, {"ebitda": 100.0, "beneficio_neto": 50.0}, 0.0, 0.0, 10.0)
    # P25 = 15, P75 = 25: EV/EBITDA → 150 y 250 ; PER → 75 y 125 ; media de ambos
    assert (bajo, alto) == (pytest.approx(112.5), pytest.approx(187.5))
    con_ruido = comps + [{"multiplos": {"ev_ebitda": 60.0}}, {"multiplos": {"ev_ebitda": -5.0}}]
    assert mediana_comparables(con_ruido, "ev_ebitda", 50.0) == 20.0  # sin negativos ni > 50x
    assert mediana_comparables(comps[:2], "ev_ebitda", 50.0) is None  # menos de 3


# --- R13: componentes del EV ------------------------------------------------------------------------------------

def test_componentes_ev_y_arrendamientos_sin_doble_conteo():
    from informes_warrants.calculo.metricas import ajustes_ev, componentes_ev

    base = {"preferentes": 5.0, "pensiones": 7.0, "patrimonio_temporal": 3.0, "arrendamientos_financieros": 4.0,
            "deuda_cp": (10.0, "LongTermDebtCurrent")}
    assert ajustes_ev(_estados({**base, "deuda_lp": (100.0, "LongTermDebtNoncurrent")}), 1) == 19.0
    # la deuda ya incluye los arrendamientos financieros: no se suman otra vez
    incluida = componentes_ev(_estados({**base, "deuda_lp": (100.0, "LongTermDebtAndCapitalLeaseObligations")}), 1)
    assert incluida["Arrendamientos financieros"] == 0.0 and sum(incluida.values()) == 15.0


# --- R12: flujo de caja y balance proyectados -------------------------------------------------------------------

def test_balance_proyectado_cuadra_cada_anio():
    from informes_warrants.calculo.proyeccion import proyectar

    est = _est(sbc_sobre_ventas=0.02, recompras_sobre_fcf=0.5, payout=0.3)
    anios = proyectar(est, 1000.0, 100.0, {"caja": 200.0, "deuda": 300.0, "patrimonio": 500.0, "minoritarios": 10.0})
    for a in anios:
        assert a.caja + a.activos_operativos_netos == pytest.approx(a.deuda + a.patrimonio + a.minoritarios_balance)
        assert a.variacion_caja == pytest.approx(a.flujo_operativo - a.capex - a.dividendos - a.recompras)
        assert a.fcf_tras_sbc == pytest.approx(a.flujo_operativo - a.capex - a.sbc)
    assert anios[0].recompras == pytest.approx(0.5 * anios[0].fcf_tras_sbc)
    assert anios[0].caja == pytest.approx(200.0 + anios[0].variacion_caja)


# --- R16: cambios frente al informe anterior --------------------------------------------------------------------

def test_atribucion_secuencial_cuadra_con_el_cambio_total():
    from informes_warrants.calculo.dcf import dcf
    from informes_warrants.informe.cambios import comparar

    datos = {"ingresos_base": 1000.0, "dfn": 100.0, "deuda": 200.0, "minoritarios": 0.0, "acciones": 100.0, "capitalizacion": 2000.0}
    antes, ahora = _est(), _est(margen_ebitda=[0.32] * 3, g=0.025, beta=1.1)
    datos_antes = {**datos, "ingresos_base": 900.0}

    def resumen(est, d):
        return {"fecha": "2026-01-01", "precio_objetivo": 10.0, "estimaciones": asdict(est), "datos_dcf": d,
                "dcf_base": dcf(est, **d).valor_por_accion}

    r = comparar(resumen(antes, datos_antes), {**resumen(ahora, datos), "fecha": "2026-04-01"})
    pasos = {p["grupo"]: p["impacto"] for p in r["atribucion"]["pasos"]}
    assert sum(pasos.values()) == pytest.approx(r["atribucion"]["total"])
    assert r["atribucion"]["total"] == pytest.approx(dcf(ahora, **datos).valor_por_accion - dcf(antes, **datos_antes).valor_por_accion)
    assert pasos["Crecimiento de ventas"] == pytest.approx(0.0) and pasos["Márgenes"] > 0
    assert abs(pasos["Resto de supuestos"]) < 1e-9


# --- R17: historial de recomendación ----------------------------------------------------------------------------

def test_senal_del_historial():
    from informes_warrants.calculo.historial import historial, senal

    d0 = date(2026, 1, 1)
    assert senal(120, 100, 115, d0, date(2026, 2, 1)) == "acertada"  # a menos del 10 % del objetivo
    assert senal(120, 100, 89, d0, date(2026, 2, 1)) == "fallida"    # −11 % en contra
    assert senal(120, 100, 89, d0, date(2026, 1, 3)) == "en curso"   # periodo de gracia
    assert senal(120, 100, 105, d0, date(2026, 2, 1)) == "en curso"
    assert senal(120, 100, 105, d0, date(2027, 2, 1)) == "fallida"   # venció el horizonte de 12 meses
    filas = historial([{"fecha": "2026-03-01", "precio_objetivo": 120, "cotizacion": 100},
                       {"fecha": "2026-01-01", "precio_objetivo": 90, "cotizacion": 100}, {"fecha": "2026-02-01"}],
                      115, date(2026, 6, 1))
    assert [f["fecha"] for f in filas] == ["2026-01-01", "2026-03-01"]  # ordenadas y sin las incompletas


# --- R6: autoría ------------------------------------------------------------------------------------------------

def test_autoria_se_guarda_fuera_del_repositorio(tmp_path, monkeypatch):
    from informes_warrants.informe import autoria

    monkeypatch.setattr(autoria, "_ruta", lambda: tmp_path / "autoria.json")
    assert not autoria.cargar().rellena  # sin archivo: vacía, la portada no muestra el bloque
    autoria.guardar(autoria.Autoria(analista="Ana", correo="ana@ejemplo.com"))
    assert autoria.cargar() == autoria.Autoria(analista="Ana", correo="ana@ejemplo.com") and autoria.cargar().rellena


# --- R14 / A1: segmentos validados ------------------------------------------------------------------------------

def test_seleccion_validada_de_segmentos():
    from informes_warrants.calculo.analitica import contribucion_segmentos
    from informes_warrants.calculo.normalizador import seleccion_validada

    # AAPL: «Products» es subtotal de iPhone + Mac; la empresa declara las dos agrupaciones: gana la más detallada
    valores = {"iPhone": 50.0, "Mac": 20.0, "Services": 30.0, "Products": 70.0}
    grupos = [{"iPhone", "Mac", "Services"}, {"Products", "Services"}]
    assert seleccion_validada(valores, 100.0, grupos) == {"iPhone": 50.0, "Mac": 20.0, "Services": 30.0}
    # dos agrupaciones distintas igual de detalladas que cuadran: ambiguo, no se publica
    assert seleccion_validada({"A": 50.0, "B": 50.0, "C": 50.0, "D": 50.0}, 100.0, [{"A", "B"}, {"C", "D"}]) is None
    assert seleccion_validada({"A": 50.0, "B": 40.0}, 100.0, []) is None  # no suman el total
    c = contribucion_segmentos({"A": {1: 60.0, 2: 66.0}, "B": {1: 40.0, 2: 44.0}}, 1, 2)
    assert c["contribuciones"] == {"A": pytest.approx(0.06), "B": pytest.approx(0.04)} and c["principal"] == "A"
    assert contribucion_segmentos({"A": {1: 60.0, 2: 66.0}, "B": {1: 40.0}, "C": {2: 44.0}}, 1, 2) is None


# --- R2: autonomía de caja --------------------------------------------------------------------------------------

def test_autonomia_de_caja():
    from informes_warrants.calculo.analitica import autonomia_de_caja

    e = _estados({"caja": 100.0, "inversiones_cp": 20.0, "acciones_diluidas": 121.0})
    a = autonomia_de_caja({"fcf": -120.0}, e, 1, acciones_inicio=100.0, anios=2)
    assert a["meses"] == pytest.approx(12.0) and a["dilucion_anual"] == pytest.approx(0.10)  # (121 / 100)^(1/2) − 1
    assert autonomia_de_caja({"fcf": 10.0}, e, 1, 100.0, 2) is None  # genera caja: no aplica


def test_es_biotecnologia():
    from informes_warrants.informe.cobertura import es_biotecnologia

    assert es_biotecnologia(2836) and es_biotecnologia("8731")
    assert not es_biotecnologia(3571) and not es_biotecnologia(None)


# --- Normalizador: errores reales de etiquetado detectados al integrar ------------------------------------------

@dataclass(frozen=True)
class _Hecho:
    concept: str
    numeric_value: float
    value: float
    period_start: date | None
    period_end: date
    accession: str


class _Facts:
    def __init__(self, hechos):
        self.hechos = hechos

    def get_all_facts(self):
        return self.hechos


def test_acciones_declaradas_en_miles_se_corrigen():
    from informes_warrants.calculo.normalizador import corregir_escala, escalas_acciones

    ini, fin = date(2025, 4, 1), date(2025, 6, 30)

    def hechos(acc, acciones):
        return [_Hecho("us-gaap:NetIncomeLoss", -110e6, -110e6, ini, fin, acc),
                _Hecho("us-gaap:EarningsPerShareDiluted", -0.33, -0.33, ini, fin, acc),
                _Hecho("us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", acciones, acciones, ini, fin, acc)]

    # IOVA: 334.511 «acciones» con BN −110 M y BPA −0,33 → BN / BPA = 333 M: declaradas en miles
    facts = _Facts(hechos("en-miles", 334_511.0) + hechos("correcto", 334_511_000.0))
    escalas = escalas_acciones(facts)
    assert escalas == {"en-miles": 1000.0}
    corregidos = {(h.accession, h.concept): h.numeric_value for h in corregir_escala(facts.get_all_facts(), escalas)}
    assert corregidos[("en-miles", "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding")] == 334_511_000.0
    assert corregidos[("en-miles", "us-gaap:NetIncomeLoss")] == -110e6  # solo las acciones
    assert corregidos[("correcto", "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding")] == 334_511_000.0


class _Fuente:
    def __init__(self, hechos):
        self.hechos = hechos

    def hecho(self, concepto, ejercicio):
        return self.hechos.get(concepto)

    def origen(self, concepto, ejercicio):
        return "prueba"


def test_derivadas_cuando_la_suma_esta_incompleta():
    from informes_warrants.calculo.normalizador import POR_ID, _resolver

    # ORCL en los 10-Q: solo un componente del BAI (EEUU) → no vale la suma parcial; BAI = BN + impuesto
    fuente = _Fuente({"IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic": 50.0, "NetIncomeLoss": 80.0,
                      "IncomeTaxExpenseBenefit": 20.0})
    d = _resolver(fuente, POR_ID["bai"], 2026)
    assert d.valor == 100.0 and d.concepto == "NetIncomeLoss + IncomeTaxExpenseBenefit"
    # deuda a largo plazo: total − parte corriente (la corriente ya está en la deuda a corto)
    d = _resolver(_Fuente({"LongTermDebt": 100.0, "LongTermDebtCurrent": 10.0}), POR_ID["deuda_lp"], 2026)
    assert d.valor == 90.0
    assert _resolver(_Fuente({"LongTermNotesAndLoans": 122.0}), POR_ID["deuda_lp"], 2026).valor == 122.0


def test_aviso_de_deuda_posiblemente_incompleta():
    from informes_warrants.calculo.calidad import revisar

    def avisos(deuda):
        return [a for a in revisar(_estados({"gasto_intereses": 50.0, "deuda_lp": deuda})).avisos if "falta deuda" in a]

    assert avisos(100.0)  # 50 % de tipo implícito: casi seguro falta deuda
    assert not avisos(1000.0)


def test_ratios_de_estimaciones_como_suma_de_sumas():
    from informes_warrants.calculo.metricas import ratio_de_sumas

    assert ratio_de_sumas([(10.0, 1.0), (20.0, 200.0)]) == pytest.approx(30 / 201)  # no la media de 10 y 0,1
    assert ratio_de_sumas([]) is None and ratio_de_sumas([(1.0, 0.0)]) is None


def test_estimaciones_editables_del_bloque_r():
    est = _est(sbc_sobre_ventas=0.05, recompras_sobre_fcf=0.8)
    assert est.validar() == []
    assert replace(est, sbc_sobre_ventas=1.5).validar() and replace(est, multiplos_sotp={"A": -1.0}).validar()


# --- A14: batería de regresión --------------------------------------------------------------------------------

def test_regresion_compara_solo_cifras_de_la_sec(tmp_path):
    from informes_warrants.informe import regresion

    base = {"ticker": "X", "origen": {"filing": "a", "ultimo_periodico": "q1"},
            "sec": {"ltm": {"ingresos": 100.0, "bpa": 1.5}, "segmentos": {"geografia": {"ejercicios": [2024, 2025]}}},
            "mercado_referencia": {"cotizacion": 10.0}}
    regresion.guardar(base, tmp_path)
    assert regresion.cargar("x", tmp_path) == base and regresion.cargar("Y", tmp_path) is None
    mercado = {**base, "mercado_referencia": {"cotizacion": 12.0}}
    assert regresion.comparar(base, mercado)["diferencias"] == []  # la cotización no se compara
    cambio = {**base, "sec": {**base["sec"], "ltm": {"ingresos": 101.0, "bpa": 1.5}}}
    r = regresion.comparar(base, cambio)
    assert r["diferencias"] == ["ltm.ingresos: 100.0 → 101.0"] and not r["nuevo_filing"]
    assert regresion.comparar(base, {**cambio, "origen": {"filing": "a", "ultimo_periodico": "q2"}})["nuevo_filing"]


def test_aviso_de_posible_doble_conteo_en_la_deuda_a_corto():
    from informes_warrants.calculo.calidad import revisar

    def avisos(concepto):
        return [a for a in revisar(_estados({"deuda_cp": (10.0, concepto)})).avisos if "papel comercial" in a]

    assert avisos("CommercialPaper + ShortTermBorrowings + LongTermDebtCurrent")
    assert not avisos("CommercialPaper + LongTermDebtCurrent")


# --- A1-bis (F7): LTM provisional por segmento -------------------------------------------------------------------

def test_segmentos_ltm_provisional(monkeypatch):
    from informes_warrants.calculo import normalizador as n

    fin_fy, fecha_ltm = date(2025, 9, 27), date(2026, 6, 27)
    ini = fin_fy + timedelta(days=1)
    ini_ant = ini - timedelta(days=364)
    fin_ant = fecha_ltm - timedelta(days=364)
    hechos = [{"miembro": "x:AMember", "etiqueta": "A", "inicio": ini, "fin": fecha_ltm, "valor": 20.0},
              {"miembro": "x:BMember", "etiqueta": "B", "inicio": ini, "fin": fecha_ltm, "valor": 10.0},
              {"miembro": "x:AMember", "etiqueta": "A", "inicio": ini_ant, "fin": fin_ant, "valor": 15.0},
              {"miembro": "x:BMember", "etiqueta": "B", "inicio": ini_ant, "fin": fin_ant, "valor": 12.0}]
    monkeypatch.setattr(n, "_hechos_eje", lambda *a, **k: hechos)

    def desglose():
        return {"producto": n.Desglose("producto", "Revenues", {"A": {2025: 60.0}, "B": {2025: 40.0}}, ejercicios=[2025])}

    d = desglose()
    n.segmentos_ltm(d, None, "q", 2025, fin_fy, fecha_ltm, 103.0)
    assert d["producto"].ltm == {"A": 65.0, "B": 38.0} and d["producto"].ltm_origen == "q"  # 60 + 20 − 15 ; 40 + 10 − 12
    d = desglose()
    n.segmentos_ltm(d, None, "q", 2025, fin_fy, fecha_ltm, 120.0)  # no cuadra con el total LTM: no se publica
    assert not d["producto"].ltm and "no cuadra" in d["producto"].ltm_motivo
    monkeypatch.setattr(n, "_hechos_eje", lambda *a, **k: hechos[:3])
    d = desglose()
    n.segmentos_ltm(d, None, "q", 2025, fin_fy, fecha_ltm, 103.0)
    assert not d["producto"].ltm and "B" in d["producto"].ltm_motivo


# --- A15: pulido ------------------------------------------------------------------------------------------------

def test_nombre_legible_de_la_sec():
    from informes_warrants.ingesta.nombres import nombre_legible

    casos = {"IOVANCE BIOTHERAPEUTICS, INC.": "Iovance Biotherapeutics, Inc.", "AT&T INC.": "AT&T Inc.", "HP INC": "HP Inc",
             "3M CO": "3M Co", "BANK OF AMERICA CORP /DE/": "Bank of America Corp", "Apple Inc.": "Apple Inc.",
             "RIVIAN AUTOMOTIVE, INC. / DE": "Rivian Automotive, Inc.", "THE WALT DISNEY CO": "The Walt Disney Co",
             "IBM": "IBM", "COCA-COLA CO": "Coca-Cola Co"}
    for sec, informe in casos.items():
        assert nombre_legible(sec) == informe, sec


# --- A3: concentración de clientes -------------------------------------------------------------------------------

class _Consulta:
    def __init__(self, df):
        self.df = df

    def by_concept(self, *_):
        return self

    def by_dimension(self, *_):
        return self

    def to_dataframe(self):
        return self.df


class _XBRL:
    def __init__(self, df):
        self.facts = type("F", (), {"query": lambda _self: _Consulta(df)})()


def test_concentracion_de_clientes():
    import pandas as pd

    from informes_warrants.calculo.normalizador import concentracion_clientes

    def fila(cliente, base, tipo, valor, fin="2025-12-31", extra=None):
        return {"dim_srt_MajorCustomersAxis": f"x:{cliente}Member", "dim_us-gaap_ConcentrationRiskByBenchmarkAxis": f"us-gaap:{base}",
                "dim_us-gaap_ConcentrationRiskByTypeAxis": f"us-gaap:{tipo}", "dim_srt_StatementGeographicalAxis": extra,
                "dimension_member_label": None, "period_end": fin, "numeric_value": valor}

    df = pd.DataFrame([
        fila("CustomerA", "RevenueFromContractWithCustomerMember", "CustomerConcentrationRiskMember", 0.17),
        fila("CustomerA", "RevenueFromContractWithCustomerMember", "CustomerConcentrationRiskMember", 0.12, "2024-12-31"),
        fila("OtherCustomers", "RevenueFromContractWithCustomerMember", "CustomerConcentrationRiskMember", 0.83),  # residuo
        fila("VendorOne", "NonTradeReceivableMember", "CreditConcentrationRiskMember", 0.46),  # proveedor: otra base
        fila("CustomerB", "TradeAccountsReceivableMember", "CreditConcentrationRiskMember", 0.30, extra="country:TW"),
    ])
    filas = concentracion_clientes(_XBRL(df), {2025: date(2025, 12, 31), 2024: date(2024, 12, 31)})
    assert [(f["cliente"], f["base"], f["detalle"], f["valores"]) for f in filas] == [
        ("Customer A", "Ingresos", "", {2025: 0.17, 2024: 0.12}),
        ("Customer B", "Cuentas a cobrar", "Taiwán", {2025: 0.30}),
    ]
    assert concentracion_clientes(_XBRL(pd.DataFrame()), {}) == []


# --- A9: vencimientos de la deuda --------------------------------------------------------------------------------

def test_vencimientos_solo_si_cuadran_con_la_deuda():
    from informes_warrants.calculo.normalizador import VENCIMIENTOS, vencimientos_deuda

    def fuente(importes, **otros):
        return _Fuente({**dict(zip(VENCIMIENTOS, importes, strict=True)), **otros})

    ok = vencimientos_deuda(fuente([10.0, 20.0, None, 5.0, 5.0, 60.0], DebtInstrumentCarryingAmount=100.0), 2025)
    assert ok["importes"][2] is None and ok["suma"] == 100.0 and ok["referencia"] == "DebtInstrumentCarryingAmount"
    mal = vencimientos_deuda(fuente([10.0, 20.0, 0.0, 5.0, 5.0, 40.0], LongTermDebt=100.0), 2025)
    assert mal["importes"] == [] and "no cuadran" in mal["motivo"]
    assert vencimientos_deuda(fuente([None] * 6), 2025)["importes"] == []


# --- A6: insiders --------------------------------------------------------------------------------------------------

def test_actividad_de_insiders_y_compras_agrupadas():
    from informes_warrants.calculo.insiders import actividad

    def op(dia, nombre, tipo, acciones, precio, plan=False):
        return {"fecha": date(2026, 3, dia), "nombre": nombre, "tipo": tipo, "acciones": acciones, "precio": precio,
                "importe": acciones * precio, "plan_10b5_1": plan}

    a = actividad([op(1, "Ana", "Compra", 100, 10.0), op(10, "Luis", "Compra", 50, 12.0), op(20, "Ana", "Venta", 30, 15.0, plan=True)])
    assert (a["compras"], a["importe_compras"], a["ventas"], a["importe_ventas"]) == (2, 1600.0, 1, 450.0)
    assert a["saldo"] == 1150.0 and a["ventas_con_plan"] == 1 and a["insiders"] == 2
    assert a["agrupadas"]["compradores"] == ["Ana", "Luis"]  # dos insiders distintos en 14 días
    separadas = actividad([op(1, "Ana", "Compra", 100, 10.0), op(25, "Luis", "Compra", 50, 12.0)])
    assert separadas["agrupadas"] is None
    assert actividad([])["saldo"] == 0


# --- A8: historial de resultados y alarmas -----------------------------------------------------------------------

def test_reaccion_a_5_sesiones_segun_la_hora_de_presentacion():
    import pandas as pd

    from informes_warrants.calculo.analitica import reaccion_resultados

    idx = pd.bdate_range("2026-07-27", "2026-08-10", tz="America/New_York")
    cierres = pd.Series(range(100, 100 + len(idx)), index=idx, dtype=float)
    tras_cierre = reaccion_resultados("2026-07-30 20:31:00+00:00", cierres)  # 16:31 en Nueva York: cotiza el viernes
    assert tras_cierre["primera_sesion"] == date(2026, 7, 31) and tras_cierre["reaccion"] == pytest.approx(108 / 103 - 1)
    antes = reaccion_resultados("2026-07-30 12:00:00+00:00", cierres)  # 08:00: cotiza ese mismo día
    assert antes["primera_sesion"] == date(2026, 7, 30) and antes["reaccion"] == pytest.approx(107 / 102 - 1)
    assert reaccion_resultados("2026-08-07 12:00:00+00:00", cierres) is None  # aún no hay 5 sesiones


def test_alarmas_solo_con_frases_afirmativas():
    from informes_warrants.ingesta.eventos import CONTINUIDAD, CONTROL_NO_EFICAZ, _frases

    texto = ("We could identify a material weakness in the future. Management concluded that our internal control over "
             "financial reporting was not effective as of December 31, 2025. Factors raise substantial doubt about our "
             "ability to continue as a going concern. If we fail to raise capital, there may be substantial doubt about "
             "our ability to continue as a going concern.")
    assert _frases(texto, CONTROL_NO_EFICAZ) == ["Management concluded that our internal control over financial reporting "
                                                 "was not effective as of December 31, 2025."]
    assert _frases(texto, CONTINUIDAD) == ["Factors raise substantial doubt about our ability to continue as a going concern."]
    favorable = ("Based upon its assessment, management has concluded that the Company's internal control over financial "
                 "reporting was effective at December 31, 2025, and that there were no material weaknesses in the Company's "
                 "internal control over financial reporting as of that date. We did not identify any material weaknesses that "
                 "remain unremediated.")  # TRV FY2025: falso positivo corregido
    assert _frases(favorable, CONTROL_NO_EFICAZ) == []


# --- A5: competencia ---------------------------------------------------------------------------------------------

def test_apartado_competition_literal():
    from informes_warrants.ingesta.competencia import apartado_competencia

    item1 = ("Products\n\nThe Company sells phones.\n\nCompetition\n\nThe markets are highly competitive.\n\n"
             "Apple Inc. | 2025 Form 10-K | 2\n\nThe Company competes on price and\n\nquality of its products.\n\n"
             "Supply of Components\n\nComponents are generally available.")
    r = apartado_competencia(item1)
    assert r["texto"] == "The markets are highly competitive.\n\nThe Company competes on price and quality of its products."
    tsla = ("Competition\n\nAutomotive\n\nThe automotive market is highly competitive.\n\nEnergy Storage\n\n"
            "The energy storage market is competitive too.\n\nIntellectual Property\n\nWe hold patents.")
    assert apartado_competencia(tsla)["texto"] == ("**Automotive.**\n\nThe automotive market is highly competitive.\n\n"
                                                   "**Energy Storage.**\n\nThe energy storage market is competitive too.")
    assert apartado_competencia("Products\n\nWe sell oil.") is None


def test_verificacion_de_la_traduccion():
    from informes_warrants.ia.bloques import verificar_traduccion

    original = "LinkedIn competes with AbelZeta Pharma. In 2025 revenue was $1,234.5 million, up 12%."
    buena = "LinkedIn compite con AbelZeta Pharma. En 2025 los ingresos fueron de 1.234,5 millones de USD, un 12 % más."
    assert verificar_traduccion(original, buena) == ""
    assert "cifras" in verificar_traduccion(original, buena.replace("12 %", "13 %"))
    assert "nombres propios" in verificar_traduccion(original, buena.replace("AbelZeta", "Abelzeta"))
    assert "longitud" in verificar_traduccion(original, "LinkedIn y AbelZeta: 2025, 1.234,5, 12.")


def test_cuotas_y_estabilidad_del_margen():
    from informes_warrants.calculo.analitica import cuotas_de_ingresos, estabilidad_margen

    assert cuotas_de_ingresos({"A": 60.0, "B": 30.0, "C": 10.0, "D": None}) == {"A": 0.6, "B": 0.3, "C": 0.1}
    assert cuotas_de_ingresos({"A": 60.0}) == {}  # sin comparables no hay cuota
    assert estabilidad_margen([0.30, 0.32, 0.28, None]) == pytest.approx(0.016329931618554522)
    assert estabilidad_margen([0.30, 0.32]) is None


# --- A4: calendario de catalizadores --------------------------------------------------------------------------------

def test_calendario_siempre_posterior_a_la_emision():
    from informes_warrants.calculo.calendario import borrador, plazo_siguiente_informe, proxima_por_aniversario

    hoy = date(2026, 10, 13)
    resultados = [date(2025, 7, 31), date(2025, 10, 30), date(2026, 1, 29), date(2026, 4, 30), date(2026, 7, 30)]
    assert proxima_por_aniversario(resultados[-4:], hoy) == date(2026, 10, 29)  # 30/10/2025 + 52 semanas
    assert proxima_por_aniversario([date(2024, 2, 28)], hoy) == date(2027, 2, 24)  # + 3 × 52 semanas: las anteriores ya pasaron
    assert proxima_por_aniversario([], hoy) is None
    # AAPL: último trimestre cerrado el 27/06/2026; el siguiente cierre es el del ejercicio → 10-K a 60 días
    plazo = plazo_siguiente_informe(date(2026, 6, 27), date(2025, 9, 27), "Large Accelerated Filer", hoy)
    assert plazo["formulario"] == "10-K" and plazo["limite"] == date(2026, 9, 26) + timedelta(days=60)
    eventos = borrador(hoy, resultados, [date(2026, 2, 24)], date(2026, 6, 27), date(2025, 9, 27), "Large Accelerated Filer",
                       12_393e6, 2025)
    assert [e["evento"] for e in eventos] == ["Próximos resultados (estimado)", "Junta anual de accionistas (estimada)",
                                             "Vencimientos de deuda de FY26: 12.393 USD mn"]
    assert all(e["fecha"] is None or e["fecha"] > hoy for e in eventos)


def test_hechos_relevantes_del_8k():
    from informes_warrants.ingesta.eventos import hechos_relevantes

    eventos = [{"fecha": date(2026, 9, 1), "items": ["5.02"], "accession": "a"},
               {"fecha": date(2026, 7, 30), "items": ["2.02", "9.01"], "accession": "b"},
               {"fecha": date(2025, 1, 1), "items": ["1.01"], "accession": "c"}]
    assert hechos_relevantes(eventos, date(2026, 10, 13)) == [
        {"fecha": date(2026, 9, 1), "hechos": ["Cambios en el consejo o la alta dirección"], "accession": "a"}]


# --- A2: hechos clave ----------------------------------------------------------------------------------------------

def test_hechos_clave_por_reglas_uno_por_tema():
    from informes_warrants.calculo.hechos_clave import observaciones, seleccionar

    entradas = {"ingresos": 400e9, "crecimiento": 0.06, "variacion_margen_pb": 339, "margen_inicio": 0.298, "margen_fin": 0.332,
                "anio_inicio": 2021, "principal": "margen bruto", "roic": 0.95, "wacc": 0.11, "roic_menos_wacc": 0.84,
                "dfn": 21e9, "dfn_ebitda": 0.13, "potencial": -0.52, "precio_objetivo": 162.6, "recomendacion": "Vender",
                "percentil": 1.0, "metrica_historica": "EV / EBITDA", "multiplo_actual": 35.7, "multiplo_mediana": 25.3,
                "alarmas": [], "puntuaciones": {"Altman Z": "segura", "Beneish M": "sin indicios (M ≤ −1,78)"}}
    hechos = seleccionar(observaciones(entradas))
    assert len(hechos) == 4 and [h["tema"] for h in hechos] == ["crecimiento", "rentabilidad", "balance", "valoracion"]
    assert next(h for h in hechos if h["tema"] == "rentabilidad")["clave"] == "margen"  # 339 pb: alta (ROIC − WACC: media)
    # una alarma de la SEC es crítica y entra siempre, desplazando al tema menos relevante
    con_alarma = seleccionar(observaciones({**entradas, "alarmas": [{"tipo": "Cambio de auditor", "fecha": date(2026, 1, 5)}]}))
    assert [h["clave"] for h in con_alarma] == ["crecimiento", "margen", "potencial", "alarma"]  # sale el balance (0,13x: baja)
    assert seleccionar(observaciones({})) == []


def test_plazo_con_cierre_fiscal_el_29_de_febrero():
    from informes_warrants.calculo.calendario import plazo_siguiente_informe

    plazo = plazo_siguiente_informe(date(2026, 8, 29), date(2024, 2, 29), "Accelerated Filer", date(2026, 10, 13))
    assert plazo["formulario"] == "10-Q" and plazo["limite"] > date(2026, 10, 13)


# --- Borradores de la IA en los apartados del analista (2026-10-14) ------------------------------------------------

def test_borrador_de_la_ia_sin_cifras_nuevas():
    from informes_warrants.ia.borradores import verificar_borrador

    contexto = "Ingresos LTM de 466.823 USD Mn (+14,2 % interanual). Margen EBITDA del 36,0 %."
    assert verificar_borrador("La compañía crece un 14,2 % con un margen EBITDA del 36,0 %, lo que sostiene la tesis.", contexto) == ""
    assert "cifras" in verificar_borrador("Crecerá un 20 % en 2027.", contexto)  # cifras que no están en el informe
    assert verificar_borrador("SIN DATOS", contexto) == "el contexto no basta"
    assert verificar_borrador("Texto [[ANALISTA: x]]", contexto) == "formato no válido"


def test_generar_borradores_con_modelo_simulado(monkeypatch):
    from informes_warrants.ia import borradores

    llamadas = []

    def completar(sistema, usuario, cfg=None):
        llamadas.append(usuario)
        if "titular" in usuario:
            return "### 1\nCrecimiento del 14,2 % con caja neta.\n### 2\nSIN DATOS\n**### 3**\nInventa un 99 %.", cfg
        return "\n".join(f"### {n}\nCrece con caja neta." for n in range(1, 7)), cfg

    monkeypatch.setattr(borradores, "completar", completar)
    r = borradores.generar(["titular de la tesis", "tamaño del mercado", "composición del consejo"], "Crece un 14,2 %.")
    assert r == {"titular de la tesis": "Crecimiento del 14,2 % con caja neta."}  # sin datos y cifra inventada: fuera
    assert len(llamadas) == 1  # un lote: el contexto se envía una vez
    llamadas.clear()
    r = borradores.generar([f"apartado {n}" for n in range(8)], "Crece un 14,2 %.")
    assert len(llamadas) == 2 and len(r) == 8  # 8 apartados = 2 lotes de como mucho 6


def test_marcadores_con_borrador_siguen_pendientes():
    from informes_warrants.informe.plantillas import con_borradores, pendientes, sin_marcas_ia

    texto = "Tesis: [[ANALISTA: titular de la tesis]] y [[ANALISTA: riesgo principal]]"
    con = con_borradores(texto, {"titular de la tesis": "Crece con caja neta."})
    assert con == "Tesis: [[IA: titular de la tesis || Crece con caja neta.]] y [[ANALISTA: riesgo principal]]"
    assert pendientes(con) == ["riesgo principal", "revisar el borrador de la IA (titular de la tesis)"]
    assert sin_marcas_ia(con) == "Tesis: Crece con caja neta. y [[ANALISTA: riesgo principal]]"


# --- B3: estructura corporativa y equipo directivo ---------------------------------------------------------------

def test_rentabilidad_desde_el_alta_y_filiales():
    import pandas as pd

    from informes_warrants.calculo.analitica import rentabilidad_desde
    from informes_warrants.ingesta.directivos import filiales

    idx = pd.bdate_range("2024-01-01", "2026-10-09", tz="America/New_York")
    cierres = pd.Series([100.0] * (len(idx) - 1) + [150.0], index=idx)
    assert rentabilidad_desde(cierres, date(2025, 1, 10)) == pytest.approx(0.5)
    assert rentabilidad_desde(cierres, date(2020, 1, 1)) is None  # la serie no llega: no se extrapola
    df = pd.DataFrame([{"name": "Apple  Asia LLC", "jurisdiction": "Delaware, U.S."},
                       {"name": "Apple Canada Inc.", "jurisdiction": "Canada"},
                       {"name": "Apple Inc. (Delaware)", "jurisdiction": "Delaware, U.S."}])
    lista = type("L", (), {"to_dataframe": lambda self: df})()
    f = filiales(type("T", (), {"subsidiaries": lista})())
    assert f["total"] == 3 and f["lista"][0]["nombre"] == "Apple Asia LLC" and f["jurisdicciones"][0] == ("Delaware, U.S.", 2)
    assert filiales(type("T", (), {"subsidiaries": None})()) is None


# --- B5: opciones y posiciones cortas (fuente externa) ------------------------------------------------------------

def test_mercado_de_opciones_a_mano():
    import pandas as pd

    from informes_warrants.calculo.derivados import lectura_cortos, max_pain, mercado_de_opciones, put_call, volatilidad_realizada

    calls = pd.DataFrame({"strike": [90.0, 100.0, 110.0], "volume": [100, 200, 1200], "openInterest": [1000, 500, 300],
                          "impliedVolatility": [0.30, 0.25, 0.40], "lastPrice": [11.0, 3.0, 1.0], "vencimiento": ["2026-11-20"] * 3})
    puts = pd.DataFrame({"strike": [90.0, 100.0, 110.0], "volume": [300, 100, 0], "openInterest": [800, 400, 100],
                         "impliedVolatility": [0.35, 0.30, 0.20], "lastPrice": [1.0, 3.0, 10.0], "vencimiento": ["2026-11-20"] * 3})
    pc = put_call(calls, puts)
    assert pc["volumen"] == pytest.approx(400 / 1500) and pc["posiciones"] == pytest.approx(1300 / 1800)
    # lo que cobran los compradores: a 90 → 0 + (100−90)·400 + (110−90)·100 = 6.000; a 100 → 10·1000 + 10·100 = 11.000;
    # a 110 → 20·1000 + 10·500 = 25.000 → max pain (el mínimo) = 90
    assert max_pain(calls, puts) == 90.0
    m = mercado_de_opciones({"vencimientos": ["2026-11-20"], "calls": calls, "puts": puts, "consulta": "2026-10-14"}, 100.0,
                            [100 * (1.01 ** i) for i in range(30)])
    assert m["iv_calls"] == pytest.approx((0.30 * 100 + 0.25 * 200 + 0.40 * 1200) / 1500)
    assert [f["strike"] for f in m["inusual"]] == [110.0]  # 1.200 contratos > 2 × 300 abiertos
    assert volatilidad_realizada([100 * (1.01 ** i) for i in range(30)]) == pytest.approx(0.0, abs=1e-9)  # sin dispersión
    assert lectura_cortos(0.12) == "elevado" and lectura_cortos(0.02) == "bajo" and lectura_cortos(None) is None


def test_stop_tamano_var_a_mano():
    from informes_warrants.calculo.posicion import dias_para_construir, stop_volatilidad, tamano_posicion, var_historico

    s = stop_volatilidad(100.0, 0.02, 2.0, 25)  # 2 × 2 % × √25 = 20 % de pérdida
    assert s["perdida"] == pytest.approx(0.20) and s["stop"] == pytest.approx(80.0)
    assert stop_volatilidad(100.0, 0.02, 2.0, 25, perdida_maxima=0.10)["stop"] == pytest.approx(90.0)  # acotado
    t = tamano_posicion(1_000_000, 0.01, 100.0, 90.0)  # arriesgar 10.000 USD con 10 USD por acción = 1.000 acciones
    assert t["acciones"] == pytest.approx(1000) and t["peso"] == pytest.approx(0.10)
    assert tamano_posicion(1_000_000, 0.01, 100.0, 90.0, peso_maximo=0.05)["acciones"] == pytest.approx(500)
    assert dias_para_construir(1000, 10_000, 0.05) == pytest.approx(2.0)
    rend = [i / 1000 - 0.05 for i in range(101)]  # −5 % … +5 %
    var, cvar = var_historico(rend)
    assert var == pytest.approx(-0.045) and cvar < var


def test_prueba_historica_del_stop():
    from informes_warrants.calculo.posicion import frecuencia_stop

    serie = [100.0] * 30 + [85.0] + [100.0] * 30  # una caída del 15 % en una sesión
    f = frecuencia_stop(serie, 0.10, 5)
    assert f == pytest.approx(5 / 56)  # solo las 5 ventanas que contienen la caída (de 56)
    assert frecuencia_stop(serie, 0.20, 5) == 0.0 and frecuencia_stop([100.0] * 10, 0.1, 5) is None
