"""Proyección de los tres estados en los años explícitos (función pura): resultados hasta el BPA, flujo de caja
y balance resumido.

Ningún repo base la resolvía (inventario, «Necesidades sin resolver» n.º 1): edgar_analytics solo
proyecta ingresos con un ARIMA a un paso, y FinRobot Equity hace crecer el BPA en proporción a las
ventas, sin intereses, impuestos ni acciones. Aquí se construye línea a línea con las mismas ventas,
EBITDA, D&A y EBIT que el DCF (calculo/dcf.py `proyeccion`), para que todo sea coherente.

Cuenta de resultados
  BAI          = EBIT + resultado financiero (ventas · resultado_financiero_sobre_ventas)
  Impuestos    = BAI · tasa fiscal  (BAI > 0; si es negativo, sin crédito fiscal)
  Minoritarios = (BAI − impuestos) · cuota de minoritarios ; Beneficio = BAI − impuestos − minoritarios
  Acciones     = acciones diluidas del LTM · (1 + variación anual)^t ; BPA = beneficio / acciones ; DPA = BPA · pay-out
  FCF accionista = FCFF + resultado financiero · (1 − t)   (sin nueva deuda neta)
Flujo de caja (R12; contabilidad real: la remuneración en acciones no sale de caja)
  Flujo operativo = (BAI − impuestos) + D&A + SBC − Δcirculante
  FCF tras SBC    = flujo operativo − capex − SBC   (= el FCF del accionista, base de la valoración)
  Dividendos      = beneficio · pay-out ; Recompras = FCF tras SBC · recompras_sobre_fcf (si es positivo)
  Δcaja           = flujo operativo − capex − dividendos − recompras   (la deuda se mantiene)
Balance resumido (cuadra por construcción)
  Caja_t = caja_t−1 + Δcaja ; Deuda constante ; Patrimonio_t = patrimonio_t−1 + beneficio + SBC − dividendos − recompras
  Minoritarios_t = minoritarios_t−1 + su parte del beneficio
  Activos operativos netos_t = AON_t−1 + capex − D&A + Δcirculante
  Identidad: caja + AON = deuda + patrimonio + minoritarios (comprobada en los tests)
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
    # Flujo de caja y balance (R12); None si no se pasó el balance de partida
    sbc: float = 0.0
    flujo_operativo: float = 0.0
    capex: float = 0.0
    fcf_tras_sbc: float = 0.0
    dividendos: float = 0.0
    recompras: float = 0.0
    variacion_caja: float = 0.0
    caja: float | None = None
    activos_operativos_netos: float | None = None
    deuda: float | None = None
    patrimonio: float | None = None
    minoritarios_balance: float | None = None

    @property
    def fcf_por_accion(self) -> float:
        return self.fcf_accionista / self.acciones

    @property
    def dfn(self) -> float | None:
        return None if self.deuda is None or self.caja is None else self.deuda - self.caja

    @property
    def dfn_ebitda(self) -> float | None:
        return self.dfn / self.ebitda if self.dfn is not None and self.ebitda > 0 else None  # con EBITDA ≤ 0, n.s.

    @property
    def retribucion(self) -> float:
        return self.dividendos + self.recompras


def activos_operativos_netos(caja: float, deuda: float, patrimonio: float, minoritarios: float) -> float:
    """Activos operativos netos = patrimonio + minoritarios + deuda − caja: la partida que cierra el balance resumido."""
    return patrimonio + minoritarios + deuda - caja


def balance_inicial(caja: float | None, inversiones_cp: float | None, deuda: float, patrimonio: float | None,
                    minoritarios: float | None) -> dict | None:
    """Balance del LTM del que parte la proyección (None si falta la caja o el patrimonio)."""
    if caja is None or patrimonio is None:
        return None
    caja_total = caja + (inversiones_cp or 0.0)
    return {"caja": caja_total, "deuda": deuda, "patrimonio": patrimonio, "minoritarios": minoritarios or 0.0,
            "activos_operativos_netos": activos_operativos_netos(caja_total, deuda, patrimonio, minoritarios or 0.0)}


def proyectar(est: Estimaciones, ingresos_base: float, acciones_base: float, balance: dict | None = None) -> list[AnioProyectado]:
    """Años explícitos (los de convergencia solo sirven al DCF).

    `balance` (opcional, del LTM): caja (con inversiones a corto), deuda, patrimonio, minoritarios.
    """
    anios = []
    caja = deuda = patrimonio = minoritarios_bal = aon = None
    if balance:
        caja, deuda = balance["caja"], balance["deuda"]
        patrimonio, minoritarios_bal = balance["patrimonio"], balance.get("minoritarios") or 0.0
        aon = activos_operativos_netos(caja, deuda, patrimonio, minoritarios_bal)
    previo = ingresos_base
    for t, linea in enumerate(_lineas_operativas(est, ingresos_base)[:len(est.crecimiento_ventas)], start=1):
        ventas = linea["ventas"]
        financiero = ventas * est.resultado_financiero_sobre_ventas
        bai = linea["ebit"] + financiero
        impuestos = max(bai, 0.0) * est.tasa_fiscal
        minoritarios = (bai - impuestos) * est.cuota_minoritarios
        beneficio = bai - impuestos - minoritarios
        acciones = acciones_base * (1 + est.variacion_acciones) ** t
        bpa = beneficio / acciones
        sbc, capex = ventas * est.sbc_sobre_ventas, ventas * est.capex_sobre_ventas
        circulante = (ventas - previo) * est.circulante_sobre_ventas
        flujo_operativo = (bai - impuestos) + linea["amortizacion"] + sbc - circulante
        fcf_tras_sbc = flujo_operativo - capex - sbc
        dividendos = beneficio * est.payout
        recompras = max(fcf_tras_sbc, 0.0) * est.recompras_sobre_fcf
        variacion_caja = flujo_operativo - capex - dividendos - recompras
        if balance:
            caja += variacion_caja
            patrimonio += beneficio + sbc - dividendos - recompras
            minoritarios_bal += minoritarios
            aon += capex - linea["amortizacion"] + circulante
        anios.append(AnioProyectado(
            ventas=ventas, ebitda=linea["ebitda"], amortizacion=linea["amortizacion"], ebit=linea["ebit"],
            resultado_financiero=financiero, bai=bai, impuestos=impuestos, minoritarios=minoritarios, beneficio_neto=beneficio,
            acciones=acciones, bpa=bpa, dpa=bpa * est.payout, fcff=linea["fcff"],
            fcf_accionista=linea["fcff"] + financiero * (1 - est.tasa_fiscal),
            sbc=sbc, flujo_operativo=flujo_operativo, capex=capex, fcf_tras_sbc=fcf_tras_sbc, dividendos=dividendos,
            recompras=recompras, variacion_caja=variacion_caja, caja=caja, activos_operativos_netos=aon, deuda=deuda,
            patrimonio=patrimonio, minoritarios_balance=minoritarios_bal))
        previo = ventas
    return anios
