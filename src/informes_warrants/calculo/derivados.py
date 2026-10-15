"""Mercado de opciones y posiciones cortas (B5): cálculos sobre datos externos (yfinance, no auditados).

Adaptado de financial-research-analyst-agent `src/tools/options_analyzer.py` (`_calculate_sentiment`,
`_calculate_volatility`, `_detect_unusual_activity`, `_calculate_max_pain`; Copyright (c) 2024 Gopal Saini, licencia
MIT). Cambios: sin su señal ni sus etiquetas «alcista/bajista» (solo cifras y una lectura descriptiva con umbrales
fijos); el ratio put/call también por posiciones abiertas; la volatilidad implícita se contrasta con la realizada a 30
días, calculada con nuestras cotizaciones (FRAA la juzgaba con umbrales absolutos).

  Put/call = volumen (o posiciones abiertas) de puts / de calls
  Volatilidad implícita = media de la de cada contrato ponderada por su volumen (calls y puts por separado)
  Max pain = precio de vencimiento con el menor pago total a los compradores de opciones (el que más conviene a
             los vendedores), sobre los strikes del vencimiento más próximo
  Actividad inusual = contratos con volumen ≥ 500 y > 2 × posiciones abiertas (FRAA)
  Volatilidad realizada a 30 días = desviación típica de los rendimientos logarítmicos diarios × √252
"""

import math

MINIMO_INUSUAL, MULTIPLO_INUSUAL, MAX_INUSUALES = 500, 2, 5
SESIONES_REALIZADA = 21
# Lectura de las posiciones cortas sobre el capital flotante (umbrales de FRAA `_SHORT_PCT_THRESHOLDS`)
NIVELES_CORTOS = ((0.25, "muy elevado"), (0.10, "elevado"), (0.05, "moderado"), (0.0, "bajo"))


def _suma(df, columna) -> float:
    return float(df[columna].fillna(0).sum()) if columna in df and not df.empty else 0.0


def put_call(calls, puts) -> dict:
    return {"volumen": _suma(puts, "volume") / _suma(calls, "volume") if _suma(calls, "volume") else None,
            "posiciones": _suma(puts, "openInterest") / _suma(calls, "openInterest") if _suma(calls, "openInterest") else None,
            "volumen_calls": _suma(calls, "volume"), "volumen_puts": _suma(puts, "volume")}


def volatilidad_implicita(df) -> float | None:
    if df.empty or "impliedVolatility" not in df or "volume" not in df:
        return None
    validos = df[(df["impliedVolatility"] > 0) & (df["volume"].fillna(0) > 0)]
    volumen = validos["volume"].sum()
    return float((validos["impliedVolatility"] * validos["volume"]).sum() / volumen) if volumen else None


def max_pain(calls, puts) -> float | None:
    """Strike en el que el valor total de las opciones al vencimiento (lo que cobran los compradores) es mínimo."""
    if calls.empty or puts.empty or "openInterest" not in calls or "openInterest" not in puts:
        return None
    oi_calls = calls.groupby("strike")["openInterest"].sum().fillna(0).to_dict()
    oi_puts = puts.groupby("strike")["openInterest"].sum().fillna(0).to_dict()
    strikes = sorted(set(oi_calls) | set(oi_puts))
    if not strikes:
        return None
    pago = {p: sum(max(p - k, 0) * oi for k, oi in oi_calls.items()) + sum(max(k - p, 0) * oi for k, oi in oi_puts.items())
            for p in strikes}
    return float(min(pago, key=pago.get))  # FRAA `_calculate_max_pain`: mínimo


def actividad_inusual(calls, puts, precio: float) -> list[dict]:
    filas = []
    for tipo, df in (("Call", calls), ("Put", puts)):
        if df.empty or "volume" not in df or "openInterest" not in df:
            continue
        volumen, abiertas = df["volume"].fillna(0), df["openInterest"].fillna(0)
        candidatos = df.assign(volume=volumen, openInterest=abiertas)[(volumen >= MINIMO_INUSUAL) & (volumen > abiertas * MULTIPLO_INUSUAL)]
        for f in candidatos.to_dict("records"):  # sin NaN: yfinance deja vacías las posiciones abiertas de algunos strikes
            filas.append({"tipo": tipo, "strike": float(f["strike"]), "vencimiento": str(f.get("vencimiento", "")),
                          "volumen": int(f["volume"]), "posiciones": int(f.get("openInterest") or 0),
                          "prima_estimada": float(f["volume"]) * 100 * (float(f["lastPrice"]) if f.get("lastPrice") == f.get("lastPrice")
                                                                          and f.get("lastPrice") is not None else 0.0),
                          "distancia": float(f["strike"]) / precio - 1 if precio else None})
    return sorted(filas, key=lambda f: -f["prima_estimada"])[:MAX_INUSUALES]


def volatilidad_realizada(cierres, sesiones: int = SESIONES_REALIZADA) -> float | None:
    """Anualizada, con los `sesiones` últimos rendimientos logarítmicos diarios (nuestras cotizaciones)."""
    import statistics

    valores = [float(x) for x in list(cierres)[-(sesiones + 1):]] if cierres is not None else []
    if len(valores) < sesiones + 1 or min(valores) <= 0:
        return None
    rendimientos = [math.log(b / a) for a, b in zip(valores, valores[1:], strict=False)]
    return statistics.stdev(rendimientos) * math.sqrt(252)


def mercado_de_opciones(cadena: dict | None, precio: float, cierres) -> dict | None:
    if not cadena:
        return None
    calls, puts = cadena["calls"], cadena["puts"]
    proximo = cadena["vencimientos"][0]
    iv_calls, iv_puts = volatilidad_implicita(calls), volatilidad_implicita(puts)
    realizada = volatilidad_realizada(cierres)
    pondera = [(iv, _suma(df, "volume")) for iv, df in ((iv_calls, calls), (iv_puts, puts)) if iv is not None]
    iv = sum(i * v for i, v in pondera) / sum(v for _, v in pondera) if pondera and sum(v for _, v in pondera) else None
    return {"vencimientos": cadena["vencimientos"], "put_call": put_call(calls, puts), "iv_calls": iv_calls, "iv_puts": iv_puts,
            "iv": iv, "realizada_30d": realizada, "iv_sobre_realizada": iv / realizada if iv and realizada else None,
            "max_pain": max_pain(calls[calls["vencimiento"] == proximo], puts[puts["vencimiento"] == proximo]),
            "vencimiento_proximo": proximo, "inusual": actividad_inusual(calls, puts, precio), "consulta": cadena["consulta"]}


def lectura_cortos(sobre_flotante: float | None) -> str | None:
    if sobre_flotante is None:
        return None
    return next(nombre for umbral, nombre in NIVELES_CORTOS if sobre_flotante >= umbral)
