"""Motor de valoración (B1) conectado al informe: de los datos ya reunidos (`componer`, sin red) al modelo.

Construye `DatosMotor` con lo que ya trae el contexto del informe (normalizador SEC, cotización, comparables del
analista, beta, tipo libre de riesgo y prima de riesgo), aplica las entradas del analista (`Estimaciones.motor`, con
los valores por defecto marcados «Revisar») y devuelve el modelo calculado. El libro .xlsx con las fórmulas se
genera a petición (`guardar_libro`) para descargarlo y comprobarlo número a número.
"""

import csv
import logging
from datetime import date
from pathlib import Path

from ..calculo.motor.modelo import (
    ANIOS_PROY,
    Comparable,
    DatosMotor,
    EntradasMotor,
    Modelo,
    construir,
    entradas_por_defecto,
    segmentos_del_modelo,
)
from ..calculo.normalizador import LTM, LTM_PREVIO
from ..observabilidad import medido

log = logging.getLogger(__name__)


def _mn(v):
    return None if v is None else v / 1e6


def _comparable(x: dict) -> Comparable | None:
    estados = x.get("estados")
    f = x.get("fundamentales") or {}
    if estados is None:  # datos de comparables de antes del motor (sin LTM − 1 ni balance): se omiten
        return None

    def v(p, k):
        return estados.valor(p, k)

    def bloque(k):
        ebit, da = v("resultado_operativo", k), v("amortizacion", k)
        ventas, coste = v("ingresos", k), v("coste_ventas", k)
        return {"ingresos": _mn(ventas), "beneficio_bruto": _mn(ventas - coste) if None not in (ventas, coste) else None,
                "ebit": _mn(ebit), "ebitda": _mn(ebit + da) if None not in (ebit, da) else None,
                "beneficio_neto": _mn(v("beneficio_neto", k)), "bpa": v("bpa_diluido", k)}

    suma = lambda *ps: sum(v(p, LTM) or 0.0 for p in ps)  # noqa: E731
    cot = x.get("cotizacion")
    return Comparable(
        ticker=x["ticker"], nombre=x["nombre"], precio=cot.precio if cot else x["multiplos"].get("precio"),
        acciones=(x.get("acciones") or 0) / 1e6, beta=x.get("beta"), tipo_impositivo=f.get("tipo_efectivo"),
        maximo_52s=cot.maximo_12m if cot else None, minimo_52s=cot.minimo_12m if cot else None, variaciones=x.get("variaciones") or {},
        ltm=bloque(LTM), ltm_previo=bloque(LTM_PREVIO),
        deuda={"deuda": _mn(suma("deuda_cp", "deuda_lp")), "caja": _mn(suma("caja", "inversiones_cp")),
               "preferentes": _mn(v("preferentes", LTM)), "minoritarios": _mn(v("minoritarios", LTM))},
        tacc_ventas_3a=x.get("tacc_ventas_3a"), origen=x.get("origen", ""))


def datos(c: dict) -> tuple[DatosMotor, str]:
    """Datos del motor a partir del contexto del informe (plantilla general)."""
    from ..calculo.metricas import componentes_ev
    from .render import etiqueta_ltm

    ejercicio = c["filing"]["ejercicio"]
    anios = list(range(ejercicio - 5, ejercicio + 1))
    segmentos, motivo = segmentos_del_modelo((c.get("segmentos") or {}).get("negocio"), c["estados"], ejercicio, anios, c["empresa"])
    cierre = c["filing"].get("cierre")
    cot = c["cotizacion"]
    est = c["estimaciones"]
    bandas = c.get("bandas") or {}
    datos_motor = DatosMotor(
        ticker=c["ticker"], empresa=c["empresa"], fecha_valoracion=date.fromisoformat(str(cot.fecha)[:10]),
        cierre_ejercicio=date.fromisoformat(cierre[:10]) if cierre else date(ejercicio, 12, 31), ejercicio=ejercicio,
        estados=c["estados"], estados_ltm=c["estados_ltm"], etiqueta_ltm=etiqueta_ltm(c), segmentos=segmentos,
        precio=cot.precio, maximo_52s=cot.maximo_12m, minimo_52s=cot.minimo_12m, acciones_basicas=c["mercado"].acciones,
        origen_acciones=c.get("acciones_origen") or "", beta_propia=c["beta"], rf=est.rf,
        origen_rf=(f"{c['rf'].fuente} a {c['rf'].fecha}" if c.get("rf") else "Valor por defecto"),
        erp=est.erp, origen_erp=c.get("origen_prima") or "Prima de riesgo del informe",
        componentes_ev=componentes_ev(c["estados_ltm"], LTM),
        # comparables del analista o, sin su lista, los «comparables modelo» del SaaS (sector de Damodaran; Revisar)
        comparables=[x for x in (_comparable(x) for x in (c.get("comparables") or [])) if x],
        comparables_modelo=not c.get("comparables_del_analista"), origen_comparables=c.get("comparables_criterio") or "",
        beta_sector=getattr(c.get("beta_sector"), "desapalancada", None),
        origen_beta_sector=getattr(c.get("beta_sector"), "origen", ""),
        mediana_historica={k: b.mediana for k, b in bandas.items() if getattr(b, "n", 0) and b.mediana},
        dpa_proyectados=list(c.get("dpa_proyectados") or []), vc_por_accion=c.get("vc_por_accion"),
        roe_sostenible=c.get("roe_sostenible"), origen_roe=c.get("origen_roe") or "")
    return datos_motor, motivo


def entradas(datos_motor: DatosMotor, est) -> EntradasMotor:
    """Valores por defecto del motor con lo que el analista haya cambiado (`Estimaciones.motor`)."""
    e = entradas_por_defecto(datos_motor, est.crecimiento_ventas, est.g, est.rf, est.erp)
    propias = getattr(est, "motor", None) or {}
    for clave in ("crecimientos", "margenes"):
        for segmento, valores in (propias.get(clave) or {}).items():
            if segmento in getattr(e, clave) and len(valores) == ANIOS_PROY:
                getattr(e, clave)[segmento] = [float(x) for x in valores]
                e.por_defecto.discard(clave)
    for clave in ("pct_perpetuidad", "convencion", "lbo"):
        if propias.get(clave) is not None:
            setattr(e, clave, type(getattr(e, clave))(propias[clave]))
            e.por_defecto.discard(clave)
    return e


def valorar(c: dict) -> dict | None:
    """Modelo calculado y su resumen para el informe; None si faltan las ventas o el EBIT del último ejercicio."""
    try:
        d, motivo = datos(c)
        if not d.segmentos or c["filing"]["ejercicio"] not in d.segmentos[0].ingresos:
            return None
        modelo = construir(d, entradas(d, c["estimaciones"]))
    except Exception as e:  # noqa: BLE001  (el motor nunca impide el informe: sin él, la valoración anterior)
        log.warning("Motor de valoración no disponible: %s", e)
        return {"error": str(e)}
    return {"modelo": modelo, "datos": d, "motivo": motivo, "salidas": modelo.salidas, "avisos": modelo.avisos}


def guardar_libro(resultado: dict, destino) -> str:
    """El .xlsx del modelo con las fórmulas vivas (para descargar desde la interfaz o junto al PDF)."""
    resultado["modelo"].libro.guardar(destino)
    return str(destino)


@medido("excel")
def exportar(c: dict, ruta_pdf, contrastar: bool = True) -> tuple[str | None, list[str]]:
    """Guarda el libro del informe (general o sectorial) junto al PDF, con el mismo nombre y extensión .xlsx, y lo
    contrasta celda a celda con LibreOffice (segunda vía de cálculo). Devuelve la ruta y los avisos de discrepancia, que
    no impiden emitir; la lista completa de discrepancias queda en `<nombre>_discrepancias.csv`."""
    from ..calculo.motor.recalculo import contrastar as contraste

    modelo = modelo_de(c.get("motor"))
    if modelo is None:
        return None, []
    ruta = Path(ruta_pdf).with_suffix(".xlsx")
    modelo.libro.guardar(ruta)
    if not contrastar:
        return str(ruta), []
    r = contraste(modelo, ruta)
    if r["diferencias"]:
        with open(ruta.with_name(ruta.stem + "_discrepancias.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["hoja", "fila", "columna", "python", "libreoffice"])
            w.writerows([*celda, py, lo] for celda, py, lo in r["diferencias"])
    elif r["recalculado"] is not None:
        r["avisos"].append(f"Motor de valoración: las {r['comparadas']} celdas con fórmula coinciden con LibreOffice")
    return str(ruta), r["avisos"]


def editables(c: dict) -> EntradasMotor | None:
    """Las entradas del motor con las que se ha calculado el informe (valores por defecto y cambios del analista)."""
    m = c.get("motor") or {}
    return entradas(m["datos"], c["estimaciones"]) if m.get("datos") else None


def modelo_de(resultado: dict | None) -> Modelo | None:
    return (resultado or {}).get("modelo")
