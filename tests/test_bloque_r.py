"""Bloque R (propuestas aprobadas R2-R18): cada fórmula con valores calculados a mano, sin conexión."""

from dataclasses import asdict, dataclass, replace
from datetime import date

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
