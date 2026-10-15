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
from datetime import date, timedelta

from ..calculo.analitica import (
    apalancamiento_operativo,
    autonomia_de_caja,
    cascada_ebitda_fcf,
    contribucion_segmentos,
    cuotas_de_ingresos,
    dupont,
    estabilidad_margen,
    puente_margen,
    reaccion_resultados,
    rentabilidad_desde,
    uso_del_capital,
)
from ..calculo.calidad import revisar
from ..calculo.dcf import crecimiento_implicito, valorar_escenarios, wacc_implicito
from ..calculo.derivados import lectura_cortos, mercado_de_opciones
from ..calculo.hechos_clave import observaciones as observaciones_clave
from ..calculo.hechos_clave import seleccionar as seleccionar_hechos
from ..calculo.historial import historial as historial_recomendaciones
from ..calculo.historico import METRICAS as METRICAS_HISTORICAS
from ..calculo.historico import Anual, banda
from ..calculo.historico import valor_implicito as valor_implicito_historico
from ..calculo.metricas import Mercado, cagr, componentes_ev, fundamentales, ratio_de_sumas, valoracion
from ..calculo.normalizador import (
    LTM,
    LTM_PREVIO,
    FuenteEntityFacts,
    FuenteLTM,
    FuenteXBRL,
    acciones_en_circulacion,
    concentracion_clientes,
    ltm_desde_anual,
    normalizar,
    segmentos,
    segmentos_ltm,
    trimestres,
    vencimientos_deuda,
)
from ..calculo.normalizador import _silencio as _silencio_edgar
from ..calculo.notas import notas_de_ratios
from ..calculo.posicion import (
    dias_para_construir,
    evaluar_criterios,
    frecuencia_stop,
    rendimientos_diarios,
    stop_volatilidad,
    tamano_posicion,
    var_historico,
)
from ..calculo.proyeccion import balance_inicial, proyectar
from ..calculo.puntuaciones import altman, beneish, piotroski
from ..calculo.sintesis import Metodo, sintetizar
from ..calculo.valoracion_relativa import (
    estadisticas,
    mediana_comparables,
    rango_por_multiplos,
    suma_de_partes,
    valor_implicito,
    valor_por_multiplos,
)
from ..ingesta.ficha import empleados
from .cambios import comparar as comparar_versiones
from .cambios import resumen as resumen_version
from .cobertura import PENDIENTE_VALIDAR, PLANTILLA_GENERAL, cobertura_de, es_biotecnologia
from .estimaciones import ANIOS_EXPLICITOS, Escenarios, Estimaciones, escenarios_por_defecto, recomendacion_propuesta
from .plantillas import MARCADOR, con_borradores, pendientes, rellenar
from .secciones import BLOQUES, Tipo

log = logging.getLogger(__name__)
ANIOS = 5
PARTIDAS_CONTRASTE = ("ingresos", "resultado_operativo", "beneficio_neto", "activos", "patrimonio", "flujo_operativo")
AVISO_PARAMETROS = "Parámetros del fondo sin definir: la gestión de la posición no sale en el informe (Configuración)."
AVISO_CALENDARIO = "Calendario de catalizadores en borrador: confírmalo o introduce el tuyo antes de emitir."
AVISO_COMPARABLES = "Comparables automáticos: introduce tu lista para incluir los múltiplos en el precio objetivo."
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
        # Ratios sobre ventas como suma / suma (no media de ratios): con ventas pequeñas en algún año (biotecnológicas
        # que empiezan a facturar) la media de ratios se dispara (IOVA: intereses de la caja > 20 % de las ventas).
        financiero = ratio_de_sumas([(v("bai", a) - v("resultado_operativo", a), v("ingresos", a)) for a in ult
                                   if None not in (v("bai", a), v("resultado_operativo", a), v("ingresos", a))])
        despues_impuestos = {a: v("bai", a) - v("impuestos", a) for a in ult if None not in (v("bai", a), v("impuestos", a))}
        minoritarios = _media(1 - v("beneficio_neto", a) / despues_impuestos[a] for a in despues_impuestos
                              if v("beneficio_neto", a) is not None and despues_impuestos[a] > 0)
        acciones = cagr(v("acciones_diluidas", ult[0]), v("acciones_diluidas", ult[-1]), len(ult) - 1)
        payout = _media(fund[a]["payout"] for a in ult)
        sbc = ratio_de_sumas([(v("pagos_basados_acciones", a), v("ingresos", a)) for a in ult
                            if None not in (v("pagos_basados_acciones", a), v("ingresos", a))])
        recompras = _media(v("recompras", a) / fund[a]["fcf_tras_sbc"] for a in ult
                           if v("recompras", a) is not None and fund[a]["fcf_tras_sbc"] and fund[a]["fcf_tras_sbc"] > 0)
        extra = {
            "sbc_sobre_ventas": round(_limitar(sbc or 0.0, 0.0, 0.3), 4),
            "recompras_sobre_fcf": round(_limitar(recompras or 0.0, 0.0, 1.5), 4),
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
    from ..ingesta.mercado import beta_semanal

    return beta_semanal(ticker)


def _series_bolsa(ticker: str, etf: str, historico, indice: str) -> dict:
    """Cierres de 5 años de la empresa, el S&P 500 y (si es distinto) su ETF sectorial."""
    series = {ticker: historico(ticker, 5)["Close"], "S&P 500": historico(indice, 5)["Close"]}
    if etf != indice:
        series[etf] = historico(etf, 5)["Close"]
    return series


def _gastos(estados, clave):
    return {"id": estados.valor("id", clave), "gastos_generales": estados.valor("gastos_generales", clave)}


def componer(**datos) -> dict:
    """Contexto del informe sin red: la plantilla sectorial si los datos traen un perfil (B2); si no, la general."""
    if "perfil" in datos:
        from .sectorial import componer_sectorial

        return componer_sectorial(**datos)
    return componer_general(**datos)


def componer_general(*, ticker: str, empresa: str, sic, cobertura, filing: dict, estados, calidad, cotizacion, acciones: float,
             beta_estimada: float, comportamiento: dict, series_bolsa: dict, riesgos: list, riesgos_lista: list,
             texto_negocio: str, fecha: str | None = None, estimaciones: Estimaciones | None = None,
             escenarios: Escenarios | None = None, estados_ltm=None, fecha_ltm: str | None = None, rf=None,
             comparables: list[dict] | None = None, comparables_criterio: str = "", comparables_del_analista: bool = False,
             gobierno=None, insiders: dict | None = None, competencia_texto: dict | None = None, catalizadores: dict | None = None,
             borradores_ia: dict | None = None, filiales: dict | None = None, opciones_cadena: dict | None = None,
             cortos: dict | None = None, parametros=None,
             eventos: list | None = None, alarmas: list | None = None,
             riesgos_cambios: dict | None = None, acciones_origen: str = "", trimestres_lista: list | None = None,
             segmentos_dict: dict | None = None, concentracion: list | None = None, vencimientos: dict | None = None,
             precios_semanales: list | None = None,
             fechas_disponibles: dict | None = None,
             anterior: dict | None = None, historial_resumenes: list | None = None, autoria=None,
             capital_flotante: tuple | None = None, prima=None, beta_sector=None, bolsa: str | None = None,
             cierre_fiscal: str | None = None) -> dict:
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
        if prima is not None:  # prima de riesgo semanal (D7): la propone el SaaS, el analista la confirma
            base = replace(base, erp=round(prima.valor, 4))
    if errores := base.validar():
        raise ValueError("Estimaciones no válidas: " + " ".join(errores))
    obs = [fund[a] for a in ejercicios[-3:]] + ([f_ltm] if estados_ltm is not None else [])  # misma ventana que la base
    esc = escenarios or escenarios_por_defecto(base, _desviacion(o["crecimiento_ingresos"] for o in obs),
                                               _desviacion(o["margen_ebitda"] for o in obs))
    base = esc.base

    # Deuda neta ajustada (R13): DFN + preferentes, pensiones, patrimonio temporal y arrendamientos financieros.
    dfn = f_ltm["deuda_neta_ajustada"] if f_ltm["deuda_neta_ajustada"] is not None else (f_ltm["dfn"] or 0.0)
    deuda = f_ltm["deuda_bruta"]
    minoritarios = ltm.valor("minoritarios", LTM) or 0.0
    datos_dcf = {"ingresos_base": f_ltm["ingresos"], "dfn": dfn, "deuda": deuda, "minoritarios": minoritarios, "acciones": acciones,
                 "capitalizacion": mercado.capitalizacion}
    avisos_valoracion = []
    # Avisos antes de emitir: el SaaS los muestra al analista, no bloquean la emisión y no salen en el informe.
    avisos_emision = [] if comparables_del_analista else [AVISO_COMPARABLES]
    catalizadores = catalizadores_del_informe(catalizadores, base, avisos_emision)
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
    balance_base = balance_inicial(ltm.valor("caja", LTM), ltm.valor("inversiones_cp", LTM), deuda, ltm.valor("patrimonio", LTM),
                                   minoritarios)
    proyeccion = proyectar(base, f_ltm["ingresos"], ltm.valor("acciones_diluidas", LTM) or acciones, balance_base)

    comps = comparables or []
    stats = estadisticas(comps)
    implicitos = valor_implicito(stats, f_ltm, dfn, minoritarios, acciones)
    # La propuesta automática por SIC es orientativa (agrupa mal a muchas empresas: AAPL → DELL, SMCI): la valoración
    # por múltiplos solo entra en el precio objetivo con la lista del analista (aviso antes de emitir, sin bloquear).
    valor_multiplos_orientativo = valor_por_multiplos(implicitos)
    valor_multiplos = valor_multiplos_orientativo if comparables_del_analista else None
    rango_multiplos = rango_por_multiplos(comps, f_ltm, dfn, minoritarios, acciones) if comparables_del_analista else (None, None)
    valor_dcf_escenarios = r_esc.valor_ponderado if r_esc else None

    # Múltiplos frente a su propia historia (R11): bandas de 5 años sobre la cifra de cada ejercicio ya presentado.
    bandas = {}
    if precios_semanales and fechas_disponibles:
        todos = {a: fund.get(a) or fundamentales(estados, a) for a in estados.ejercicios if fechas_disponibles.get(a)}
        anuales = [Anual(fechas_disponibles[a], estados.valor("bpa_diluido", a), x["ebitda"], x["fcf_tras_sbc"],
                         x["deuda_neta_ajustada"], estados.valor("acciones_diluidas", a)) for a, x in todos.items()]
        bandas = {m: banda(m, precios_semanales, anuales) for m in METRICAS_HISTORICAS}
    historicos = {m: {q: valor_implicito_historico(b, f_ltm, dfn, acciones, q) for q in ("mediana", "p25", "p75")}
                  for m, b in bandas.items() if b.n}
    usados_hist = [historicos[m] for m in ("ev_ebitda", "per") if m in historicos and historicos[m]["mediana"]]
    valor_historicos = statistics.fmean(h["mediana"] for h in usados_hist) if usados_hist else None

    def _media_q(q):
        v = [h[q] for h in usados_hist if h[q]]
        return statistics.fmean(v) if v else None

    # Motor de valoración (B1): las plantillas de «Motor de valoración» en un libro propio; prevalece sobre el DCF por
    # escenarios y los comparables anteriores, que se mantienen como análisis complementario (decisión D5).
    from .motor import valorar as valorar_motor
    origen_prima = f"{prima.fuente}{', ' + prima.fecha if prima.fecha else ''}" if prima is not None else "Estimaciones del informe"
    motor = valorar_motor({
        "ticker": ticker, "empresa": empresa, "filing": filing, "segmentos": segmentos_dict or {}, "estados": estados, "estados_ltm": ltm,
        "fecha_ltm": fecha_ltm, "cotizacion": cotizacion, "estimaciones": base, "bandas": bandas, "mercado": mercado,
        "acciones_origen": acciones_origen, "beta": beta_estimada, "rf": rf, "origen_prima": origen_prima, "comparables": comps,
        "comparables_del_analista": comparables_del_analista, "comparables_criterio": comparables_criterio, "beta_sector": beta_sector})
    sm = (motor or {}).get("salidas") or {}
    if motor and motor.get("error"):
        avisos_emision.append(f"Motor de valoración no disponible ({motor['error']}): el DCF es el de escenarios")
    avisos_emision += (motor or {}).get("avisos") or []
    valor_dcf = sm.get("precio_dcf") if sm.get("precio_dcf") is not None else valor_dcf_escenarios
    if sm.get("precio_dcf") is not None and sm["precio_dcf"] <= 0:  # no es una valoración: se muestra, no entra en el precio
        valor_dcf = None
        importe = f"{sm['precio_dcf']:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".").replace("-", "−")
        avisos_emision.append(f"Motor de valoración: el DCF da {importe} USD por acción (el valor de la empresa no "
                              "cubre la deuda neta con estos supuestos); no entra en el precio objetivo: revisa los supuestos")
    wacc_motor = sm.get("wacc")
    wacc_informe = wacc_motor if wacc_motor is not None else (valor.wacc if valor else None)
    if sm and comparables_del_analista:  # comparables del motor: media de los precios a la mediana EV/EBITDA y PER
        centrales = [x for x in (sm.get("comps_ebitda"), sm.get("comps_per")) if x is not None and x > 0]
        valor_multiplos = statistics.fmean(centrales) if centrales else valor_multiplos
        bajos = [x for x in (sm.get("comps_ebitda_bajo"), sm.get("comps_per_bajo")) if x is not None and x > 0]
        altos = [x for x in (sm.get("comps_ebitda_alto"), sm.get("comps_per_alto")) if x is not None and x > 0]
        if bajos and altos:
            rango_multiplos = (min(bajos), max(altos))

    # Suma de partes (R14): resultado de cada segmento del último ejercicio × EV/EBIT (analista o mediana de comparables).
    sotp = None
    negocio = (segmentos_dict or {}).get("negocio")
    if negocio and negocio.resultado_operativo:
        resultado = {n: s[ejercicio] for n, s in negocio.resultado_operativo.items() if ejercicio in s}
        if resultado and len(resultado) == len([n for n, s in negocio.miembros.items() if ejercicio in s]):
            mediana_ev_ebit = mediana_comparables(comps, "ev_ebit", 50.0) if comparables_del_analista else None
            sotp = suma_de_partes(resultado, f["ebit"], base.multiplos_sotp, mediana_ev_ebit, dfn, minoritarios, acciones)

    # Derivación del precio objetivo (R8): media ponderada de los métodos disponibles, con los pesos del analista.
    pesimista = r_esc.resultados["Pesimista"].valor_por_accion if r_esc else None
    optimista = r_esc.resultados["Optimista"].valor_por_accion if r_esc else None
    supuesto_motor = (f"Modelo de valoración: WACC {wacc_motor * 100:.1f} %, g {base.g * 100:.1f} %; rango WACC ± 0,5 pp y g ± 0,5 pp"
                      .replace(".", ",", 2) if wacc_motor is not None else "")
    metodos = [
        Metodo("DCF", valor_dcf, sm.get("sintesis_dcf_bajo") if sm else pesimista, sm.get("sintesis_dcf_alto") if sm else optimista,
               supuesto_motor or (f"WACC {valor.wacc * 100:.1f} %, g {base.g * 100:.1f} %; escenarios 25/50/25".replace(".", ",")
                                  if valor else ""), base.pesos.get("DCF", 0.0)),
        Metodo("DCF por escenarios", valor_dcf_escenarios if sm else None, pesimista, optimista,
               f"WACC {valor.wacc * 100:.1f} %, g {base.g * 100:.1f} %; escenarios 25/50/25".replace(".", ",") if valor else "",
               base.pesos.get("DCF por escenarios", 0.0)),
        Metodo("Comparables", valor_multiplos, *rango_multiplos,
               ("Mediana EV/EBITDA y PER de la lista del analista (modelo de valoración); rango mínimo-máximo" if sm else
                "Mediana EV/EBITDA y PER de la lista del analista") if comparables_del_analista else "Falta la lista del analista",
               base.pesos.get("Comparables", 0.0)),
        Metodo("Múltiplos históricos", valor_historicos, _media_q("p25"), _media_q("p75"),
               "Mediana de EV/EBITDA y PER de 5 años", base.pesos.get("Múltiplos históricos", 0.0)),
        Metodo("Suma de partes", sotp["por_accion"] if sotp else None, None, None, "EV/EBIT por segmento",
               base.pesos.get("Suma de partes", 0.0)),
    ]
    precio_modelo, metodos = sintetizar(metodos)
    precio_objetivo = base.precio_objetivo_analista or precio_modelo  # el del analista prevalece si lo fija
    potencial = precio_objetivo / cotizacion.precio - 1 if precio_objetivo else None
    potencial_dcf = valor_dcf / cotizacion.precio - 1 if valor_dcf else None
    propuesta = recomendacion_propuesta(potencial) if potencial is not None else "Pendiente"
    gestion = _gestion(parametros, cotizacion, series_bolsa.get(ticker), {
        "potencial": potencial, "per": multiplos.get("per"), "ev_ebitda": multiplos.get("ev_ebitda"),
        "dfn_ebitda": f_ltm.get("dfn_ebitda"), "roic": f_ltm.get("roic"), "crecimiento": f_ltm.get("crecimiento_ingresos")})
    if gestion is None:
        avisos_emision.append(AVISO_PARAMETROS)

    # Analítica, notas y puntuaciones (deterministas)
    puente = puente_margen(fund[ejercicios[0]], f_ltm, _gastos(estados, ejercicios[0]), _gastos(ltm, LTM))
    apalancamiento = apalancamiento_operativo(fund[ejercicios[0]], f_ltm)
    uso = uso_del_capital(estados, ejercicios, fund)
    notas = notas_de_ratios(f_ltm, ltm, LTM, multiplos, uso["retribucion"])
    autonomia = autonomia_de_caja(f_ltm, ltm, LTM, None, 0)  # R2: solo si consume caja
    if autonomia and ejercicio - 3 in estados.ejercicios:
        acc = [estados.valor("acciones_diluidas", a) for a in (ejercicio - 3, ejercicio)]
        autonomia["dilucion_anual"] = cagr(acc[0], acc[1], 3)
        autonomia["anios_dilucion"] = 3
    desglose_crec = None
    for eje in ("negocio", "producto"):  # origen del crecimiento por segmento (último año validado frente al anterior)
        d = (segmentos_dict or {}).get(eje)
        if d and len(d.ejercicios) >= 2:
            desglose_crec = contribucion_segmentos(d.miembros, d.ejercicios[-2], d.ejercicios[-1])
            if desglose_crec:
                desglose_crec.update(eje=eje, inicio=d.ejercicios[-2], fin=d.ejercicios[-1])
                break
    puntuaciones = []
    if cobertura is None or cobertura.plantilla == PLANTILLA_GENERAL:
        previo = ejercicio - 1 if ejercicio - 1 in estados.ejercicios else None
        puntuaciones.append(altman(estados, ejercicio, mercado.capitalizacion))
        if previo is not None:
            puntuaciones += [beneish(estados, ejercicio, previo), piotroski(estados, ejercicio, previo)]

    anio_ini = ejercicios[0]
    etiquetas = etiquetas_estimadas(fecha_ltm, ejercicio, len(base.crecimiento_ventas))
    # Hechos clave (A2): reglas sobre lo ya calculado
    banda_hist = next((bandas[k] for k in ("ev_ebitda", "per") if bandas.get(k) and bandas[k].n), None)
    por_ingresos = [x for x in (concentracion or []) if x["base"] == "Ingresos" and not x["detalle"]]
    principal_cliente = None
    if por_ingresos:
        anio = max(por_ingresos[0]["valores"])
        principal_cliente = {"cliente": por_ingresos[0]["cliente"], "porcentaje": por_ingresos[0]["valores"][anio], "anio": anio}
    hechos = seleccionar_hechos(observaciones_clave({
        "ingresos": f_ltm.get("ingresos"), "crecimiento": f_ltm.get("crecimiento_ingresos"),
        "variacion_margen_pb": puente["total"] if puente else None, "margen_inicio": fund[ejercicios[0]]["margen_operativo"],
        "margen_fin": f_ltm.get("margen_operativo"), "anio_inicio": ejercicios[0], "principal": puente["principal"] if puente else None,
        "roic": f_ltm.get("roic"), "wacc": wacc_informe,
        "roic_menos_wacc": f_ltm["roic"] - wacc_informe if wacc_informe is not None and f_ltm.get("roic") is not None else None,
        "meses_caja": autonomia["meses"] if autonomia else None, "dfn": f_ltm.get("dfn"), "dfn_ebitda": f_ltm.get("dfn_ebitda"),
        "potencial": potencial, "precio_objetivo": precio_objetivo, "recomendacion": propuesta,
        "percentil": banda_hist.percentil_actual if banda_hist else None,
        "metrica_historica": METRICAS_HISTORICAS[banda_hist.metrica] if banda_hist else None,
        "multiplo_actual": banda_hist.actual if banda_hist else None, "multiplo_mediana": banda_hist.mediana if banda_hist else None,
        "alarmas": alarmas or [], "puntuaciones": {p.nombre: p.lectura for p in puntuaciones},
        "cliente_principal": principal_cliente,
        "compras_agrupadas": (insiders or {}).get("actividad", {}).get("agrupadas"),
    }))
    datos = {
        "hechos": hechos,
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
        "wacc": wacc_informe, "g": base.g, "wacc_escenarios": valor.wacc if valor else None,
        "valor_escenarios": valor_dcf_escenarios, "motor_precio": sm.get("precio_dcf"),
        "motor_segmentos": len(motor["datos"].segmentos) if motor and motor.get("datos") else 0,
        "motor_perpetuidad": (motor["modelo"].salidas.get("pct_perpetuidad_efectivo") if motor and motor.get("modelo") else None),
        "motor_convencion": ("mitad de año" if motor and motor.get("modelo") and motor["modelo"].valores.get(("Entradas", 14, 3)) == 1
                             else "fin de año"),
        "auditor": (gobierno.auditor if gobierno and gobierno.auditor else "[[ANALISTA: auditor (Item 9 / proxy)]]"),
        "gobierno": gobierno, "puente": puente, "apalancamiento": apalancamiento, "uso": uso, "fecha_ltm": fecha_ltm,
        "crecimiento_ltm": f_ltm["crecimiento_ingresos"], "margen_operativo_ltm": f_ltm["margen_operativo"],
        "margen_operativo_ini": fund[anio_ini]["margen_operativo"],
        "escenarios": {n: r.valor_por_accion for n, r in r_esc.resultados.items()} if r_esc else {},
        "crecimiento_implicito": inverso["crecimiento"], "wacc_implicito": inverso["wacc"],
        "crecimiento_base": base.crecimiento_ventas[0], "contribucion": desglose_crec,
        "es_biotecnologia": es_biotecnologia(sic),
    }
    textos = {b.id: rellenar(b.id, datos) for b in BLOQUES if b.tipo in (Tipo.PLANTILLA, Tipo.ANALISTA)}
    textos["negocio.competencia"] = _texto_competencia(competencia_texto)
    if borradores_ia:  # borrador de la IA en cada apartado del analista que lo tiene (lo revisa el analista)
        textos = {k: con_borradores(v, borradores_ia) for k, v in textos.items()}
    c = {
        "ticker": ticker, "empresa": empresa, "sic": sic, "etf": etf_sectorial(sic), "cobertura": cobertura, "filing": filing,
        "ejercicios": ejercicios, "estados": estados, "fundamentales": fund, "calidad": calidad,
        "estados_ltm": ltm, "fund_ltm": f_ltm, "fecha_ltm": fecha_ltm, "rf": rf, "acciones_origen": acciones_origen,
        "cotizacion": cotizacion, "mercado": mercado, "multiplos": multiplos, "comportamiento": comportamiento,
        "estimaciones": base, "escenarios": esc, "dcf_escenarios": r_esc, "beta": beta_estimada, "dcf": valor,
        "inverso": inverso, "proyeccion": proyeccion, "etiquetas_estimadas": etiquetas,
        "comparables": comps, "comparables_stats": stats, "comparables_implicitos": implicitos,
        "comparables_criterio": comparables_criterio, "comparables_del_analista": comparables_del_analista,
        "valor_dcf": valor_dcf, "valor_multiplos": valor_multiplos, "valor_multiplos_orientativo": valor_multiplos_orientativo,
        "valor_dcf_escenarios": valor_dcf_escenarios,
        "potencial_dcf_escenarios": valor_dcf_escenarios / cotizacion.precio - 1 if valor_dcf_escenarios else None,
        "motor": motor, "wacc_motor": wacc_motor, "origen_prima": origen_prima, "beta_sector": beta_sector,
        "ficha": {"bolsa": bolsa, "cierre_fiscal": cierre_fiscal, "empleados": empleados(texto_negocio)},
        "precio_modelo": precio_modelo,
        "precio_objetivo": precio_objetivo, "potencial": potencial, "potencial_dcf": potencial_dcf, "recomendacion": propuesta,
        "avisos_valoracion": avisos_valoracion, "avisos_emision": avisos_emision, "datos_dcf": datos_dcf,
        "componentes_ev": componentes_ev(ltm, LTM), "metodos": metodos, "bandas": bandas, "historicos": historicos,
        "valor_historicos": valor_historicos, "sotp": sotp, "precios_semanales": precios_semanales or [], "balance_base": balance_base,
        "segmentos": segmentos_dict or {}, "concentracion": concentracion or [], "trimestres": trimestres_lista or [],
        "autonomia": autonomia, "contribucion": desglose_crec, "autoria": autoria, "capital_flotante": capital_flotante,
        "valor_contable_por_accion": (ltm.valor("patrimonio", LTM) / acciones) if ltm.valor("patrimonio", LTM) and acciones else None,
        "rango_dcf": (pesimista, optimista),
        "puente": puente, "apalancamiento": apalancamiento, "uso": uso, "notas": notas,
        "dupont": {**{f"FY{a}": dupont(estados, a) for a in ejercicios[-3:]}, "LTM": dupont(ltm, LTM)},
        "cascada": cascada_ebitda_fcf(estados, ejercicio, f), "vencimientos": vencimientos or {"importes": [], "motivo": ""},
        "puntuaciones": puntuaciones, "gobierno": gobierno, "riesgos_cambios": riesgos_cambios, "insiders": insiders,
        "catalizadores": catalizadores, "filiales": filiales, "gestion": gestion,
        "opciones": mercado_de_opciones(opciones_cadena, cotizacion.precio, series_bolsa.get(ticker)),  # externos (B5)
        "cortos": {**cortos, "lectura": lectura_cortos(cortos.get("sobre_flotante"))} if cortos else None,
        "equipo": _equipo(insiders, series_bolsa.get(ticker)),
        "cambios_direccion": [e for e in (eventos or []) if "5.02" in e["items"] and (date.today() - e["fecha"]).days <= 730],
        "competencia": _competencia(competencia_texto, ticker, f_ltm, fund, ejercicios, comps if comparables_del_analista else [],
                                    wacc_informe),
        "publicaciones": _publicaciones(eventos or [], trimestres_lista or [], series_bolsa.get(ticker)), "alarmas": alarmas or [],
        "riesgos": riesgos, "riesgos_lista": riesgos_lista, "textos": textos,
        "pendientes": [p for t in textos.values() for p in pendientes(t)], "fecha": fecha or date.today().isoformat(),
        "series_bolsa": series_bolsa,
    }
    c["cambios"] = comparar_versiones(anterior, resumen_version(c)) if anterior else None  # R16
    c["historial"] = historial_recomendaciones(historial_resumenes or [], cotizacion.precio,
                                               date.fromisoformat(c["fecha"]))  # R17
    return c


def catalizadores_del_informe(catalizadores: dict | None, base: Estimaciones, avisos_emision: list[str]) -> dict:
    """Calendario y catalizadores (A4): los del analista sustituyen al borrador del SaaS y a la propuesta de la IA."""
    catalizadores = {"calendario": [], "hechos": [], "ia": None, **(catalizadores or {}), "del_analista": bool(base.calendario)}
    if base.calendario:  # el analista manda: sustituye al borrador del SaaS
        catalizadores["calendario"] = base.calendario
    if base.catalizadores:  # y a la propuesta de la IA
        catalizadores["ia"] = {"lista": base.catalizadores, "modelo": None, "candidatos": None}
    elif catalizadores.get("calendario"):
        avisos_emision.append(AVISO_CALENDARIO)
    return catalizadores


def _gestion(parametros, cotizacion, cierres, datos: dict) -> dict | None:
    """Apartados 12, 23 y 24 (B4) con los parámetros del analista; None si no hay ninguno definido."""
    if parametros is None or not parametros.definidos:
        return None
    rend = rendimientos_diarios(cierres)
    sigma = statistics.pstdev(rend) if len(rend) >= 20 else None
    salida = {"parametros": parametros, "criterios": evaluar_criterios(parametros, datos), "volatilidad_diaria": sigma,
              "var": var_historico(rend), "riesgo": None}
    p = parametros
    if sigma and None not in (p.multiplo_volatilidad, p.horizonte_stop_dias, p.capital_cartera, p.riesgo_por_posicion):
        stop = stop_volatilidad(cotizacion.precio, sigma, p.multiplo_volatilidad, p.horizonte_stop_dias, p.perdida_minima_stop,
                                p.perdida_maxima_stop)
        tam = tamano_posicion(p.capital_cartera, p.riesgo_por_posicion, cotizacion.precio, stop["stop"], p.peso_maximo)
        salida["riesgo"] = {**stop, **tam, "dias_para_construir": dias_para_construir(
            tam["acciones"], cotizacion.volumen_medio_acciones_12m, p.participacion_maxima_volumen),
            "frecuencia_stop": frecuencia_stop(cierres, stop["perdida"], p.horizonte_stop_dias)}
    return salida


def _texto_competencia(texto: dict | None) -> str:
    """Markdown del bloque de competencia: la traducción verificada o, si no la hay, el marcador para el analista."""
    if not texto:
        return "[[ANALISTA: el Item 1 del 10-K no tiene un apartado «Competition»: describe la competencia de la empresa]]"
    if texto["valida"]:
        return texto["texto"]
    citado = "\n\n".join(f"> {p}" for p in texto["original"].split("\n\n"))
    return f"[[ANALISTA: traduce o resume el apartado «Competition» del Item 1 ({texto['motivo']})]]\n\n{citado}"


def _competencia(texto: dict | None, ticker: str, f_ltm: dict, fund: dict, ejercicios: list[int], comps: list[dict],
                 wacc: float | None) -> dict:
    """Apartado 14 (A5): texto del 10-K (traducido por la IA si pasó la verificación) y cifras frente a los
    comparables del analista (sin su lista no hay cuotas: la propuesta automática por SIC es solo orientativa)."""
    roic = f_ltm.get("roic")
    estab = [c.get("estabilidad_margen_5a") for c in comps if c.get("estabilidad_margen_5a") is not None]
    roics = [c["fundamentales"].get("roic") for c in comps if c["fundamentales"].get("roic") is not None]
    return {
        "texto": texto,
        "cuotas": cuotas_de_ingresos({ticker: f_ltm.get("ingresos"), **{c["ticker"]: c["fundamentales"].get("ingresos") for c in comps}}),
        "nombres": {c["ticker"]: c["nombre"] for c in comps},
        "roic": roic, "wacc": wacc, "roic_menos_wacc": roic - wacc if roic is not None and wacc is not None else None,
        "roic_mediana": statistics.median(roics) if roics else None,
        "estabilidad": estabilidad_margen([fund[a]["margen_operativo"] for a in ejercicios[-5:]]),
        "estabilidad_mediana": statistics.median(estab) if estab else None,
    }


def _equipo(insiders: dict | None, cierres) -> list[dict]:
    """Apartado 5 (B3): quien presentó Form 4 en 12 meses, con su cargo declarado, su alta como insider (Form 3) y la
    rentabilidad de la acción desde entonces (solo si la serie de cotizaciones llega a esa fecha)."""
    if not insiders:
        return []
    altas = insiders.get("altas") or {}
    return sorted(({"nombre": n, "cargo": cargo, "alta": altas.get(n), "rentabilidad": rentabilidad_desde(cierres, altas.get(n))}
                   for n, cargo in (insiders.get("personas") or {}).items()), key=lambda p: (p["alta"] or date.max))


MAX_PUBLICACIONES = 8


def _publicaciones(eventos: list[dict], trimestres_lista: list[dict], cierres) -> list[dict]:
    """Apartado 21 (A8): cada 8-K de resultados (ítem 2.02) con su trimestre y la reacción a 5 sesiones."""
    salida = []
    for e in [e for e in eventos if "2.02" in e["items"]][-MAX_PUBLICACIONES:]:
        trimestre = next((t for t in sorted(trimestres_lista, key=lambda t: t["fin"], reverse=True)
                          if 0 <= (e["fecha"] - t["fin"]).days <= 100), None)  # el último trimestre cerrado antes del 8-K
        salida.append({**e, "trimestre": trimestre, "reaccion": reaccion_resultados(e["aceptacion"], cierres)})
    return salida


def _insiders(empresa, ticker: str) -> dict:
    """Apartado 18 (A6): Form 4 de 12 meses, accionistas de más del 5 % y participaciones de yfinance (externas)."""
    from ..calculo.insiders import actividad
    from ..ingesta.directivos import altas_como_insider
    from ..ingesta.insiders import accionistas_principales, transacciones
    from ..ingesta.mercado import participaciones

    hoy = date.today()
    tr = transacciones(empresa, hoy)
    return {**tr, "actividad": actividad(tr["operaciones"]), "accionistas": accionistas_principales(empresa, hoy),
            "participaciones": participaciones(ticker), "altas": altas_como_insider(empresa, list(tr["personas"]))}


def construir(ticker: str, con_ia: bool = True, comparables: list[str] | None = None, anterior: dict | None = None,
              historial_resumenes: list[dict] | None = None, estimaciones: Estimaciones | None = None) -> dict:
    """Reúne los datos (SEC, mercado, IA opcional) y compone el informe. Requiere EDGAR_IDENTITY y red."""
    return componer(**reunir(ticker, con_ia, comparables, anterior, historial_resumenes, estimaciones))


def reunir(ticker: str, con_ia: bool = True, comparables: list[str] | None = None, anterior: dict | None = None,
           historial_resumenes: list[dict] | None = None, estimaciones: Estimaciones | None = None) -> dict:
    """Datos del informe (SEC, mercado, IA opcional), listos para `componer`. Requiere EDGAR_IDENTITY y red.

    `comparables`: lista del analista; sin ella, el SaaS propone una por código SIC (marcada «Revisar»).
    `anterior`: resumen del informe anterior (R16). `historial_resumenes`: resúmenes de las versiones emitidas (R17).
    """
    from edgar import Company

    from ..ingesta import comparables as ingesta_comparables
    from ..ingesta.mercado import precios_semanales

    ticker = ticker.upper()
    empresa = Company(ticker)
    cobertura = cobertura_de(ticker)
    if cobertura.plantilla not in (PLANTILLA_GENERAL, PENDIENTE_VALIDAR):  # banca, seguros, REIT y BDC (B2)
        from .sectorial import reunir_sectorial

        return reunir_sectorial(empresa, ticker, cobertura, con_ia, comparables, anterior, historial_resumenes, estimaciones)
    anuales_10k = empresa.get_filings(form="10-K", amendments=False).head(3)
    filing = anuales_10k[0]
    xbrl = filing.xbrl()
    ejercicio = int(xbrl.entity_info["fiscal_year"])
    ejercicios = list(range(ejercicio - ANIOS, ejercicio + 1))  # + 1 año previo para el crecimiento del primero

    facts = empresa.get_facts()
    fuente_anual = FuenteEntityFacts(facts)
    estados = normalizar(fuente_anual, ejercicios, ticker)
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

    # LTM: hasta el cierre del último 10-Q/10-K. La API companyfacts de la SEC tarda a veces semanas en incluir el
    # último 10-Q (KO, XOM: cierre de julio aún ausente en octubre): entonces, el periodo anterior. Si ninguno cuadra
    # (o no hay trimestres, 20-F), el último ejercicio.
    periodicos = empresa.get_filings(form=["10-Q", "10-K"], amendments=False).head(2)
    estados_ltm, fecha_ltm, periodico, incompletos = None, None, None, []
    for p in (p for p in periodicos if p.period_of_report):
        candidata = str(p.period_of_report)
        if date.fromisoformat(candidata) < date.fromisoformat(str(filing.period_of_report)):
            break  # anterior al último 10-K: no aporta nada sobre el anual
        prueba = normalizar(FuenteLTM(facts, date.fromisoformat(candidata)), [LTM_PREVIO, LTM], ticker)
        calidad_ltm = revisar(prueba, [LTM], etiqueta=lambda _, f=candidata: f"LTM a {f}")
        if not calidad_ltm.errores:
            estados_ltm, fecha_ltm, periodico = prueba, candidata, p
            calidad.avisos += calidad_ltm.avisos
            break
        if prueba.valor("ingresos", LTM) is None:
            incompletos.append(f"el periodo cerrado a {candidata} aún no está en la API companyfacts de la SEC")
        else:
            incompletos.append(f"LTM a {candidata} incompleto ({'; '.join(calidad_ltm.errores)})")
    if incompletos:
        destino = f"LTM a {fecha_ltm}" if fecha_ltm else f"FY{ejercicio}"
        calidad.avisos.append(f"{'; '.join(incompletos)}: se usa {destino}")
    acciones, acciones_origen = acciones_en_circulacion(
        facts, date.fromisoformat(fecha_ltm) if fecha_ltm else date.today(),
        (estados_ltm or estados).valor("acciones_diluidas", LTM if estados_ltm else ejercicio))

    del_analista = comparables is not None
    criterio = "lista del analista"
    if not del_analista:
        ingresos_ref = (estados_ltm or estados).valor("ingresos", LTM if estados_ltm else ejercicio)
        comparables, criterio = ingesta_comparables.proponer(empresa.sic, empresa.cik, ingresos_ref, ticker=ticker)
    datos_comparables = [d for d in (ingesta_comparables.datos(t) for t in comparables) if d]

    # Fecha de cierre y de presentación de cada ejercicio: segmentos (R14) y múltiplos sin sesgo de anticipación (R11)
    cierres, disponibles = {}, {}
    for a in estados.ejercicios:
        dato = estados.datos.get("ingresos", {}).get(a)
        if dato:
            cierres[a], disponibles[a] = fuente_anual.presentacion(dato.concepto, a)
    totales = {a: estados.valor("ingresos", a) for a in estados.ejercicios[-ANIOS:] if estados.valor("ingresos", a)}
    xbrls = [(xbrl, filing.accession_no)]
    if len(anuales_10k) > 2:  # cada 10-K trae 3 años: con el de hace dos años se cubren los 5
        try:
            xbrls.append((anuales_10k[2].xbrl(), anuales_10k[2].accession_no))
        except Exception as e:  # noqa: BLE001  (sin el 10-K antiguo, los segmentos cubren 3 años)
            log.warning("XBRL del 10-K de hace dos años no disponible: %s", e)
    desgloses = segmentos(xbrls, totales, cierres)
    if desgloses and periodico is not None and periodico.form == "10-Q" and fecha_ltm and cierres.get(ejercicio):
        try:  # LTM provisional por segmento (F7): último ejercicio + acumulados del 10-Q
            segmentos_ltm(desgloses, periodico.xbrl(), periodico.accession_no, ejercicio, cierres[ejercicio],
                          date.fromisoformat(fecha_ltm), estados_ltm.valor("ingresos", LTM))
        except Exception as e:  # noqa: BLE001  (sin XBRL del 10-Q: los segmentos se quedan sin columna LTM)
            log.warning("Segmentos LTM no disponibles: %s", e)
    lista_trimestres = trimestres(facts, date.fromisoformat(fecha_ltm)) if fecha_ltm else []
    venc = vencimientos_deuda(fuente_anual, ejercicio)
    comunes = _comunes(empresa, ticker, filing, xbrl, ejercicio, con_ia, facts,
                       date.fromisoformat(fecha_ltm) if fecha_ltm else cierres.get(ejercicio), cierres.get(ejercicio),
                       venc["importes"][0] if venc.get("importes") else None)
    datos = dict(  # argumentos de `componer`: la interfaz los guarda y recompone el informe sin red al editar (A12)
        **comunes, cobertura=cobertura, estimaciones=estimaciones,
        filing={"accession": filing.accession_no, "fecha": str(filing.filing_date), "ejercicio": ejercicio,
                "cierre": str(cierres.get(ejercicio) or filing.period_of_report),  # cierre del ejercicio (motor de valoración)
                "ultimo_periodico": periodico.accession_no if periodico is not None else None,
                "ultimo_periodico_formulario": periodico.form if periodico is not None else None},
        estados=estados, calidad=calidad, acciones=acciones,
        estados_ltm=estados_ltm, fecha_ltm=fecha_ltm, comparables=datos_comparables,
        comparables_criterio=criterio, comparables_del_analista=del_analista,
        acciones_origen=acciones_origen, trimestres_lista=lista_trimestres, segmentos_dict=desgloses,
        concentracion=concentracion_clientes(xbrl, cierres), vencimientos=venc,
        precios_semanales=precios_semanales(ticker), fechas_disponibles=disponibles, anterior=anterior,
        historial_resumenes=historial_resumenes,
    )
    return con_borradores_ia(datos, con_ia)


def con_borradores_ia(datos: dict, con_ia: bool) -> dict:
    """Borradores de la IA para los apartados del analista, sobre lo que ya dice el informe (los revisa el analista)."""
    if con_ia:
        from ..ia.borradores import contexto, generar

        borrador = componer(**datos)
        instrucciones = [m.strip() for texto in borrador["textos"].values() for m in MARCADOR.findall(texto)]
        datos["borradores_ia"] = generar(instrucciones, contexto(borrador, datos["texto_negocio"]))
    return datos


def _comunes(empresa, ticker: str, filing, xbrl, ejercicio: int, con_ia: bool, facts, cierre_periodo, cierre_ejercicio,
             vencimiento_proximo) -> dict:
    """Argumentos de `componer` que no dependen de la plantilla (general o sectorial): 8-K, Item 1, 1A y 7 del 10-K
    (con los bloques de IA), gobierno, insiders, mercado, opciones y cortos, autoría y parámetros del fondo."""
    from ..calculo.calendario import borrador as borrador_calendario
    from ..ingesta.competencia import apartado_competencia
    from ..ingesta.damodaran import beta_sectorial
    from ..ingesta.derivados import cadena_opciones, posiciones_cortas
    from ..ingesta.directivos import filiales as filiales_10k
    from ..ingesta.eventos import ANIOS_ALARMAS, categoria_presentador, eventos_8k, hechos_relevantes
    from ..ingesta.eventos import alarmas as alarmas_sec
    from ..ingesta.ficha import bolsa as bolsa_de
    from ..ingesta.ficha import cierre_fiscal
    from ..ingesta.gobierno import gobierno as datos_gobierno
    from ..ingesta.mercado import INDICE, comportamiento, cotizacion, etf_sectorial, historico, prima_riesgo, tipo_libre_riesgo
    from ..ingesta.nombres import nombre_legible
    from ..ingesta.riesgos import comparar_riesgos, riesgos_anteriores, riesgos_anuales
    from .autoria import cargar as cargar_autoria
    from .parametros import cargar as cargar_parametros

    with _silencio_edgar():
        flotante = (facts.public_float, getattr(facts.public_float_fact, "period_end", None))
    eventos = eventos_8k(empresa, date.today() - timedelta(days=365 * ANIOS_ALARMAS))
    tenk = filing.obj()
    texto_negocio = tenk.business or ""
    hoy = date.today()
    catalizadores = {
        "calendario": borrador_calendario(
            hoy, [e["fecha"] for e in eventos if "2.02" in e["items"]], [e["fecha"] for e in eventos if "5.07" in e["items"]],
            cierre_periodo, cierre_ejercicio, categoria_presentador(xbrl), vencimiento_proximo, ejercicio),
        "hechos": hechos_relevantes(eventos, hoy), "ia": None}
    if con_ia and (tenk.management_discussion or ""):  # bloque de IA del MD&A: elige y resume frases literales
        from ..ia.bloques import catalizadores as catalizadores_ia

        try:
            elegidos, cfg, candidatos = catalizadores_ia(tenk.management_discussion)
            catalizadores["ia"] = {"lista": [{"resumen": s.resumen, "cita": s.cita} for s in elegidos],
                                   "modelo": f"{cfg.proveedor} · {cfg.modelo}", "candidatos": candidatos}
        except Exception as e:  # noqa: BLE001  (sin modelo: el bloque queda para el analista)
            log.warning("Catalizadores del MD&A sin IA: %s", e)
    competencia_texto = None
    literal = apartado_competencia(texto_negocio)
    if literal:  # A5: tercer bloque de IA, solo traduce el texto literal; sin IA, el original para el analista
        competencia_texto = {"original": literal["texto"], "texto": literal["texto"], "valida": False, "recortado": literal["recortado"],
                             "motivo": "sin modelo de lenguaje (--sin-ia)", "modelo": None}
        if con_ia:
            from ..ia.bloques import competencia_en_espanol

            tr, cfg = competencia_en_espanol(literal["texto"])
            competencia_texto.update(texto=tr.texto, valida=tr.valida, motivo=tr.motivo,
                                     modelo=f"{cfg.proveedor} · {cfg.modelo}" if cfg else None)
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
    return dict(
        ticker=ticker, empresa=nombre_legible(empresa.name), sic=empresa.sic, cotizacion=cotizacion(ticker),
        beta_estimada=_beta_semanal(ticker), comportamiento=comportamiento(ticker, empresa.sic),
        series_bolsa=_series_bolsa(ticker, etf_sectorial(empresa.sic), historico, INDICE),
        riesgos=riesgos, riesgos_lista=riesgos_lista, texto_negocio=texto_negocio, competencia_texto=competencia_texto,
        rf=tipo_libre_riesgo(), prima=prima_riesgo(), beta_sector=beta_sectorial(ticker), gobierno=datos_gobierno(empresa, xbrl),
        bolsa=bolsa_de(empresa), cierre_fiscal=cierre_fiscal(cierre_ejercicio),  # P6: ficha de empresa
        insiders=_insiders(empresa, ticker), eventos=eventos, alarmas=alarmas_sec(empresa, date.today(), filing, eventos),
        riesgos_cambios=cambios, catalizadores=catalizadores, filiales=filiales_10k(tenk),
        opciones_cadena=cadena_opciones(ticker), cortos=posiciones_cortas(ticker),
        autoria=cargar_autoria(), parametros=cargar_parametros(), capital_flotante=flotante if flotante[0] else None,
    )
