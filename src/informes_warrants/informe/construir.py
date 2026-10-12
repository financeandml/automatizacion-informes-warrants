"""Ensamblado de los datos de un informe (plantilla general) a partir de un ticker.

Orden: SEC (normalizador, 5 ejercicios + LTM) → contraste con el XBRL del último 10-K → semáforo de
calidad → mercado y tipo libre de riesgo → estimaciones por defecto (medias históricas) y escenarios →
DCF de escenarios, DCF inverso y proyección hasta el BPA → comparables → recomendación propuesta →
gobierno, puntuaciones y cambios en los riesgos → riesgos (lista literal + selección de IA opcional) →
analítica y notas → textos de las plantillas. Todas las cifras salen del motor matemático (calculo/);
la IA solo elige y resume títulos literales del 10-K.
"""

import logging
import re
import statistics
from dataclasses import replace
from datetime import date

from ..calculo.analitica import apalancamiento_operativo, puente_margen, uso_del_capital
from ..calculo.calidad import revisar
from ..calculo.dcf import beta, crecimiento_implicito, valorar_escenarios, wacc_implicito
from ..calculo.metricas import Mercado, cagr, fundamentales, valoracion
from ..calculo.normalizador import (
    LTM,
    LTM_PREVIO,
    FuenteEntityFacts,
    FuenteLTM,
    FuenteXBRL,
    acciones_en_circulacion,
    ltm_desde_anual,
    normalizar,
)
from ..calculo.notas import notas_de_ratios
from ..calculo.proyeccion import proyectar
from ..calculo.puntuaciones import altman, beneish, piotroski
from ..calculo.valoracion_relativa import estadisticas, valor_implicito, valor_por_multiplos
from .cobertura import PENDIENTE_VALIDAR, PLANTILLA_GENERAL, cobertura_de
from .estimaciones import ANIOS_EXPLICITOS, Escenarios, Estimaciones, escenarios_por_defecto, recomendacion_propuesta
from .plantillas import pendientes, rellenar
from .secciones import BLOQUES, Tipo

log = logging.getLogger(__name__)
ANIOS = 5
PARTIDAS_CONTRASTE = ("ingresos", "resultado_operativo", "beneficio_neto", "activos", "patrimonio", "flujo_operativo")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _limitar(x, bajo, alto):
    return max(bajo, min(alto, x))


def _media(valores):
    valores = [v for v in valores if v is not None]
    return statistics.fmean(valores) if valores else None


def _desviacion(valores):
    valores = [v for v in valores if v is not None]
    return statistics.stdev(valores) if len(valores) >= 2 else None


def _observaciones(fund: dict[int, dict], ejercicios: list[int], f_ltm: dict | None) -> list[dict]:
    """Los 3 últimos periodos de doce meses: los 2 últimos ejercicios y el LTM (o los 3 últimos ejercicios sin LTM)."""
    if f_ltm is None:
        return [fund[a] for a in ejercicios[-3:]]
    return [fund[a] for a in ejercicios[-2:]] + [f_ltm]


def estimaciones_por_defecto(fund: dict[int, dict], ejercicios: list[int], beta_estimada: float, estados=None,
                             rf: float | None = None, f_ltm: dict | None = None) -> Estimaciones:
    """Supuestos iniciales del analista: medias de los 3 últimos periodos de doce meses (los 2 últimos
    ejercicios y el LTM, si lo hay), acotadas a rangos razonables."""
    ult = ejercicios[-3:]
    obs = _observaciones(fund, ejercicios, f_ltm)
    crec = _media(o["crecimiento_ingresos"] for o in obs)
    margen = _media(o["margen_ebitda"] for o in obs)
    da = _media((o["ebitda"] - o["ebit"]) / o["ingresos"] for o in obs if o["ebitda"] is not None and o["ingresos"])
    capex = _media(o["capex_sobre_ventas"] for o in obs)
    tipo = _media(o["tipo_efectivo"] for o in obs)
    base = Estimaciones()
    extra = {}
    if estados is not None:
        v = estados.valor
        financiero = _media((v("bai", a) - v("resultado_operativo", a)) / v("ingresos", a) for a in ult
                            if None not in (v("bai", a), v("resultado_operativo", a)) and v("ingresos", a))
        despues_impuestos = {a: v("bai", a) - v("impuestos", a) for a in ult if None not in (v("bai", a), v("impuestos", a))}
        minoritarios = _media(1 - v("beneficio_neto", a) / despues_impuestos[a] for a in despues_impuestos
                              if v("beneficio_neto", a) is not None and despues_impuestos[a] > 0)
        acciones = cagr(v("acciones_diluidas", ult[0]), v("acciones_diluidas", ult[-1]), len(ult) - 1)
        payout = _media(fund[a]["payout"] for a in ult)
        extra = {
            "resultado_financiero_sobre_ventas": round(_limitar(financiero or 0.0, -0.2, 0.2), 4),
            "cuota_minoritarios": round(_limitar(minoritarios or 0.0, 0.0, 0.5), 4),
            "variacion_acciones": round(_limitar(acciones or 0.0, -0.05, 0.05), 4),
            "payout": round(_limitar(payout or 0.0, 0.0, 1.5), 4),
        }
    return Estimaciones(
        crecimiento_ventas=[round(_limitar(crec if crec is not None else 0.05, -0.10, 0.25), 4)] * ANIOS_EXPLICITOS,
        margen_ebitda=[round(_limitar(margen if margen is not None else 0.20, -0.5, 0.8), 4)] * ANIOS_EXPLICITOS,
        da_sobre_ventas=round(_limitar(da if da is not None else base.da_sobre_ventas, 0, 0.3), 4),
        capex_sobre_ventas=round(_limitar(capex if capex is not None else base.capex_sobre_ventas, 0, 0.4), 4),
        circulante_sobre_ventas=0.0,
        tasa_fiscal=round(_limitar(tipo if tipo is not None else base.tasa_fiscal, 0.05, 0.35), 4),
        rf=round(rf, 4) if rf is not None else base.rf,
        beta=round(_limitar(beta_estimada, 0.3, 3.0), 2),
        **extra,
    )


def etiquetas_estimadas(fecha_ltm: str | None, ejercicio: int, n: int) -> list[str]:
    """Periodos de 12 meses a partir del LTM («jun-27e» = 12 meses hasta junio de 2027)."""
    if not fecha_ltm:
        return [f"FY{ejercicio + k}e" for k in range(1, n + 1)]
    d = date.fromisoformat(fecha_ltm)
    return [f"{MESES[d.month - 1]}-{(d.year + k) % 100:02d}e" for k in range(1, n + 1)]


def periodo_largo(fecha_ltm: str | None, ejercicio: int, k: int) -> str:
    """«los doce meses hasta junio de 2031» (o «FY2030» sin LTM): para el texto corrido."""
    if not fecha_ltm:
        return f"FY{ejercicio + k}"
    d = date.fromisoformat(fecha_ltm)
    nombres = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
               "diciembre")
    return f"los doce meses hasta {nombres[d.month - 1]} de {d.year + k}"


def _cita_negocio(texto_item_1: str) -> str:
    """Primeras frases literales del Item 1 que describen la compañía."""
    for parrafo in (p.strip() for p in (texto_item_1 or "").splitlines()):
        if len(parrafo) > 150 and not parrafo.lower().startswith("item"):
            frases = re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(parrafo.split()))
            return " ".join(frases[:2])
    return ""


def _beta_semanal(ticker: str) -> float:
    from ..ingesta.mercado import INDICE, historico

    a = historico(ticker)["Close"].resample("W-FRI").last().pct_change()
    i = historico(INDICE)["Close"].resample("W-FRI").last().pct_change()
    juntos = a.to_frame("a").join(i.to_frame("i"), how="inner").dropna()
    return beta(juntos["a"], juntos["i"])


def _series_bolsa(ticker: str, etf: str, historico, indice: str) -> dict:
    """Cierres de 5 años de la empresa, el S&P 500 y (si es distinto) su ETF sectorial."""
    series = {ticker: historico(ticker, 5)["Close"], "S&P 500": historico(indice, 5)["Close"]}
    if etf != indice:
        series[etf] = historico(etf, 5)["Close"]
    return series


def _gastos(estados, clave):
    return {"id": estados.valor("id", clave), "gastos_generales": estados.valor("gastos_generales", clave)}


def componer(*, ticker: str, empresa: str, sic, cobertura, filing: dict, estados, calidad, cotizacion, acciones: float,
             beta_estimada: float, comportamiento: dict, series_bolsa: dict, riesgos: list, riesgos_lista: list,
             texto_negocio: str, fecha: str | None = None, estimaciones: Estimaciones | None = None,
             escenarios: Escenarios | None = None, estados_ltm=None, fecha_ltm: str | None = None, rf=None,
             comparables: list[dict] | None = None, comparables_criterio: str = "", comparables_del_analista: bool = False,
             gobierno=None, riesgos_cambios: dict | None = None, acciones_origen: str = "") -> dict:
    """Parte pura (sin red): de los datos ya reunidos al contexto completo del informe.

    Sin `estimaciones` ni `escenarios`, se usan los de por defecto; el editor pasa los del analista y todo se
    recalcula. Sin `estados_ltm` (p. ej. en los tests), el LTM es el último ejercicio fiscal.
    """
    from ..ingesta.mercado import etf_sectorial

    ejercicios = estados.ejercicios[-ANIOS:]  # el ejercicio anterior, si se cargó, solo sirve de base del crecimiento
    ejercicio = filing["ejercicio"]
    fund = {a: fundamentales(estados, a) for a in ejercicios}
    ltm = estados_ltm if estados_ltm is not None else ltm_desde_anual(estados, ejercicio)
    f_ltm = fundamentales(ltm, LTM)
    mercado = Mercado(cotizacion.precio, acciones, cotizacion.fecha)
    multiplos = valoracion(ltm, LTM, mercado)
    f = fund[ejercicio]

    # Estimaciones y escenarios (editables). El coste de la deuda solo se ajusta si la empresa declara intereses.
    base = estimaciones
    if base is None:
        base = estimaciones_por_defecto(fund, ejercicios, beta_estimada, estados, rf.valor if rf else None,
                                        f_ltm if estados_ltm is not None else None)
        intereses = estados.valor("gasto_intereses", ejercicio)
        if intereses and f["deuda_bruta"]:
            base = replace(base, coste_deuda=round(_limitar(intereses / f["deuda_bruta"], 0.02, 0.12), 4))
    if errores := base.validar():
        raise ValueError("Estimaciones no válidas: " + " ".join(errores))
    obs = [fund[a] for a in ejercicios[-3:]] + ([f_ltm] if estados_ltm is not None else [])  # misma ventana que la base
    esc = escenarios or escenarios_por_defecto(base, _desviacion(o["crecimiento_ingresos"] for o in obs),
                                               _desviacion(o["margen_ebitda"] for o in obs))
    base = esc.base

    dfn, deuda = f_ltm["dfn"] or 0.0, f_ltm["deuda_bruta"]
    minoritarios = ltm.valor("minoritarios", LTM) or 0.0
    avisos_valoracion = []
    try:
        r_esc = valorar_escenarios(esc, f_ltm["ingresos"], dfn, deuda, minoritarios, acciones, mercado.capitalizacion)
        valor = r_esc.resultados["Base"]
    except ValueError as e:
        r_esc, valor = None, None
        avisos_valoracion.append(f"DCF no aplicable: {e}")
    inverso = {"crecimiento": None, "wacc": None}
    if valor is not None:
        inverso["crecimiento"] = crecimiento_implicito(base, f_ltm["ingresos"], dfn, deuda, minoritarios, acciones,
                                                       mercado.capitalizacion, cotizacion.precio)
        inverso["wacc"] = wacc_implicito(base, f_ltm["ingresos"], dfn, minoritarios, acciones, cotizacion.precio)
    proyeccion = proyectar(base, f_ltm["ingresos"], ltm.valor("acciones_diluidas", LTM) or acciones)

    comps = comparables or []
    stats = estadisticas(comps)
    implicitos = valor_implicito(stats, f_ltm, dfn, minoritarios, acciones)
    valor_multiplos = valor_por_multiplos(implicitos)
    valor_dcf = r_esc.valor_ponderado if r_esc else None
    if valor_dcf is not None and valor_multiplos is not None:
        precio_modelo = base.peso_dcf * valor_dcf + (1 - base.peso_dcf) * valor_multiplos
    else:
        precio_modelo = valor_dcf if valor_dcf is not None else valor_multiplos
    precio_objetivo = base.precio_objetivo_analista or precio_modelo  # el del analista prevalece si lo fija
    potencial = precio_objetivo / cotizacion.precio - 1 if precio_objetivo else None
    potencial_dcf = valor_dcf / cotizacion.precio - 1 if valor_dcf else None
    propuesta = recomendacion_propuesta(potencial) if potencial is not None else "Pendiente"

    # Analítica, notas y puntuaciones (deterministas)
    puente = puente_margen(fund[ejercicios[0]], f_ltm, _gastos(estados, ejercicios[0]), _gastos(ltm, LTM))
    apalancamiento = apalancamiento_operativo(fund[ejercicios[0]], f_ltm)
    uso = uso_del_capital(estados, ejercicios, fund)
    notas = notas_de_ratios(f_ltm, ltm, LTM, multiplos, uso["retribucion"])
    puntuaciones = []
    if cobertura is None or cobertura.plantilla == PLANTILLA_GENERAL:
        previo = ejercicio - 1 if ejercicio - 1 in estados.ejercicios else None
        puntuaciones.append(altman(estados, ejercicio, mercado.capitalizacion))
        if previo is not None:
            puntuaciones += [beneish(estados, ejercicio, previo), piotroski(estados, ejercicio, previo)]

    anio_ini = ejercicios[0]
    etiquetas = etiquetas_estimadas(fecha_ltm, ejercicio, len(base.crecimiento_ventas))
    datos = {
        "empresa": empresa, "ticker": ticker, "ejercicio": f"FY{ejercicio}",
        "recomendacion_propuesta": propuesta, "precio_objetivo": precio_objetivo, "precio": cotizacion.precio,
        "potencial": potencial, "potencial_dcf": potencial_dcf, "ventas": f["ingresos"] / 1e6,
        "crecimiento_ventas": f["crecimiento_ingresos"],
        "margen_ebitda": f["margen_ebitda"], "dfn_ebitda": f["dfn_ebitda"],
        "anio_ini": anio_ini, "anio_fin": ejercicio, "ventas_ini": fund[anio_ini]["ingresos"] / 1e6,
        "ventas_fin": f["ingresos"] / 1e6, "cagr_ventas": cagr(fund[anio_ini]["ingresos"], f["ingresos"], len(ejercicios) - 1),
        "margen_ebitda_ini": fund[anio_ini]["margen_ebitda"], "margen_ebitda_fin": f["margen_ebitda"], "dfn": (f["dfn"] or 0) / 1e6,
        "ventas_est": proyeccion[-1].ventas / 1e6, "anio_fin_est": periodo_largo(fecha_ltm, ejercicio, len(proyeccion)),
        "cagr_ventas_est": cagr(f_ltm["ingresos"], proyeccion[-1].ventas, len(proyeccion)),
        "margen_ebitda_est": base.margen_ebitda[-1],
        "riesgos": riesgos or [{"resumen": "[[ANALISTA: resume los riesgos principales del Item 1A]]", "cita": "—"}],
        "cita_negocio": _cita_negocio(texto_negocio)
        or "[[ANALISTA: describe el negocio (el 10-K no tiene un párrafo descriptivo extraíble)]]",
        "segmentos": [],
        "margen_bruto": f["margen_bruto"], "margen_operativo": f["margen_operativo"], "roic": f["roic"], "roe": f["roe"],
        "fcf": (f["fcf"] or 0) / 1e6, "conversion_fcf": f["conversion_fcf"],
        "precio_objetivo_dcf": valor_dcf, "precio_objetivo_multiplos": valor_multiplos,
        "wacc": valor.wacc if valor else None, "g": base.g,
        "auditor": (gobierno.auditor if gobierno and gobierno.auditor else "[[ANALISTA: auditor (Item 9 / proxy)]]"),
        "gobierno": gobierno, "puente": puente, "apalancamiento": apalancamiento, "uso": uso, "fecha_ltm": fecha_ltm,
        "crecimiento_ltm": f_ltm["crecimiento_ingresos"], "margen_operativo_ltm": f_ltm["margen_operativo"],
        "margen_operativo_ini": fund[anio_ini]["margen_operativo"],
        "escenarios": {n: r.valor_por_accion for n, r in r_esc.resultados.items()} if r_esc else {},
        "crecimiento_implicito": inverso["crecimiento"], "wacc_implicito": inverso["wacc"],
        "crecimiento_base": base.crecimiento_ventas[0],
    }
    textos = {b.id: rellenar(b.id, datos) for b in BLOQUES if b.tipo in (Tipo.PLANTILLA, Tipo.ANALISTA)}
    return {
        "ticker": ticker, "empresa": empresa, "sic": sic, "etf": etf_sectorial(sic), "cobertura": cobertura, "filing": filing,
        "ejercicios": ejercicios, "estados": estados, "fundamentales": fund, "calidad": calidad,
        "estados_ltm": ltm, "fund_ltm": f_ltm, "fecha_ltm": fecha_ltm, "rf": rf, "acciones_origen": acciones_origen,
        "cotizacion": cotizacion, "mercado": mercado, "multiplos": multiplos, "comportamiento": comportamiento,
        "estimaciones": base, "escenarios": esc, "dcf_escenarios": r_esc, "beta": beta_estimada, "dcf": valor,
        "inverso": inverso, "proyeccion": proyeccion, "etiquetas_estimadas": etiquetas,
        "comparables": comps, "comparables_stats": stats, "comparables_implicitos": implicitos,
        "comparables_criterio": comparables_criterio, "comparables_del_analista": comparables_del_analista,
        "valor_dcf": valor_dcf, "valor_multiplos": valor_multiplos, "precio_modelo": precio_modelo,
        "precio_objetivo": precio_objetivo, "potencial": potencial, "potencial_dcf": potencial_dcf, "recomendacion": propuesta,
        "avisos_valoracion": avisos_valoracion, "puente": puente, "apalancamiento": apalancamiento, "uso": uso, "notas": notas,
        "puntuaciones": puntuaciones, "gobierno": gobierno, "riesgos_cambios": riesgos_cambios,
        "riesgos": riesgos, "riesgos_lista": riesgos_lista, "textos": textos,
        "pendientes": [p for t in textos.values() for p in pendientes(t)], "fecha": fecha or date.today().isoformat(),
        "series_bolsa": series_bolsa,
    }


def construir(ticker: str, con_ia: bool = True, comparables: list[str] | None = None) -> dict:
    """Reúne los datos (SEC, mercado, IA opcional) y compone el informe. Requiere EDGAR_IDENTITY y red.

    `comparables`: lista del analista; sin ella, el SaaS propone una por código SIC (marcada «Revisar»).
    """
    from edgar import Company

    from ..ingesta import comparables as ingesta_comparables
    from ..ingesta.gobierno import gobierno as datos_gobierno
    from ..ingesta.mercado import INDICE, comportamiento, cotizacion, etf_sectorial, historico, tipo_libre_riesgo
    from ..ingesta.riesgos import comparar_riesgos, riesgos_anteriores, riesgos_anuales

    ticker = ticker.upper()
    empresa = Company(ticker)
    cobertura = cobertura_de(ticker)
    if cobertura.plantilla not in (PLANTILLA_GENERAL, PENDIENTE_VALIDAR):
        raise ValueError(f"{ticker}: {cobertura.motivo}. El PDF de las plantillas sectoriales está pendiente; sus métricas "
                         f"ya se calculan con `informes-warrants metricas {ticker}`.")
    filing = empresa.get_filings(form="10-K", amendments=False).latest()
    xbrl = filing.xbrl()
    ejercicio = int(xbrl.entity_info["fiscal_year"])
    ejercicios = list(range(ejercicio - ANIOS, ejercicio + 1))  # + 1 año previo para el crecimiento del primero

    facts = empresa.get_facts()
    estados = normalizar(FuenteEntityFacts(facts), ejercicios, ticker)
    # Empresa reciente (p. ej. salida a bolsa en 2021): los años sin estados no son errores, sino falta de historial.
    con_datos = [a for a in ejercicios if estados.valor("ingresos", a) is not None and estados.valor("activos", a) is not None]
    sin_historial = [a for a in ejercicios if con_datos and a < min(con_datos)]
    for a in sin_historial:
        estados.faltan.pop(a, None)
    estados.ejercicios = [a for a in estados.ejercicios if a not in sin_historial]
    calidad = revisar(estados, estados.ejercicios[-ANIOS:])  # el año anterior solo es la base del crecimiento
    if sin_historial:
        calidad.avisos.append(f"Sin estados financieros anteriores a FY{min(con_datos)}: historial de {len(con_datos)} ejercicios")
    del_10k = normalizar(FuenteXBRL(xbrl, filing.accession_no), [ejercicio], ticker)
    for p in PARTIDAS_CONTRASTE:  # contraste entre fuentes: companyfacts vs XBRL del último 10-K
        a, b = estados.valor(p, ejercicio), del_10k.valor(p, ejercicio)
        if a is not None and b is not None and abs(a - b) > 0.005 * max(abs(a), abs(b)):
            calidad.errores.append(f"FY{ejercicio}: {p} difiere entre companyfacts ({a:,.0f}) y el 10-K ({b:,.0f})")

    # LTM: hasta el cierre del último 10-Q/10-K; si no cuadra (o no hay trimestres, 20-F), el último ejercicio.
    periodico = empresa.get_filings(form=["10-Q", "10-K"], amendments=False).latest()
    fecha_ltm = str(periodico.period_of_report) if periodico is not None else None
    estados_ltm = None
    if fecha_ltm:
        estados_ltm = normalizar(FuenteLTM(facts, date.fromisoformat(fecha_ltm)), [LTM_PREVIO, LTM], ticker)
        calidad_ltm = revisar(estados_ltm, [LTM], etiqueta=lambda _: f"LTM a {fecha_ltm}")
        if calidad_ltm.errores:
            calidad.avisos.append(f"LTM a {fecha_ltm} incompleto ({'; '.join(calidad_ltm.errores)}): se usa FY{ejercicio}")
            estados_ltm, fecha_ltm = None, None
        else:
            calidad.avisos += calidad_ltm.avisos
    acciones, acciones_origen = acciones_en_circulacion(
        facts, date.fromisoformat(fecha_ltm) if fecha_ltm else date.today(),
        (estados_ltm or estados).valor("acciones_diluidas", LTM if estados_ltm else ejercicio))

    del_analista = comparables is not None
    criterio = "lista del analista"
    if not del_analista:
        ingresos_ref = (estados_ltm or estados).valor("ingresos", LTM if estados_ltm else ejercicio)
        comparables, criterio = ingesta_comparables.proponer(empresa.sic, empresa.cik, ingresos_ref)
    datos_comparables = [d for d in (ingesta_comparables.datos(t) for t in comparables) if d]

    riesgos_lista, texto_1a, _ = riesgos_anuales(ticker)
    try:  # la comparación con el año anterior es un añadido: si falla la red, el informe sale sin ella
        anteriores, _ = riesgos_anteriores(ticker)
    except Exception as e:  # noqa: BLE001
        log.warning("Riesgos del informe anual anterior no disponibles: %s", e)
        anteriores = []
    cambios = comparar_riesgos(riesgos_lista, anteriores) if riesgos_lista and anteriores else None
    riesgos = []
    if con_ia and riesgos_lista:
        from ..ia.bloques import riesgos_principales

        elegidos, cfg = riesgos_principales(riesgos_lista, texto_1a)
        riesgos = [{"resumen": s.resumen, "cita": s.cita, "modelo": f"{cfg.proveedor} · {cfg.modelo}"} for s in elegidos]

    return componer(
        ticker=ticker, empresa=empresa.name, sic=empresa.sic, cobertura=cobertura,
        filing={"accession": filing.accession_no, "fecha": str(filing.filing_date), "ejercicio": ejercicio,
                "ultimo_periodico": periodico.accession_no if periodico is not None else None,
                "ultimo_periodico_formulario": periodico.form if periodico is not None else None},
        estados=estados, calidad=calidad, cotizacion=cotizacion(ticker), acciones=acciones,
        beta_estimada=_beta_semanal(ticker), comportamiento=comportamiento(ticker, empresa.sic),
        series_bolsa=_series_bolsa(ticker, etf_sectorial(empresa.sic), historico, INDICE),
        riesgos=riesgos, riesgos_lista=riesgos_lista, texto_negocio=filing.obj().business or "",
        estados_ltm=estados_ltm, fecha_ltm=fecha_ltm, rf=tipo_libre_riesgo(), comparables=datos_comparables,
        comparables_criterio=criterio, comparables_del_analista=del_analista, gobierno=datos_gobierno(empresa, xbrl),
        riesgos_cambios=cambios, acciones_origen=acciones_origen,
    )
