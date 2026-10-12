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
