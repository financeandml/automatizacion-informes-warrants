"""DCF de flujos libres para la empresa (FCFF) y beta, como funciones puras.

Patrón de financial-research-analyst-agent `src/tools/dcf_model.py` (WACC, sensibilidad), con sus
errores corregidos (ver docs/inventario/README.md): resta la deuda neta al EV, proyecta con las
estimaciones del analista (no con crecimientos de Yahoo) y no emite valores infinitos.

  FCFF_t   = EBIT_t · (1 − t) + D&A_t − capex_t − ΔCirculante_t
  Ke       = Rf + β · ERP ;  Kd neto = coste de la deuda · (1 − t)
  WACC     = Ke · E/(D+E) + Kd neto · D/(D+E)   (pesos a valor de mercado)
  Terminal = FCFF_n · (1 + g) / (WACC − g)
  Equity   = EV − DFN − minoritarios ; valor por acción = Equity / acciones
"""

from dataclasses import dataclass

from ..informe.estimaciones import Estimaciones


@dataclass(frozen=True)
class ResultadoDCF:
    wacc: float
    ke: float
    flujos: list[float]  # FCFF proyectados
    ingresos: list[float]
    valor_terminal: float
    ev: float
    equity: float
    valor_por_accion: float
    sensibilidad: dict[tuple[float, float], float]  # (wacc, g) → valor por acción


def wacc(est: Estimaciones, capitalizacion: float, deuda: float) -> tuple[float, float]:
    ke = est.coste_equity()
    peso_deuda = deuda / (deuda + capitalizacion) if deuda + capitalizacion > 0 else 0.0
    return ke * (1 - peso_deuda) + est.coste_deuda * (1 - est.tasa_fiscal) * peso_deuda, ke


def _valor(est, ingresos_base, w, g, dfn, minoritarios, acciones):
    ingresos, flujos, previo = [], [], ingresos_base
    for crecimiento, margen in zip(est.crecimiento_ventas, est.margen_ebitda, strict=True):
        ventas = previo * (1 + crecimiento)
        ebitda = ventas * margen
        da = ventas * est.da_sobre_ventas
        ebit = ebitda - da
        fcff = ebit * (1 - est.tasa_fiscal) + da - ventas * est.capex_sobre_ventas - (ventas - previo) * est.circulante_sobre_ventas
        ingresos.append(ventas)
        flujos.append(fcff)
        previo = ventas
    descuento = [(1 + w) ** (i + 1) for i in range(len(flujos))]
    terminal = flujos[-1] * (1 + g) / (w - g)
    ev = sum(f / d for f, d in zip(flujos, descuento, strict=True)) + terminal / descuento[-1]
    equity = ev - dfn - minoritarios
    return ingresos, flujos, terminal, ev, equity, equity / acciones


def dcf(est: Estimaciones, ingresos_base: float, dfn: float, deuda: float, minoritarios: float, acciones: float,
        capitalizacion: float) -> ResultadoDCF:
    errores = est.validar()
    if errores:
        raise ValueError("Estimaciones no válidas: " + " ".join(errores))
    w, ke = wacc(est, capitalizacion, deuda)
    if est.g >= w:
        raise ValueError(f"g ({est.g:.2%}) debe ser menor que el WACC ({w:.2%})")
    ingresos, flujos, terminal, ev, equity, por_accion = _valor(est, ingresos_base, w, est.g, dfn, minoritarios, acciones)
    sensibilidad = {}
    for dw in (-0.01, -0.005, 0.0, 0.005, 0.01):
        for dg in (-0.005, 0.0, 0.005):
            if est.g + dg < w + dw:  # nunca valores infinitos ni negativos por g ≥ WACC
                sensibilidad[(round(w + dw, 4), round(est.g + dg, 4))] = _valor(
                    est, ingresos_base, w + dw, est.g + dg, dfn, minoritarios, acciones)[5]
    return ResultadoDCF(w, ke, flujos, ingresos, terminal, ev, equity, por_accion, sensibilidad)


def beta(rent_activo, rent_indice) -> float:
    """Beta = cov(activo, índice) / var(índice) sobre rentabilidades del mismo periodo (p. ej. semanales)."""
    import numpy as np

    a, i = np.asarray(rent_activo, dtype=float), np.asarray(rent_indice, dtype=float)
    if len(a) != len(i) or len(a) < 20:
        raise ValueError("Se necesitan al menos 20 rentabilidades alineadas")
    return float(np.cov(a, i, ddof=1)[0, 1] / np.var(i, ddof=1))
