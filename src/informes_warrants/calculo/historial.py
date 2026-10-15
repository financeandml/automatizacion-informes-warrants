"""Historial de recomendación y precio objetivo (R17), a partir de las versiones emitidas.

Reglas de la señal adaptadas de FinRobot `finrobot_desktop/finrobot/engine/compute/operators/signal.py`
(`compute_signal`; AI4Finance Foundation, Apache-2.0):
  - acertada: el precio está a menos del 10 % del objetivo, o ya recorrió más del 50 % del camino esperado
  - fallida: el precio se movió un 10 % o más en contra (tras 7 días), o venció el horizonte sin acertar
  - en curso: el resto (y siempre los 7 primeros días)
Cambio: horizonte de 12 meses fijo (el de nuestro sistema de recomendación) y textos en español.
"""

from datetime import date, timedelta

BANDA_ACIERTO, PROGRESO_ACIERTO, CONTRA_FALLO = 0.10, 0.50, 0.10
DIAS_GRACIA, HORIZONTE_DIAS = 7, 365


def senal(objetivo: float, entrada: float, actual: float, fecha_entrada: date, hoy: date) -> str:
    if not (objetivo and entrada and actual) or objetivo == entrada:
        return "sin señal"
    esperado = objetivo - entrada
    movimiento = actual - entrada
    if abs(actual - objetivo) / objetivo <= BANDA_ACIERTO or movimiento / esperado > PROGRESO_ACIERTO:
        return "acertada"
    dias = (hoy - fecha_entrada).days
    if dias >= DIAS_GRACIA and (movimiento / entrada) * (1 if esperado > 0 else -1) <= -CONTRA_FALLO:
        return "fallida"
    if hoy > fecha_entrada + timedelta(days=HORIZONTE_DIAS):
        return "fallida"
    return "en curso"


def historial(resumenes: list[dict], precio_actual: float, hoy: date) -> list[dict]:
    """Filas del historial (de la más antigua a la más reciente) con su señal a fecha de hoy."""
    filas = []
    for r in sorted(resumenes, key=lambda x: x.get("fecha", "")):
        if not r.get("precio_objetivo") or not r.get("cotizacion"):
            continue
        fecha = date.fromisoformat(r["fecha"])
        filas.append({"fecha": r["fecha"], "recomendacion": r.get("recomendacion"), "precio_objetivo": r["precio_objetivo"],
                      "cotizacion": r["cotizacion"],
                      "senal": senal(r["precio_objetivo"], r["cotizacion"], precio_actual, fecha, hoy)})
    return filas


def real_frente_a_estimado(anterior: dict, actual: dict) -> dict | None:
    """P9 (apartado 25): con un 10-Q nuevo, lo real (LTM nuevo) frente a lo que esperaba el informe anterior para esa fecha.

    Esperado = LTM anterior + (estimación del primer año − LTM anterior) × meses transcurridos / 12 (interpolación
    lineal del primer año proyectado; sin la estimación guardada, las ventas con el primer crecimiento compuesto).
    Devuelve None si no ha pasado tiempo entre los dos LTM o faltan datos."""
    from datetime import date

    try:
        f0, f1 = date.fromisoformat(str(anterior["fecha_ltm"])[:10]), date.fromisoformat(str(actual["fecha_ltm"])[:10])
    except (KeyError, TypeError, ValueError):
        return None
    meses = (f1.year - f0.year) * 12 + f1.month - f0.month
    if meses <= 0:
        return None
    fraccion = min(meses, 12) / 12
    filas = []
    for nombre, clave in (("Ventas LTM (USD mn)", "ingresos"), ("EBITDA LTM (USD mn)", "ebitda"), ("BPA LTM (USD)", "bpa")):
        base, real, est = anterior.get(f"{clave}_ltm"), actual.get(f"{clave}_ltm"), anterior.get(f"{clave}_est_1")
        if est is None and clave == "ingresos" and base is not None:
            crecimiento = ((anterior.get("estimaciones") or {}).get("crecimiento_ventas") or [None])[0]
            est = base * (1 + crecimiento) if crecimiento is not None else None
        if base is None or real is None or est is None:
            continue
        esperado = base + (est - base) * fraccion
        filas.append({"concepto": nombre, "anterior": base, "esperado": esperado, "real": real,
                      "desviacion": real / esperado - 1 if esperado else None})
    return {"meses": meses, "fecha_anterior": str(anterior.get("fecha")), "filas": filas} if filas else None
