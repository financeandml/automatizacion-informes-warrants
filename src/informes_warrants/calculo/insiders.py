"""Actividad de los insiders en mercado (A6): saldo de compras y ventas y compras agrupadas.

Adaptado de financial-research-analyst-agent `src/tools/insider_activity.py` (`_compute_net_activity`,
`_detect_cluster_buying`; Copyright (c) 2024 Gopal Saini, licencia MIT). Cambios:
- Las operaciones salen de los Form 4 de la SEC con su código oficial (P compra, S venta), no de clasificar el
  texto de yfinance.
- Se separan las ventas hechas con un plan 10b5-1 (programadas de antemano: dicen poco de la opinión del insider).
- No se calcula su «smart money score» (pesos arbitrarios): solo cifras.

  Saldo neto = importe comprado − importe vendido (USD)
  Compras agrupadas = al menos 2 insiders distintos comprando en una ventana de 14 días
"""

from datetime import timedelta

VENTANA_AGRUPADAS_DIAS, MINIMO_COMPRADORES = 14, 2


def actividad(operaciones: list[dict]) -> dict:
    compras = [o for o in operaciones if o["tipo"] == "Compra"]
    ventas = [o for o in operaciones if o["tipo"] == "Venta"]
    importe = lambda ops: sum(o["importe"] or 0.0 for o in ops)  # noqa: E731
    con_plan = [o for o in ventas if o["plan_10b5_1"]]
    return {
        "compras": len(compras), "importe_compras": importe(compras), "acciones_compradas": sum(o["acciones"] for o in compras),
        "ventas": len(ventas), "importe_ventas": importe(ventas), "acciones_vendidas": sum(o["acciones"] for o in ventas),
        "saldo": importe(compras) - importe(ventas),
        "ventas_con_plan": len(con_plan), "importe_ventas_con_plan": importe(con_plan),
        "insiders": len({o["nombre"] for o in operaciones}),
        "agrupadas": compras_agrupadas(compras),
    }


def compras_agrupadas(compras: list[dict]) -> dict | None:
    """Primera ventana de 14 días con al menos 2 compradores distintos (None si no la hay)."""
    for inicio in sorted({o["fecha"] for o in compras}):
        fin = inicio + timedelta(days=VENTANA_AGRUPADAS_DIAS)
        en_ventana = [o for o in compras if inicio <= o["fecha"] <= fin]
        nombres = sorted({o["nombre"] for o in en_ventana})
        if len(nombres) >= MINIMO_COMPRADORES:
            return {"desde": inicio, "hasta": fin, "compradores": nombres, "importe": sum(o["importe"] or 0.0 for o in en_ventana)}
    return None


def participacion_institucional(trece_f: dict | None, acciones: float | None) -> dict | None:
    """Apartado 18 (P11): % del capital de cada gran tenedor y de la suma de los 13F sobre las acciones en circulación.
    La suma puede pasar del 100 % (una misma acción figura en el 13F de la gestora y en el de su matriz)."""
    if not trece_f or not acciones:
        return None
    filas = [{**f, "porcentaje": f["acciones"] / acciones} for f in trece_f["filas"]]
    return {**trece_f, "filas": filas, "porcentaje_total": trece_f["acciones_totales"] / acciones}
