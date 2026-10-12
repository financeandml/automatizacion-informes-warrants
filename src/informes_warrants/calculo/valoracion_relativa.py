"""Valoración relativa: medianas de los comparables y valor implícito por múltiplo (funciones puras).

Los múltiplos de cada comparable se calculan con el mismo normalizador y las mismas fórmulas que los
de la empresa (calculo/metricas.py `valoracion`, sobre su LTM). Reglas de la mediana adaptadas de
FinRobot `engine/compute/operators/multiples.py` (`PEER_PE_NM_CAP`, `PEER_EV_EBITDA_NM_CAP`,
`calculate_peer_statistics`; Apache-2.0): un múltiplo negativo, no finito o por encima del límite
«no significativo» sigue en la tabla, pero no entra en la mediana. Patrón de agregación de
financial-research-analyst-agent `peer_comparison.compare_peers` (mediana, mínimo, máximo).

  Valor implícito (por acción):
    EV/EBITDA, EV/Ventas: (mediana · métrica LTM − DFN − minoritarios) / acciones
    PER:                  mediana · beneficio neto LTM / acciones
    P/FCF:                mediana · FCF tras remuneración en acciones LTM / acciones
  Valor por múltiplos = media de los implícitos por EV/EBITDA y PER disponibles.
"""

import math
import statistics

# (clave en `valoracion`, nombre, límite «no significativo» o None, métrica LTM de la empresa, ¿es múltiplo de EV?)
MULTIPLOS: tuple[tuple[str, str, float | None, str, bool], ...] = (
    ("ev_ebitda", "EV / EBITDA", 50.0, "ebitda", True),
    ("per", "PER", 75.0, "beneficio_neto", False),
    ("ev_ventas", "EV / Ventas", None, "ingresos", True),
    ("p_fcf", "P / FCF", 75.0, "fcf_tras_sbc", False),
)
PARA_EL_PRECIO = ("ev_ebitda", "per")
MINIMO_COMPARABLES = 3  # con menos, la mediana no es representativa y no entra en el precio objetivo


def significativo(valor: float | None, limite: float | None) -> bool:
    return valor is not None and math.isfinite(valor) and valor > 0 and (limite is None or valor <= limite)


def estadisticas(comparables: list[dict]) -> dict[str, dict]:
    """Por múltiplo: mediana, mínimo, máximo y nº de comparables que entran (`comparables[i]["multiplos"]`)."""
    salida = {}
    for clave, _, limite, _, _ in MULTIPLOS:
        validos = [c["multiplos"].get(clave) for c in comparables if significativo(c["multiplos"].get(clave), limite)]
        salida[clave] = {
            "mediana": statistics.median(validos) if validos else None, "minimo": min(validos, default=None),
            "maximo": max(validos, default=None), "n": len(validos),
        }
    return salida


def valor_implicito(stats: dict[str, dict], fundamentales_ltm: dict, dfn: float, minoritarios: float,
                    acciones: float) -> dict[str, float | None]:
    """Precio por acción implícito en la mediana de cada múltiplo (None si falta la mediana o la métrica)."""
    salida = {}
    for clave, _, _, metrica, de_ev in MULTIPLOS:
        mediana, valor = stats[clave]["mediana"], fundamentales_ltm.get(metrica)
        if mediana is None or valor is None or valor <= 0 or stats[clave]["n"] < MINIMO_COMPARABLES:
            salida[clave] = None
        elif de_ev:
            salida[clave] = (mediana * valor - dfn - minoritarios) / acciones
        else:
            salida[clave] = mediana * valor / acciones
    return salida


def valor_por_multiplos(implicitos: dict[str, float | None]) -> float | None:
    usados = [implicitos[k] for k in PARA_EL_PRECIO if implicitos.get(k) is not None and implicitos[k] > 0]
    return statistics.fmean(usados) if usados else None


def rango_por_multiplos(comparables: list[dict], fundamentales_ltm: dict, dfn: float, minoritarios: float,
                        acciones: float) -> tuple[float | None, float | None]:
    """Rango del valor por múltiplos: cuartiles inferior y superior de EV/EBITDA y PER de los comparables."""
    from .historico import cuantil

    bajos, altos = [], []
    for clave, _, limite, metrica, de_ev in MULTIPLOS:
        if clave not in PARA_EL_PRECIO:
            continue
        validos = [c["multiplos"][clave] for c in comparables if significativo(c["multiplos"].get(clave), limite)]
        valor = fundamentales_ltm.get(metrica)
        if len(validos) < MINIMO_COMPARABLES or not valor or valor <= 0:
            continue
        for q, destino in ((0.25, bajos), (0.75, altos)):
            m = cuantil(validos, q)
            destino.append((m * valor - dfn - minoritarios) / acciones if de_ev else m * valor / acciones)
    return (statistics.fmean(bajos) if bajos else None, statistics.fmean(altos) if altos else None)


def suma_de_partes(resultado_por_segmento: dict[str, float], ebit_consolidado: float | None, multiplos: dict[str, float],
                   multiplo_defecto: float | None, deuda_neta_ajustada: float, minoritarios: float, acciones: float) -> dict | None:
    """Suma de partes (R14) sobre el resultado operativo de cada segmento declarado (ASC 280).

    Patrón de FinRobot `engine/compute/operators/sotp.py` (`value_segment`, `compute_sotp_breakdown`: suelo por
    segmentos × múltiplo − deuda neta; Apache-2.0). Cambios: múltiplo EV/EBIT por segmento (el del analista o, por
    defecto, la mediana EV/EBIT de sus comparables) y una línea de **costes no asignados** = EBIT consolidado − Σ
    resultado de los segmentos, valorada al múltiplo por defecto (como el «Group Holding» de los informes de
    referencia): sin ella, la suma de partes sobrevaloraría a las empresas con costes corporativos.
    """
    if not resultado_por_segmento or not acciones:
        return None
    filas, ev = [], 0.0
    for nombre, resultado in resultado_por_segmento.items():
        m = multiplos.get(nombre, multiplo_defecto)
        if m is None:
            return None
        filas.append({"nombre": nombre, "resultado": resultado, "multiplo": m, "ev": resultado * m})
        ev += resultado * m
    no_asignado = None
    if ebit_consolidado is not None:
        no_asignado = ebit_consolidado - sum(resultado_por_segmento.values())
        m = multiplos.get("Costes no asignados", multiplo_defecto)
        if m is None:
            return None
        filas.append({"nombre": "Costes no asignados", "resultado": no_asignado, "multiplo": m, "ev": no_asignado * m})
        ev += no_asignado * m
    equity = ev - deuda_neta_ajustada - minoritarios
    return {"filas": filas, "ev": ev, "equity": equity, "por_accion": equity / acciones, "no_asignado": no_asignado}


def mediana_comparables(comparables: list[dict], clave: str, limite: float | None) -> float | None:
    """Mediana de un múltiplo de los comparables con las mismas reglas (sin negativos ni no significativos)."""
    validos = [c["multiplos"].get(clave) for c in comparables if significativo(c["multiplos"].get(clave), limite)]
    return statistics.median(validos) if len(validos) >= MINIMO_COMPARABLES else None
