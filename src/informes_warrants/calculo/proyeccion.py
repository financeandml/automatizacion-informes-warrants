"""Proyección de la cuenta de resultados hasta el BPA en los años explícitos (función pura).

Ningún repo base la resolvía (inventario, «Necesidades sin resolver» n.º 1): edgar_analytics solo
proyecta ingresos con un ARIMA a un paso, y FinRobot Equity hace crecer el BPA en proporción a las
ventas, sin intereses, impuestos ni acciones. Aquí se construye línea a línea con las mismas ventas,
EBITDA, D&A y EBIT que el DCF (calculo/dcf.py `proyeccion`), para que ambos sean coherentes:

  BAI          = EBIT + resultado financiero (ventas · resultado_financiero_sobre_ventas)
  Impuestos    = BAI · tasa fiscal  (BAI > 0; si es negativo, sin crédito fiscal)
  Beneficio    = (BAI − impuestos) · (1 − cuota de minoritarios)
  Acciones     = acciones diluidas del LTM · (1 + variación anual)^t
  BPA          = beneficio / acciones ; DPA = BPA · pay-out
  FCF accionista = FCFF + resultado financiero · (1 − t)   (sin nueva deuda neta)
"""

from dataclasses import dataclass

from ..informe.estimaciones import Estimaciones
from .dcf import proyeccion as _lineas_operativas


@dataclass(frozen=True)
class AnioProyectado:
    ventas: float
    ebitda: float
    amortizacion: float
    ebit: float
    resultado_financiero: float
    bai: float
    impuestos: float
    minoritarios: float
    beneficio_neto: float
    acciones: float
    bpa: float
    dpa: float
    fcff: float
    fcf_accionista: float

    @property
    def fcf_por_accion(self) -> float:
        return self.fcf_accionista / self.acciones


def proyectar(est: Estimaciones, ingresos_base: float, acciones_base: float) -> list[AnioProyectado]:
    """Años explícitos de la proyección (los de convergencia solo sirven al DCF)."""
    anios = []
    for t, linea in enumerate(_lineas_operativas(est, ingresos_base)[:len(est.crecimiento_ventas)], start=1):
        financiero = linea["ventas"] * est.resultado_financiero_sobre_ventas
        bai = linea["ebit"] + financiero
        impuestos = max(bai, 0.0) * est.tasa_fiscal
        minoritarios = (bai - impuestos) * est.cuota_minoritarios
        beneficio = bai - impuestos - minoritarios
        acciones = acciones_base * (1 + est.variacion_acciones) ** t
        bpa = beneficio / acciones
        anios.append(AnioProyectado(
            ventas=linea["ventas"], ebitda=linea["ebitda"], amortizacion=linea["amortizacion"], ebit=linea["ebit"],
            resultado_financiero=financiero, bai=bai, impuestos=impuestos, minoritarios=minoritarios, beneficio_neto=beneficio,
            acciones=acciones, bpa=bpa, dpa=bpa * est.payout, fcff=linea["fcff"],
            fcf_accionista=linea["fcff"] + financiero * (1 - est.tasa_fiscal)))
    return anios
