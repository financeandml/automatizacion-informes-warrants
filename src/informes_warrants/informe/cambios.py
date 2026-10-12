"""Cambios frente al informe anterior (R16): qué se movió y cuánto explica cada supuesto del cambio de valor.

Patrón de FinRobot `finrobot_desktop/finrobot/artifact/semantic_diff.py` (`build_semantic_delta`: lista curada
de campos y atribución por re-valoración con la función pura del DCF, sin IA; Apache-2.0). Cambio: atribución
SECUENCIAL, que cuadra exactamente con el cambio total (la de un factor cada vez deja un residuo de
interacción). Orden fijo: datos de partida (LTM, balance, acciones, cotización) → crecimiento → márgenes →
WACC (Rf, prima, beta, coste de la deuda, tasa fiscal) → g → resto de supuestos.

Cada informe guarda su `resumen` (JSON) junto al PDF y en su versión; el siguiente lo compara.
"""

from dataclasses import asdict, fields

from ..calculo.dcf import atribucion_secuencial
from .estimaciones import Estimaciones

GRUPOS = (
    ("Crecimiento de ventas", ("crecimiento_ventas",)),
    ("Márgenes", ("margen_ebitda",)),
    ("Coste del capital (WACC)", ("rf", "erp", "beta", "coste_deuda", "tasa_fiscal")),
    ("Crecimiento a perpetuidad", ("g",)),
)
CAMPOS_DCF = ("ingresos_base", "dfn", "deuda", "minoritarios", "acciones", "capitalizacion")


def resumen(c: dict) -> dict:
    """Lo necesario para comparar con el siguiente informe (serializable en JSON)."""
    est = c["estimaciones"]
    return {
        "ticker": c["ticker"], "fecha": c["fecha"], "fecha_ltm": c["fecha_ltm"], "ejercicio": c["filing"]["ejercicio"],
        "cotizacion": c["cotizacion"].precio, "precio_objetivo": c["precio_objetivo"], "recomendacion": c["recomendacion"],
        "valor_dcf": c["valor_dcf"], "valor_multiplos": c["valor_multiplos"],
        "dcf_base": c["dcf"].valor_por_accion if c["dcf"] else None,
        "estimaciones": {k: v for k, v in asdict(est).items()},
        "datos_dcf": c.get("datos_dcf"),
        "ingresos_ltm": c["fund_ltm"].get("ingresos"), "ebitda_ltm": c["fund_ltm"].get("ebitda"),
        "bpa_ltm": c["fund_ltm"].get("bpa_diluido"),
    }


def _estimaciones(d: dict) -> Estimaciones:
    validos = {f.name for f in fields(Estimaciones)}
    return Estimaciones(**{k: v for k, v in d.items() if k in validos})


def comparar(anterior: dict, actual: dict) -> dict:
    """Diferencias de los campos clave y atribución del cambio del valor DCF (escenario base) por grupos."""
    campos = (("Precio objetivo (USD)", "precio_objetivo"), ("Recomendación", "recomendacion"), ("Cotización (USD)", "cotizacion"),
              ("Valor DCF (USD)", "valor_dcf"), ("Ingresos LTM", "ingresos_ltm"), ("EBITDA LTM", "ebitda_ltm"), ("BPA LTM", "bpa_ltm"))
    cambios = [{"campo": n, "antes": anterior.get(k), "ahora": actual.get(k)} for n, k in campos if anterior.get(k) != actual.get(k)]
    atribucion = None
    if anterior.get("datos_dcf") and actual.get("datos_dcf") and anterior.get("dcf_base") and actual.get("dcf_base"):
        est_ant, est_act = _estimaciones(anterior["estimaciones"]), _estimaciones(actual["estimaciones"])
        try:
            atribucion = atribucion_secuencial(est_ant, est_act, actual["datos_dcf"], anterior["dcf_base"], GRUPOS)
        except (ValueError, TypeError):
            atribucion = None
    return {"fecha_anterior": anterior.get("fecha"), "cambios": cambios, "atribucion": atribucion}
