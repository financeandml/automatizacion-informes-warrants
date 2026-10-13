"""Criterios del fondo y gestión de la posición (B4, apartados 12, 23 y 24), con los parámetros del analista.

Reutiliza:
- financial-research-analyst-agent `src/agents/risk.py` `calculate_var_tool` (Copyright (c) 2024 Gopal Saini, MIT):
  VaR y CVaR históricos al 95 % con el percentil de los rendimientos diarios.
- stock-screener `src/screening/signal_engine.py` `calculate_stop_loss` (MIT), solo la idea de acotar la pérdida
  hasta el stop entre un mínimo y un máximo (su stop es técnico, de *swing trading*; el nuestro es por volatilidad).

  Stop = precio × (1 − k × σ_diaria × √h), con la pérdida acotada entre el mínimo y el máximo del analista
  Acciones = capital × riesgo por posición / (precio − stop), sin superar el peso máximo de la cartera
  Días para construir la posición = acciones / (volumen medio diario × participación máxima)
  Prueba histórica del stop = % de ventanas de h sesiones (5 años) en que la cotización cayó hasta el stop
"""

import math
import statistics

CONFIANZA_VAR = 0.95
SESIONES_VOLATILIDAD = 252


def evaluar_criterios(p, datos: dict) -> list[dict]:
    """Cada criterio definido por el analista frente a la cifra del informe: cumple, no cumple o sin dato."""
    reglas = (("Potencial frente al precio objetivo", "potencial_minimo", "potencial", ">="),
              ("PER (LTM)", "per_maximo", "per", "<="), ("EV / EBITDA (LTM)", "ev_ebitda_maximo", "ev_ebitda", "<="),
              ("Deuda neta / EBITDA", "deuda_neta_ebitda_maxima", "dfn_ebitda", "<="), ("ROIC (LTM)", "roic_minimo", "roic", ">="),
              ("Crecimiento de ventas (LTM)", "crecimiento_minimo", "crecimiento", ">="))
    filas = []
    for nombre, parametro, clave, signo in reglas:
        umbral = getattr(p, parametro)
        if umbral is None:
            continue
        valor = datos.get(clave)
        cumple = None if valor is None else (valor >= umbral if signo == ">=" else valor <= umbral)
        filas.append({"criterio": nombre, "umbral": umbral, "signo": signo, "valor": valor, "cumple": cumple,
                      "porcentaje": parametro in ("potencial_minimo", "roic_minimo", "crecimiento_minimo")})
    return filas


def rendimientos_diarios(cierres, sesiones: int = SESIONES_VOLATILIDAD) -> list[float]:
    valores = [float(x) for x in list(cierres)[-(sesiones + 1):]] if cierres is not None else []
    return [math.log(b / a) for a, b in zip(valores, valores[1:], strict=False) if a > 0 and b > 0]


def var_historico(rendimientos: list[float], confianza: float = CONFIANZA_VAR) -> tuple[float, float] | None:
    """(VaR, CVaR) diarios: el percentil (1 − confianza) de los rendimientos y la media de los que quedan por debajo."""
    if len(rendimientos) < 20:
        return None
    ordenados = sorted(rendimientos)
    posicion = (1 - confianza) * (len(ordenados) - 1)  # interpolación lineal, como numpy.percentile
    bajo, alto = math.floor(posicion), math.ceil(posicion)
    var = ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (posicion - bajo)
    cola = [r for r in ordenados if r <= var]
    return var, statistics.fmean(cola)


def stop_volatilidad(precio: float, sigma_diaria: float, k: float, horizonte: int,
                     perdida_minima: float | None = None, perdida_maxima: float | None = None) -> dict:
    perdida = k * sigma_diaria * math.sqrt(horizonte)
    acotada = min(max(perdida, perdida_minima or 0.0), perdida_maxima or perdida)
    return {"stop": precio * (1 - acotada), "perdida": acotada, "perdida_sin_acotar": perdida}


def tamano_posicion(capital: float, riesgo_por_posicion: float, precio: float, stop: float, peso_maximo: float | None = None) -> dict:
    riesgo_usd = capital * riesgo_por_posicion
    acciones = riesgo_usd / (precio - stop) if precio > stop else 0.0
    limitada = peso_maximo is not None and acciones * precio > capital * peso_maximo
    if limitada:
        acciones = capital * peso_maximo / precio
    return {"acciones": acciones, "importe": acciones * precio, "peso": acciones * precio / capital,
            "riesgo_usd": acciones * (precio - stop), "limitada_por_peso": limitada}


def dias_para_construir(acciones: float, volumen_medio: float | None, participacion: float | None) -> float | None:
    if not volumen_medio or not participacion:
        return None
    return acciones / (volumen_medio * participacion)


def frecuencia_stop(cierres, perdida: float, horizonte: int) -> float | None:
    """Prueba histórica del stop: proporción de ventanas de `horizonte` sesiones (todas las de la serie, solapadas) en
    las que la cotización llegó a caer `perdida` desde el inicio de la ventana. Cotizaciones propias, ajustadas."""
    valores = [float(x) for x in list(cierres)] if cierres is not None else []
    ventanas = len(valores) - horizonte
    if ventanas < 20 or perdida <= 0:
        return None
    tocadas = sum(1 for i in range(ventanas) if min(valores[i + 1:i + horizonte + 1]) <= valores[i] * (1 - perdida))
    return tocadas / ventanas
