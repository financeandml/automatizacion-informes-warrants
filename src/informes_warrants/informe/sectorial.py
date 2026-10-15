"""Informe de las plantillas sectoriales (B2): banca, seguros, REIT y BDC/fondos cerrados.

Misma maquetación y apartados 01-06 que la plantilla general (piezas compartidas de plantillas/informe/), con las
métricas del perfil (calculo/perfiles.py, calculo/sectoriales.py) y su valoración (calculo/valoracion_sectorial.py):
sin EBITDA, EV, FCF ni DCF de FCFF, que en estos sectores no tienen sentido (perfil `no_aplica`).

Qué se reutiliza tal cual de la plantilla general: la ingesta común (`construir._comunes`: 8-K, Items 1, 1A y 7 con
sus bloques de IA, gobierno, insiders, mercado, opciones y cortos, autoría y parámetros del fondo), los borradores
de la IA, el calendario y los catalizadores, la gestión de la posición (B4), los hechos clave
(`calculo/hechos_clave.seleccionar`), la síntesis del precio objetivo (`calculo/sintesis`), la recomendación por
potencial, el historial (R17) y la comparación con la versión anterior (R16).

Periodo de las cifras: LTM hasta el último 10-Q si cuadra (flujos de 4 trimestres y saldos al cierre, como en la
general); si no, el último ejercicio, con aviso en el semáforo.
"""

import logging
import math
from dataclasses import replace
from datetime import date

from ..calculo.calidad import Informe as Calidad
from ..calculo.hechos_clave import observaciones_sectoriales, seleccionar
from ..calculo.historial import historial as historial_recomendaciones
from ..calculo.insiders import participacion_institucional
from ..calculo.metricas import Mercado, cagr
from ..calculo.normalizador import LTM, FuenteEntityFacts, FuenteLTM, FuenteXBRL, acciones_en_circulacion
from ..calculo.perfiles import IMPORTES, NOMBRES_ENTRADAS, PERFILES_SECTORIALES, POR_ACCION, VECES, Perfil
from ..calculo.sectoriales import calcular
from ..calculo.sintesis import Metodo, sintetizar
from ..calculo.valoracion_sectorial import (
    COMPARABLES,
    DIVIDENDOS,
    G_POR_DEFECTO,
    METODOS,
    MULTIPLO_PRINCIPAL,
    PESOS_POR_DEFECTO,
    RENTABILIDAD,
    VALOR_CONTABLE,
    multiplos,
    patrimonio_comun,
    potencial,
    rentabilidad_del_ciclo,
    valorar,
)
from ..calculo.valoracion_sectorial import NOMBRES as NOMBRES_MULTIPLOS
from ..ingesta.ficha import empleados
from .cambios import comparar as comparar_versiones
from .cambios import resumen as resumen_version
from .construir import (
    ANIOS,
    AVISO_COMPARABLES,
    AVISO_PARAMETROS,
    MESES,
    _cita_negocio,
    _comunes,
    _equipo,
    _gestion,
    _limitar,
    _texto_competencia,
    catalizadores_del_informe,
    con_borradores_ia,
)
from .estimaciones import Estimaciones, recomendacion_propuesta
from .plantillas import _num, _pct, con_borradores, pendientes, rellenar
from .secciones import BLOQUES, Tipo

log = logging.getLogger(__name__)
ACCIONES_DILUIDAS = "WeightedAverageNumberOfDilutedSharesOutstanding"  # respaldo de las acciones en circulación
PLANTILLAS = {b: f"sectorial/{a}.md.j2" for b, a in (
    ("portada.titulares", "titulares"), ("portada.recomendacion", "recomendacion"), ("conclusiones.hechos_clave", "hechos_clave"),
    ("conclusiones.situacion", "situacion"), ("conclusiones.perspectivas", "perspectivas"), ("financiero.comentario", "financiero"),
    ("valoracion.comentario", "valoracion"))}
# Presentación de cada perfil: base del múltiplo principal, rentabilidad del valor contable justificado, la métrica de
# la situación actual, las de la portada y lo que el analista debe valorar en las perspectivas.
BASE_NOMBRE = {"banco": "su valor contable tangible", "aseguradora": "su valor contable", "reit": "su FFO", "inversion": "su NAV"}
NOMBRE_RENTABILIDAD = {"banco": "ROTE", "aseguradora": "ROE", "inversion": "ROE"}
CLAVE_SITUACION = {"banco": "rote", "aseguradora": "roe", "reit": "ffo", "inversion": "nav_por_accion"}
CLAVES_PORTADA = {"banco": ("rote", "eficiencia", "nim"), "aseguradora": ("roe", "combinado", "rendimiento_inversiones"),
                  "reit": ("ffo", "payout_ffo", "ltv"), "inversion": ("nav_por_accion", "cobertura_dividendo", "apalancamiento")}
PERSPECTIVAS = {"banco": "el margen de intereses, la eficiencia, el coste del riesgo y el ROTE",
                "aseguradora": "las primas, el ratio combinado, los ingresos de las inversiones y el ROE",
                "reit": "la ocupación, las rentas, el FFO, el dividendo y el endeudamiento (LTV)",
                "inversion": "el NAV por acción, el ingreso neto de inversiones, la cobertura del dividendo y el apalancamiento"}


def perfil_por_id(perfil_id: str) -> Perfil:
    return next(p for p in PERFILES_SECTORIALES if p.id == perfil_id)


def _valor(x) -> float | None:
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else x


def formato_metrica(metrica_id: str, valor, unidades: bool = True) -> str:
    """Una métrica del perfil con su unidad: % (ratios), USD Mn (importes), USD (por acción) o veces."""
    valor = _valor(valor)
    if valor is None:
        return "n.d."
    if metrica_id in IMPORTES:
        return _num(valor / 1e6, 0) + (" USD Mn" if unidades else "")
    if metrica_id in POR_ACCION:
        return _num(valor, 2) + (" USD" if unidades else "")
    if metrica_id in VECES:
        return _num(valor, 2) + "x"
    return _pct(valor)


def nombre_en_texto(metrica) -> str:
    return metrica.nombre.replace(" (USD)", "")


def etiqueta_periodo(fecha_ltm: str | None, ejercicio: int) -> str:
    if not fecha_ltm:
        return f"FY{ejercicio}"
    d = date.fromisoformat(fecha_ltm)
    return f"LTM {MESES[d.month - 1]}-{d.year % 100:02d}"


def estimaciones_sectoriales(estimaciones: Estimaciones | None, perfil_id: str, rf, beta_estimada: float) -> Estimaciones:
    """Supuestos del perfil: Rf de mercado, β estimada y los pesos de sus métodos (los del DCF no se usan)."""
    pesos = {n: PESOS_POR_DEFECTO[n] for n in METODOS[perfil_id]}
    if estimaciones is None:
        base = Estimaciones()
        return replace(base, rf=round(rf.valor, 4) if rf else base.rf, beta=round(_limitar(beta_estimada, 0.3, 3.0), 2), pesos=pesos,
                       g=G_POR_DEFECTO.get(perfil_id, base.g))
    if set(estimaciones.pesos) != set(pesos):  # pesos de la plantilla general: los del perfil, con los del analista que coincidan
        return replace(estimaciones, pesos={n: estimaciones.pesos.get(n, peso) for n, peso in pesos.items()})
    return estimaciones


def _comparable(ticker: str, perfil: Perfil) -> dict | None:
    """Métricas del último ejercicio y múltiplos de hoy de un comparable con el mismo perfil (None si faltan datos)."""
    from edgar import Company

    from ..ingesta.mercado import cotizacion
    from ..ingesta.nombres import nombre_legible

    try:
        empresa = Company(ticker)
        facts = empresa.get_facts()
        fuente = FuenteEntityFacts(facts)
        r = calcular(perfil, fuente)
        acciones, _ = acciones_en_circulacion(facts, date.today(), fuente.hecho(ACCIONES_DILUIDAS, r.ejercicio))
        valores = {k: d.valor for k, d in r.datos.items()}
        precio = cotizacion(ticker).precio
        return {"ticker": ticker, "nombre": nombre_legible(empresa.name), "ejercicio": r.ejercicio, "metricas": dict(r.metricas),
                "multiplos": multiplos(perfil.id, precio, acciones, valores, r.metricas),
                # libro del motor (hoja Comps): datos de partida de cada múltiplo
                "precio": precio, "acciones": acciones, "valores": valores}
    except Exception as e:  # noqa: BLE001  (un comparable sin datos no impide el informe)
        log.warning("Comparable %s sin datos: %s", ticker, e)
        return None


def _calidad(perfil: Perfil, historico: dict, ejercicio: int, xbrl, accession: str) -> Calidad:
    """Semáforo del perfil: sin métricas esenciales del último ejercicio o si companyfacts y el 10-K no cuadran, rojo."""
    calidad = Calidad()
    for a, r in sorted(historico.items()):
        sin_esenciales = [m.nombre for m in perfil.metricas if m.esencial and math.isnan(r.metricas[m.id])]
        if sin_esenciales:
            texto = (f"FY{a}: sin {', '.join(sin_esenciales)} (faltan: "
                     f"{', '.join(NOMBRES_ENTRADAS[f].lower() for f in r.faltan) or 'partidas'})")
            (calidad.errores if a == ejercicio else calidad.avisos).append(texto)
    secundarias = [m.nombre for m in perfil.metricas if m.id in historico[ejercicio].para_el_analista]
    if secundarias:
        calidad.avisos.append(f"FY{ejercicio}: {', '.join(secundarias)} n.d. (la empresa no los declara en XBRL estándar)")
    del_10k = FuenteXBRL(xbrl, accession)
    for clave in ("beneficio", "patrimonio", "activos"):  # contraste entre fuentes, como en la plantilla general
        d = historico[ejercicio].datos.get(clave)
        b = del_10k.hecho(d.concepto, ejercicio) if d and d.concepto else None
        if b is not None and abs(d.valor - b) > 0.005 * max(abs(d.valor), abs(b)):
            calidad.errores.append(f"FY{ejercicio}: {NOMBRES_ENTRADAS[clave].lower()} difiere entre companyfacts ({d.valor:,.0f}) "
                                   f"y el 10-K ({b:,.0f})")
    return calidad


def reunir_sectorial(empresa, ticker: str, cobertura, con_ia: bool = True, comparables: list[str] | None = None,
                     anterior: dict | None = None, historial_resumenes: list[dict] | None = None,
                     estimaciones: Estimaciones | None = None) -> dict:
    """Argumentos de `componer` (con `perfil`) para una empresa de un perfil sectorial. Requiere EDGAR_IDENTITY y red."""
    from ..ingesta.mercado import precios_semanales

    perfil = perfil_por_id(cobertura.plantilla)
    filing = empresa.get_filings(form="10-K", amendments=False).latest()
    xbrl = filing.xbrl()
    ejercicio = int(xbrl.entity_info["fiscal_year"])
    facts = empresa.get_facts()
    fuente = FuenteEntityFacts(facts)
    historico = {}
    for a in range(ejercicio - ANIOS + 1, ejercicio + 1):
        r = calcular(perfil, fuente, a)
        if "beneficio" in r.datos and "patrimonio" in r.datos:  # sin estados ese año: falta de historial, no error
            historico[a] = r
    if ejercicio not in historico:
        raise ValueError(f"{ticker}: el XBRL de FY{ejercicio} no trae beneficio neto ni patrimonio para el perfil «{perfil.nombre}».")
    calidad = _calidad(perfil, historico, ejercicio, xbrl, filing.accession_no)

    # LTM hasta el último 10-Q (si la API companyfacts ya lo incluye y las métricas esenciales cuadran); si no, el anual
    cierre = date.fromisoformat(str(filing.period_of_report))
    ltm, fecha_ltm, periodico, incompletos = None, None, None, []
    for p in empresa.get_filings(form=["10-Q", "10-K"], amendments=False).head(2):
        fecha = date.fromisoformat(str(p.period_of_report)) if p.period_of_report else None
        if fecha is None or fecha <= cierre:
            break
        candidato = calcular(perfil, FuenteLTM(facts, fecha), LTM)
        if candidato.completo:
            ltm, fecha_ltm, periodico = candidato, fecha.isoformat(), p
            break
        incompletos.append(f"LTM a {fecha} incompleto (faltan: {', '.join(NOMBRES_ENTRADAS[f].lower() for f in candidato.faltan)})")
    if incompletos:
        calidad.avisos.append(f"{'; '.join(incompletos)}: se usa {'LTM a ' + fecha_ltm if fecha_ltm else f'FY{ejercicio}'}")
    acciones, acciones_origen = acciones_en_circulacion(facts, date.fromisoformat(fecha_ltm) if fecha_ltm else date.today(),
                                                        fuente.hecho(ACCIONES_DILUIDAS, ejercicio))

    del_analista = comparables is not None
    lista = comparables if del_analista else [t for t in perfil.referencias if t != ticker]
    criterio = ("lista del analista" if del_analista
                else f"empresas de referencia del perfil «{perfil.nombre}» ({', '.join(lista)}), propuesta orientativa")
    datos = dict(
        **_comunes(empresa, ticker, filing, xbrl, ejercicio, con_ia, facts, date.fromisoformat(fecha_ltm) if fecha_ltm else cierre,
                   cierre, None),
        perfil=perfil.id, cobertura=cobertura, estimaciones=estimaciones,
        filing={"accession": filing.accession_no, "fecha": str(filing.filing_date), "ejercicio": ejercicio,
                "ultimo_periodico": periodico.accession_no if periodico is not None else None,
                "ultimo_periodico_formulario": periodico.form if periodico is not None else None},
        historico=historico, ltm=ltm, fecha_ltm=fecha_ltm, calidad=calidad, acciones=acciones, acciones_origen=acciones_origen,
        comparables=[d for d in (_comparable(t, perfil) for t in lista) if d], comparables_criterio=criterio,
        comparables_del_analista=del_analista, precios_semanales=precios_semanales(ticker), anterior=anterior,
        historial_resumenes=historial_resumenes,
    )
    return con_borradores_ia(datos, con_ia)


def _supuesto(nombre: str, m: dict, perfil_id: str, origen: str) -> str:
    if nombre == VALOR_CONTABLE:
        if m["rentabilidad"] is None:
            return "Sin rentabilidad declarada"
        texto = f"{NOMBRE_RENTABILIDAD[perfil_id]} sostenible {_pct(m['rentabilidad'])} ({origen})"
        return f"{texto} → {_num(m['multiplo_justo'], 2)}x; rango Ke ± 1 pp" if m["multiplo_justo"] else f"{texto} ≤ g: sin valor"
    if nombre == DIVIDENDOS:
        return f"DPA {_num(m['dpa'], 2)} USD; rango Ke ± 1 pp" if m.get("dpa") else "Sin dividendo declarado"
    if m.get("valor") is not None:
        return f"Mediana {NOMBRES_MULTIPLOS[m['multiplo']]} de la lista del analista ({m['n']}); rango P25-P75"
    return "Falta la lista del analista"


def componer_sectorial(*, ticker: str, empresa: str, sic, cobertura, perfil: str, filing: dict, historico: dict, ltm,
                       fecha_ltm: str | None, calidad, cotizacion, acciones: float, acciones_origen: str, beta_estimada: float,
                       comportamiento: dict, series_bolsa: dict, riesgos: list, riesgos_lista: list, texto_negocio: str,
                       competencia_texto: dict | None, rf, gobierno, insiders: dict | None, eventos: list | None, alarmas: list | None,
                       riesgos_cambios: dict | None, catalizadores: dict | None, filiales: dict | None, opciones_cadena: dict | None,
                       cortos: dict | None, autoria, parametros, capital_flotante: tuple | None, comparables: list[dict] | None,
                       comparables_criterio: str = "", comparables_del_analista: bool = False, precios_semanales: list | None = None,
                       estimaciones: Estimaciones | None = None, escenarios=None, borradores_ia: dict | None = None,
                       anterior: dict | None = None, historial_resumenes: list | None = None, fecha: str | None = None,
                       prima=None, beta_sector=None, bolsa: str | None = None, cierre_fiscal: str | None = None,
                       consenso: dict | None = None) -> dict:
    """Parte pura (sin red) de la plantilla sectorial: de los datos reunidos al contexto del informe.

    `escenarios` se acepta por compatibilidad con la interfaz y no se usa: el perfil no tiene DCF."""
    from ..calculo.derivados import lectura_cortos, mercado_de_opciones
    from ..ingesta.mercado import etf_sectorial

    p = perfil_por_id(perfil)
    ejercicios = sorted(historico)
    ejercicio = filing["ejercicio"]
    ultimo, inicial = historico[ejercicio], historico[ejercicios[0]]
    r = ltm or ultimo  # periodo de las cifras del informe
    periodo = etiqueta_periodo(fecha_ltm, ejercicio)
    base = estimaciones_sectoriales(estimaciones, p.id, rf, beta_estimada)
    if estimaciones is None and prima is not None:  # prima de riesgo semanal (D7): la propone el SaaS, el analista la confirma
        base = replace(base, erp=round(prima.valor, 4))
    if errores := base.validar():
        raise ValueError("Estimaciones no válidas: " + " ".join(errores))
    ke, g = base.coste_equity(), base.g
    valores = {k: d.valor for k, d in r.datos.items()}
    clave_rentabilidad = RENTABILIDAD.get(p.id)
    if base.rentabilidad_sostenible is not None:
        sostenible, origen = base.rentabilidad_sostenible, "del analista"
    else:  # a lo largo del ciclo: la media de los ejercicios del informe
        sostenible = rentabilidad_del_ciclo([historico[a].metricas[clave_rentabilidad] for a in ejercicios]) if clave_rentabilidad else None
        origen = f"media FY{ejercicios[0]}-FY{ejercicio}"
    val = valorar(p.id, cotizacion.precio, acciones, valores, r.metricas, ke, g, comparables or [], comparables_del_analista,
                  sostenible)
    precio_modelo, metodos = sintetizar([Metodo(n, m["valor"], m["bajo"], m["alto"], _supuesto(n, m, p.id, origen), base.pesos.get(n, 0.0))
                                         for n, m in ((n, val["metodos"][n]) for n in METODOS[p.id])])
    precio_objetivo = base.precio_objetivo_analista or precio_modelo  # el del analista prevalece si lo fija
    pot = potencial(precio_objetivo, cotizacion.precio)
    propuesta = recomendacion_propuesta(pot) if pot is not None else "Pendiente"
    avisos_emision = [] if comparables_del_analista else [AVISO_COMPARABLES]
    catalizadores = catalizadores_del_informe(catalizadores, base, avisos_emision)
    # Libro del motor (D4): la valoración B2 con fórmulas vivas y la hoja de comparables de la plantilla; se contrasta con val
    from ..calculo.motor.sectorial import construir as libro_sectorial
    try:
        motor = {"modelo": libro_sectorial(p, historico, ltm, empresa, ticker, date.fromisoformat(str(cotizacion.fecha)[:10]),
                                           cotizacion.precio, acciones, base.rf, base.erp, base.beta, g, sostenible, origen,
                                           comparables or [], comparables_del_analista, val, base.pesos, METODOS[p.id],
                                           NOMBRES_MULTIPLOS[MULTIPLO_PRINCIPAL[p.id]], BASE_NOMBRE[p.id])}
        avisos_emision += motor["modelo"].avisos
    except Exception as e:  # noqa: BLE001  (el libro nunca impide el informe)
        log.warning("Libro del motor sectorial no disponible: %s", e)
        motor = {"error": str(e)}
        avisos_emision.append(f"Motor de valoración: libro sectorial no disponible ({e})")
    gestion = _gestion(parametros, cotizacion, series_bolsa.get(ticker), {"potencial": pot, "per": val["multiplos"]["per"]})
    if gestion is None:
        avisos_emision.append(AVISO_PARAMETROS)

    vcj = val["metodos"].get(VALOR_CONTABLE)
    es_dividendo = p.id in ("reit", "inversion")
    hechos = seleccionar(observaciones_sectoriales({
        "potencial": pot, "precio_objetivo": precio_objetivo, "recomendacion": propuesta, "alarmas": alarmas or [],
        "compras_agrupadas": (insiders or {}).get("actividad", {}).get("agrupadas"), "diferencial": val["diferencial"],
        "rentabilidad": val["rentabilidad"], "rentabilidad_nombre": NOMBRE_RENTABILIDAD.get(p.id), "ke": ke,
        "prima": val["prima_sobre_justo"], "multiplo": val["multiplo_principal"], "multiplo_justo": vcj["multiplo_justo"] if vcj else None,
        "base_nombre": BASE_NOMBRE[p.id],
        "rentabilidad_dividendo": val["multiplos"]["rentabilidad_dividendo"] if es_dividendo else None,
        "payout_ffo": _valor(r.metricas.get("payout_ffo")), "cobertura_dividendo": _valor(r.metricas.get("cobertura_dividendo"))}))

    def dato(resultado, clave):
        d = resultado.datos.get(clave)
        return d.valor if d else None

    por_id = {m.id: m for m in p.metricas}
    clave = por_id[CLAVE_SITUACION[p.id]]
    anios = ejercicio - ejercicios[0]
    datos = {
        "empresa": empresa, "ticker": ticker, "periodo": periodo, "perfil_nombre": p.nombre, "ejercicio": f"FY{ejercicio}",
        "hechos": hechos, "multiplo_principal": val["multiplo_principal"], "base_nombre": BASE_NOMBRE[p.id],
        "metricas_clave": [{"nombre": nombre_en_texto(por_id[k]), "valor": formato_metrica(k, r.metricas[k])}
                           for k in CLAVES_PORTADA[p.id]],
        "recomendacion_propuesta": propuesta, "precio_objetivo": precio_objetivo, "precio": cotizacion.precio, "potencial": pot,
        "origen_precio": "analista" if base.precio_objetivo_analista else
        (" y ".join(m.nombre.lower() for m in metodos if m.peso_efectivo) or "sin método con valor"),
        "anio_ini": f"FY{ejercicios[0]}", "anio_fin": f"FY{ejercicio}",
        "beneficio_ini": dato(inicial, "beneficio") / 1e6, "beneficio_fin": dato(ultimo, "beneficio") / 1e6,
        "cagr_beneficio": cagr(dato(inicial, "beneficio"), dato(ultimo, "beneficio"), anios),
        "patrimonio_ini": dato(inicial, "patrimonio") / 1e6, "patrimonio_fin": dato(ultimo, "patrimonio") / 1e6,
        "cagr_patrimonio": cagr(dato(inicial, "patrimonio"), dato(ultimo, "patrimonio"), anios),
        "clave_nombre": nombre_en_texto(clave), "clave_ini": formato_metrica(clave.id, inicial.metricas[clave.id]),
        "clave_fin": formato_metrica(clave.id, r.metricas[clave.id]), "claves_perspectivas": PERSPECTIVAS[p.id],
        "evolucion": [{"nombre": nombre_en_texto(m), "inicio": formato_metrica(m.id, inicial.metricas[m.id]),
                       "fin": formato_metrica(m.id, r.metricas[m.id])} for m in p.metricas],
        "para_el_analista": [nombre_en_texto(por_id[m]).lower() for m in r.para_el_analista],
        "ke": ke, "rf": base.rf, "beta": base.beta, "erp": base.erp, "g": g, "rentabilidad_nombre": NOMBRE_RENTABILIDAD.get(p.id, ""),
        "vcj": vcj, "origen_rentabilidad": origen, "base_vcj": BASE_NOMBRE[p.id],
        "multiplo_vcj": val["multiplo_principal"] if vcj else None,
        "ddm": val["metodos"].get(DIVIDENDOS), "comps": val["metodos"][COMPARABLES],
        "comps_nombre": NOMBRES_MULTIPLOS[MULTIPLO_PRINCIPAL[p.id]], "precio_modelo": precio_modelo,
        "potencial_modelo": potencial(precio_modelo, cotizacion.precio),
        # Bloques con la plantilla general: descripción, fortalezas y riesgos, gobierno, pipeline, posicionamiento y mercado
        "cita_negocio": _cita_negocio(texto_negocio)
        or "[[ANALISTA: describe el negocio (el 10-K no tiene un párrafo descriptivo extraíble)]]",
        "segmentos": [], "riesgos": riesgos or [{"resumen": "[[ANALISTA: resume los riesgos principales del Item 1A]]", "cita": "—"}],
        "auditor": (gobierno.auditor if gobierno and gobierno.auditor else "[[ANALISTA: auditor (Item 9 / proxy)]]"),
        "gobierno": gobierno, "es_biotecnologia": False,
    }
    textos = {b.id: rellenar(b.id, datos, PLANTILLAS.get(b.id)) for b in BLOQUES if b.tipo in (Tipo.PLANTILLA, Tipo.ANALISTA)}
    textos["negocio.competencia"] = _texto_competencia(competencia_texto)
    if borradores_ia:  # borrador de la IA en cada apartado del analista que lo tiene (lo revisa el analista)
        textos = {k: con_borradores(v, borradores_ia) for k, v in textos.items()}
    c = {
        "ticker": ticker, "empresa": empresa, "sic": sic, "etf": etf_sectorial(sic), "cobertura": cobertura, "filing": filing,
        "perfil": p.id, "perfil_def": p, "calidad": calidad, "cotizacion": cotizacion,
        "mercado": Mercado(cotizacion.precio, acciones, cotizacion.fecha), "multiplos": val["multiplos"], "valoracion": val,
        "beta": beta_estimada, "historico": historico, "ltm": ltm, "periodo": periodo, "resultado_periodo": r,
        "ejercicios": ejercicios, "fecha_ltm": fecha_ltm, "rf": rf, "acciones_origen": acciones_origen,
        # Sin DCF ni proyección en el perfil (las claves existen para la interfaz y las versiones)
        "estimaciones": base, "escenarios": None, "dcf": None, "dcf_escenarios": None, "datos_dcf": None, "fund_ltm": {},
        "etiquetas_estimadas": [], "valor_dcf": None, "rango_dcf": (None, None),
        "valor_multiplos": val["metodos"][COMPARABLES]["valor"], "metodos": metodos, "precio_modelo": precio_modelo,
        "precio_objetivo": precio_objetivo, "potencial": pot, "recomendacion": propuesta,
        "avisos_valoracion": [], "avisos_emision": avisos_emision,
        "comparables": comparables or [], "comparables_criterio": comparables_criterio,
        "comparables_del_analista": comparables_del_analista,
        "valor_contable_por_accion": patrimonio_comun(valores) / acciones if patrimonio_comun(valores) and acciones else None,
        "capital_flotante": capital_flotante, "comportamiento": comportamiento, "autoria": autoria, "gestion": gestion,
        "catalizadores": catalizadores, "filiales": filiales, "equipo": _equipo(insiders, series_bolsa.get(ticker)),
        "cambios_direccion": [e for e in (eventos or []) if "5.02" in e["items"] and (date.today() - e["fecha"]).days <= 730],
        "insiders": insiders, "gobierno": gobierno, "cita_negocio": datos["cita_negocio"], "hechos": hechos,
        "institucionales": participacion_institucional((insiders or {}).get("trece_f"), acciones),
        "competencia": {"texto": competencia_texto, "cuotas": {}, "nombres": {}, "roic": None, "wacc": None, "roic_menos_wacc": None,
                        "roic_mediana": None, "estabilidad": None, "estabilidad_mediana": None},
        "riesgos": riesgos, "riesgos_lista": riesgos_lista, "riesgos_cambios": riesgos_cambios, "puntuaciones": [],
        "alarmas": alarmas or [], "autonomia": None,
        "opciones": mercado_de_opciones(opciones_cadena, cotizacion.precio, series_bolsa.get(ticker)),  # externos (B5)
        "cortos": {**cortos, "lectura": lectura_cortos(cortos.get("sobre_flotante"))} if cortos else None,
        "motor": motor, "beta_sector": beta_sector,
        "ficha": {"bolsa": bolsa, "cierre_fiscal": cierre_fiscal, "empleados": empleados(texto_negocio)}, "consenso": consenso,
        "origen_prima": (f"{prima.fuente}{', ' + prima.fecha if prima.fecha else ''}" if prima is not None
                                         else "Estimaciones del informe"),
        "textos": textos, "pendientes": [x for t in textos.values() for x in pendientes(t)],
        "fecha": fecha or date.today().isoformat(), "series_bolsa": series_bolsa, "precios_semanales": precios_semanales or [],
    }
    c["cambios"] = comparar_versiones(anterior, resumen_version(c)) if anterior else None  # R16
    from .tesis import cifras_sectoriales

    c["rentabilidad_sostenible"] = sostenible
    c["tesis_cifras"] = cifras_sectoriales(c)  # P8: apartado 22
    c["historial"] = historial_recomendaciones(historial_resumenes or [], cotizacion.precio, date.fromisoformat(c["fecha"]))  # R17
    return c
