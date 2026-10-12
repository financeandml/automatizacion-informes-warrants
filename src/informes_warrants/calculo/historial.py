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
