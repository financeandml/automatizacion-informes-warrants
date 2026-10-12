"""Notas de contexto de los ratios, por reglas deterministas (sin IA).

Un ratio correcto puede parecer un error sin contexto (p. ej. el ROE del 151,9 % de AAPL con un
patrimonio reducido por las recompras). Cada regla mira las partidas que explican la anomalía y, si se
cumple, añade una nota al pie del informe. Umbrales fijos y documentados aquí.
"""

PATRIMONIO_REDUCIDO = 0.10  # patrimonio < 10 % del activo
ROE_ELEVADO = 0.50
ROIC_ELEVADO = 0.50
TIPO_ANOMALO = (0.05, 0.40)
PER_NO_SIGNIFICATIVO = 75.0  # mismo límite que la mediana de comparables (FinRobot)


def notas_de_ratios(f: dict, estados, clave: int, multiplos: dict, recompras_periodo: float | None) -> list[tuple[str, str]]:
    """(ratio, nota) para el periodo `clave` de `estados` (normalmente el LTM)."""
    notas = []
    patrimonio, activos = estados.valor("patrimonio", clave), estados.valor("activos", clave)
    if patrimonio is not None and patrimonio <= 0:
        notas.append(("ROE", "Patrimonio neto negativo: el ROE y el precio / valor contable no son interpretables."))
    elif patrimonio is not None and activos and (patrimonio / activos < PATRIMONIO_REDUCIDO or (f.get("roe") or 0) > ROE_ELEVADO):
        motivo = ""
        if recompras_periodo and recompras_periodo > patrimonio:
            motivo = (
                f" Las recompras de acciones de los últimos ejercicios ({_mn(recompras_periodo)} USD Mn) superan el "
                "patrimonio actual: la empresa devuelve más capital del que retiene."
            )
        peso = _pct(patrimonio / activos)
        reducido = patrimonio / activos < PATRIMONIO_REDUCIDO
        causa = f"patrimonio reducido ({peso} del activo)" if reducido else f"patrimonio del {peso} del activo"
        notas.append(("ROE", f"ROE elevado frente al patrimonio contable ({causa}).{motivo}"))
    if f.get("dfn") is not None and f["dfn"] < 0:
        notas.append(
            ("Deuda neta / EBITDA", "Valor negativo: la empresa tiene caja neta (más caja e inversiones a corto que deuda).")
        )
    if f.get("roic") is not None and f["roic"] > ROIC_ELEVADO:
        notas.append(
            (
                "ROIC",
                "ROIC elevado: el capital invertido (patrimonio + deuda neta) es pequeño por la caja neta y las recompras; "
                "mide la rentabilidad sobre el capital contable, no sobre el valor de mercado.",
            )
        )
    tipo = f.get("tipo_efectivo")
    if tipo is not None and not TIPO_ANOMALO[0] <= tipo <= TIPO_ANOMALO[1]:
        notas.append(
            ("Tipo impositivo efectivo", f"Tipo efectivo atípico ({_pct(tipo)}): puede reflejar partidas fiscales puntuales.")
        )
    per = multiplos.get("per")
    if per is not None and (per <= 0 or per > PER_NO_SIGNIFICATIVO):
        notas.append(("PER", "PER no significativo (beneficio negativo o muy reducido frente a la cotización)."))
    return notas


def _pct(x: float) -> str:
    return f"{x * 100:.1f} %".replace(".", ",")


def _mn(x: float) -> str:
    return f"{x / 1e6:,.0f}".replace(",", ".")
