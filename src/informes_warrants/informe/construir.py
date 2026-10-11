"""Ensamblado de los datos de un informe (plantilla general) a partir de un ticker.

Orden: SEC (normalizador, 5 ejercicios) → contraste con el XBRL del último 10-K → semáforo de calidad
→ mercado → estimaciones por defecto (medias históricas) → DCF → recomendación propuesta → riesgos
(lista literal + selección de IA opcional) → textos de las plantillas. Todas las cifras salen del
motor matemático (calculo/); la IA solo elige y resume títulos literales del 10-K.
"""

import re
import statistics
from dataclasses import asdict
from datetime import date

from ..calculo.calidad import revisar
from ..calculo.dcf import beta, dcf
from ..calculo.metricas import Mercado, cagr, fundamentales, valoracion
from ..calculo.normalizador import FuenteEntityFacts, FuenteXBRL, normalizar
from .cobertura import cobertura_de
from .estimaciones import Estimaciones, recomendacion_propuesta
from .plantillas import pendientes, rellenar
from .secciones import BLOQUES, Tipo

ANIOS = 5
PARTIDAS_CONTRASTE = ("ingresos", "resultado_operativo", "beneficio_neto", "activos", "patrimonio", "flujo_operativo")


def _limitar(x, bajo, alto):
    return max(bajo, min(alto, x))


def _media(valores):
    valores = [v for v in valores if v is not None]
    return statistics.fmean(valores) if valores else None


def estimaciones_por_defecto(fund: dict[int, dict], ejercicios: list[int], beta_estimada: float) -> Estimaciones:
    """Supuestos iniciales del analista: medias de los 3 últimos ejercicios, acotadas a rangos razonables."""
    ult = ejercicios[-3:]
    crec = cagr(fund[ult[0]]["ingresos"], fund[ult[-1]]["ingresos"], len(ult) - 1)
    margen = _media(fund[a]["margen_ebitda"] for a in ult)
    da = _media((fund[a]["ebitda"] - fund[a]["ebit"]) / fund[a]["ingresos"] for a in ult
                if fund[a]["ebitda"] is not None and fund[a]["ingresos"])
    capex = _media(fund[a]["capex_sobre_ventas"] for a in ult)
    tipo = _media(fund[a]["tipo_efectivo"] for a in ult)
    base = Estimaciones()
    return Estimaciones(
        crecimiento_ventas=[round(_limitar(crec if crec is not None else 0.05, -0.10, 0.25), 4)] * 3,
        margen_ebitda=[round(_limitar(margen if margen is not None else 0.20, -0.5, 0.8), 4)] * 3,
        da_sobre_ventas=round(_limitar(da if da is not None else base.da_sobre_ventas, 0, 0.3), 4),
        capex_sobre_ventas=round(_limitar(capex if capex is not None else base.capex_sobre_ventas, 0, 0.4), 4),
        circulante_sobre_ventas=0.0,
        tasa_fiscal=round(_limitar(tipo if tipo is not None else base.tasa_fiscal, 0.05, 0.35), 4),
        beta=round(_limitar(beta_estimada, 0.3, 3.0), 2),
    )


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


def componer(*, ticker: str, empresa: str, sic, cobertura, filing: dict, estados, calidad, cotizacion, acciones: float,
             beta_estimada: float, comportamiento: dict, series_bolsa: dict, riesgos: list, riesgos_lista: list,
             texto_negocio: str, fecha: str | None = None, estimaciones: Estimaciones | None = None) -> dict:
    """Parte pura (sin red): de los datos ya reunidos al contexto completo del informe.

    Sin `estimaciones`, se usan las de por defecto; el editor pasa las del analista y todo se recalcula.
    """
    from ..ingesta.mercado import etf_sectorial

    ejercicios = estados.ejercicios[-ANIOS:]  # el ejercicio anterior, si se cargó, solo sirve de base del crecimiento
    ejercicio = filing["ejercicio"]
    fund = {a: fundamentales(estados, a) for a in ejercicios}
    mercado = Mercado(cotizacion.precio, acciones, cotizacion.fecha)
    multiplos = valoracion(estados, ejercicio, mercado)

    f = fund[ejercicio]
    est = estimaciones
    if est is None:
        est = estimaciones_por_defecto(fund, ejercicios, beta_estimada)
        intereses = estados.valor("gasto_intereses", ejercicio)
        if intereses and f["deuda_bruta"]:  # si la empresa no declara el gasto por intereses, se usa el valor por defecto
            est = Estimaciones(**{**asdict(est), "coste_deuda": round(_limitar(intereses / f["deuda_bruta"], 0.02, 0.12), 4)})
    if errores := est.validar():
        raise ValueError("Estimaciones no válidas: " + " ".join(errores))
    valor = dcf(est, f["ingresos"], f["dfn"] or 0.0, f["deuda_bruta"], estados.valor("minoritarios", ejercicio) or 0.0,
                acciones, mercado.capitalizacion)
    potencial_dcf = valor.valor_por_accion / cotizacion.precio - 1
    precio_objetivo = est.precio_objetivo_analista or valor.valor_por_accion  # el del analista prevalece si lo fija
    potencial = precio_objetivo / cotizacion.precio - 1
    propuesta = recomendacion_propuesta(potencial)

    anio_ini = ejercicios[0]
    datos = {
        "empresa": empresa, "ticker": ticker, "ejercicio": f"FY{ejercicio}",
        "recomendacion_propuesta": propuesta, "precio_objetivo": precio_objetivo, "precio": cotizacion.precio,
        "potencial": potencial, "potencial_dcf": potencial_dcf, "ventas": f["ingresos"] / 1e6,
        "crecimiento_ventas": f["crecimiento_ingresos"],
        "margen_ebitda": f["margen_ebitda"], "dfn_ebitda": f["dfn_ebitda"],
        "anio_ini": anio_ini, "anio_fin": ejercicio, "ventas_ini": fund[anio_ini]["ingresos"] / 1e6,
        "ventas_fin": f["ingresos"] / 1e6, "cagr_ventas": cagr(fund[anio_ini]["ingresos"], f["ingresos"], len(ejercicios) - 1),
        "margen_ebitda_ini": fund[anio_ini]["margen_ebitda"], "margen_ebitda_fin": f["margen_ebitda"], "dfn": (f["dfn"] or 0) / 1e6,
        "ventas_est": valor.ingresos[-1] / 1e6, "anio_fin_est": ejercicio + len(est.crecimiento_ventas),
        "cagr_ventas_est": cagr(f["ingresos"], valor.ingresos[-1], len(valor.ingresos)), "margen_ebitda_est": est.margen_ebitda[-1],
        "riesgos": riesgos or [{"resumen": "[[ANALISTA: resume los riesgos principales del Item 1A]]", "cita": "—"}],
        "cita_negocio": _cita_negocio(texto_negocio)
        or "[[ANALISTA: describe el negocio (el 10-K no tiene un párrafo descriptivo extraíble)]]",
        "segmentos": [],
        "margen_bruto": f["margen_bruto"], "margen_operativo": f["margen_operativo"], "roic": f["roic"], "roe": f["roe"],
        "fcf": (f["fcf"] or 0) / 1e6, "conversion_fcf": f["conversion_fcf"],
        "precio_objetivo_dcf": valor.valor_por_accion, "precio_objetivo_multiplos": None, "wacc": valor.wacc, "g": est.g,
        "auditor": "[[ANALISTA: auditor (Item 9 / proxy)]]",
    }
    textos = {b.id: rellenar(b.id, datos) for b in BLOQUES if b.tipo in (Tipo.PLANTILLA, Tipo.ANALISTA)}
    return {
        "ticker": ticker, "empresa": empresa, "sic": sic, "etf": etf_sectorial(sic), "cobertura": cobertura, "filing": filing,
        "ejercicios": ejercicios, "estados": estados, "fundamentales": fund, "calidad": calidad,
        "cotizacion": cotizacion, "mercado": mercado, "multiplos": multiplos, "comportamiento": comportamiento,
        "estimaciones": est, "beta": beta_estimada, "dcf": valor, "precio_objetivo": precio_objetivo, "potencial": potencial,
        "potencial_dcf": potencial_dcf, "recomendacion": propuesta,
        "riesgos": riesgos, "riesgos_lista": riesgos_lista, "textos": textos,
        "pendientes": [p for t in textos.values() for p in pendientes(t)], "fecha": fecha or date.today().isoformat(),
        "series_bolsa": series_bolsa,
    }


def construir(ticker: str, con_ia: bool = True) -> dict:
    """Reúne los datos (SEC, mercado, IA opcional) y compone el informe. Requiere EDGAR_IDENTITY y red."""
    from edgar import Company

    from ..ingesta.mercado import INDICE, comportamiento, cotizacion, etf_sectorial, historico
    from ..ingesta.riesgos import riesgos_anuales

    ticker = ticker.upper()
    empresa = Company(ticker)
    filing = empresa.get_filings(form="10-K", amendments=False).latest()
    xbrl = filing.xbrl()
    ejercicio = int(xbrl.entity_info["fiscal_year"])
    ejercicios = list(range(ejercicio - ANIOS, ejercicio + 1))  # + 1 año previo para el crecimiento del primero

    facts = empresa.get_facts()
    estados = normalizar(FuenteEntityFacts(facts), ejercicios, ticker)
    calidad = revisar(estados)
    del_10k = normalizar(FuenteXBRL(xbrl, filing.accession_no), [ejercicio], ticker)
    for p in PARTIDAS_CONTRASTE:  # contraste entre fuentes: companyfacts vs XBRL del último 10-K
        a, b = estados.valor(p, ejercicio), del_10k.valor(p, ejercicio)
        if a is not None and b is not None and abs(a - b) > 0.005 * max(abs(a), abs(b)):
            calidad.errores.append(f"FY{ejercicio}: {p} difiere entre companyfacts ({a:,.0f}) y el 10-K ({b:,.0f})")

    riesgos_lista, texto_1a, _ = riesgos_anuales(ticker)
    riesgos = []
    if con_ia and riesgos_lista:
        from ..ia.bloques import riesgos_principales

        elegidos, cfg = riesgos_principales(riesgos_lista, texto_1a)
        riesgos = [{"resumen": s.resumen, "cita": s.cita, "modelo": f"{cfg.proveedor} · {cfg.modelo}"} for s in elegidos]

    return componer(
        ticker=ticker, empresa=empresa.name, sic=empresa.sic, cobertura=cobertura_de(ticker),
        filing={"accession": filing.accession_no, "fecha": str(filing.filing_date), "ejercicio": ejercicio},
        estados=estados, calidad=calidad, cotizacion=cotizacion(ticker),
        acciones=float(facts.shares_outstanding or 0) or estados.valor("acciones_diluidas", ejercicio),
        beta_estimada=_beta_semanal(ticker), comportamiento=comportamiento(ticker, empresa.sic),
        series_bolsa=_series_bolsa(ticker, etf_sectorial(empresa.sic), historico, INDICE),
        riesgos=riesgos, riesgos_lista=riesgos_lista, texto_negocio=filing.obj().business or "",
    )
