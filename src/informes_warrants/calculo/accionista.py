"""Valoración por los flujos del accionista (P19): descuento de dividendos por etapas e ingreso residual.

Adaptado de FinRobot `engine/compute/operators/ddm.py` y `residual_income.py` (Apache-2.0). Cambios:
- DDM: los dividendos por acción de los años explícitos son los de la proyección del informe (BPA × pay-out,
  `calculo/proyeccion.py`), no unas tasas de crecimiento aparte; valor terminal de Gordon sobre el último, con g.
- Ingreso residual de una etapa (P/VC justificado): VC por acción × (ROE − g) / (Ke − g), la misma fórmula que el
  valor contable justificado de las plantillas sectoriales (`valoracion_sectorial.multiplo_justo`); ROE sostenible =
  la media de los ejercicios (o el del analista), no el de un año pico.
- Las mismas salvaguardas que FinRobot: Ke − g de al menos 1,5 puntos (`MIN_GORDON_SPREAD`), sin dividendos o con
  valor contable no positivo no hay valor (None), y nunca un valor por acción negativo.

    DDM = Σ DPA_t / (1 + Ke)^t + DPA_n × (1 + g) / (Ke − g) / (1 + Ke)^n
    Ingreso residual = VC por acción × [1 + (ROE − Ke) / (Ke − g)]
"""

from .valoracion_sectorial import multiplo_justo

DIFERENCIAL_MINIMO = 0.015  # Ke − g mínimo (FinRobot `MIN_GORDON_SPREAD`): por debajo, la perpetuidad se dispara


def ddm_por_etapas(dpa: list[float], ke: float, g: float) -> dict | None:
    """Valor por acción de los dividendos proyectados y de su valor terminal; None si no hay dividendos o Ke − g < 1,5 pp."""
    if not dpa or dpa[-1] is None or dpa[-1] <= 0 or ke - g < DIFERENCIAL_MINIMO:
        return None
    va = [d / (1 + ke) ** (t + 1) for t, d in enumerate(dpa)]
    terminal = dpa[-1] * (1 + g) / (ke - g)
    va_terminal = terminal / (1 + ke) ** len(dpa)
    return {"valor": sum(va) + va_terminal, "va_dividendos": sum(va), "va_terminal": va_terminal, "dpa": list(dpa), "ke": ke, "g": g}


def ingreso_residual(valor_contable_por_accion: float | None, roe: float | None, ke: float, g: float) -> dict | None:
    """Valor por acción del ingreso residual de una etapa; None sin valor contable positivo, sin ROE o si no da valor."""
    if not valor_contable_por_accion or valor_contable_por_accion <= 0 or roe is None or ke - g < DIFERENCIAL_MINIMO:
        return None
    multiplo = multiplo_justo(roe, ke, g)
    if multiplo is None:
        return None
    return {"valor": valor_contable_por_accion * multiplo, "multiplo": multiplo, "roe": roe, "ke": ke, "g": g,
            "valor_contable_por_accion": valor_contable_por_accion}
