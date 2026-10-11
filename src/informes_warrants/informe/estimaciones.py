"""Estimaciones que el analista puede ajustar (bloque editable).

Son los supuestos que mueven la proyección y el DCF. El resto de cifras del informe son
históricas y no se tocan. Origen de cada supuesto y de su valor por defecto:
  - Horizonte de 3 años + perpetuidad, g = 2,5 %: informe de referencia (docs/estructura-informe.md, §7).
  - Rf = 4,5 %, ERP = 5,5 % y tasa fiscal = 21 %: valores por defecto de financial-research-analyst-agent
    `src/tools/dcf_model.py` (_DEFAULT_RISK_FREE, _EQUITY_RISK_PREMIUM y tipo federal de EEUU).
  - Crecimiento de ventas, márgenes, D&A, capex y circulante: media histórica de 3-5 años que calcula
    la capa 2 (edgar_analytics `multi_period_analysis`); la beta, del histórico de precios (capa 1).
"""

from dataclasses import dataclass, field

UMBRAL_COMPRAR = 0.15  # potencial mínimo para proponer «Comprar»
UMBRAL_VENDER = -0.10  # potencial máximo para proponer «Vender»


@dataclass
class Estimaciones:
    crecimiento_ventas: list[float] = field(default_factory=lambda: [0.05, 0.05, 0.05])
    margen_ebitda: list[float] = field(default_factory=lambda: [0.20, 0.20, 0.20])
    da_sobre_ventas: float = 0.04
    capex_sobre_ventas: float = 0.05
    circulante_sobre_ventas: float = 0.10  # inversión en circulante sobre el incremento de ventas
    tasa_fiscal: float = 0.21
    rf: float = 0.045
    erp: float = 0.055
    beta: float = 1.0
    coste_deuda: float = 0.05
    g: float = 0.025
    peso_dcf: float = 0.5  # peso del DCF frente a múltiplos en el precio objetivo

    def validar(self) -> list[str]:
        """Errores de coherencia; una lista vacía significa que se pueden usar."""
        errores = []
        if len(self.crecimiento_ventas) != len(self.margen_ebitda):
            errores.append("Crecimiento de ventas y margen EBITDA deben cubrir los mismos años.")
        for nombre in ("da_sobre_ventas", "capex_sobre_ventas", "tasa_fiscal", "rf", "erp", "coste_deuda", "peso_dcf"):
            if not 0 <= getattr(self, nombre) <= 1:
                errores.append(f"{nombre} debe estar entre 0 y 1.")
        if any(not -0.5 <= c <= 1 for c in self.crecimiento_ventas):
            errores.append("El crecimiento anual de ventas debe estar entre -50 % y 100 %.")
        if any(not -1 <= m <= 1 for m in self.margen_ebitda):
            errores.append("El margen EBITDA debe estar entre -100 % y 100 %.")
        if not 0 < self.beta <= 4:
            errores.append("La beta debe estar entre 0 y 4.")
        if self.g >= self.coste_equity():
            errores.append("g debe ser menor que el coste del capital.")
        return errores

    def coste_equity(self) -> float:
        return self.rf + self.beta * self.erp


def recomendacion_propuesta(potencial: float) -> str:
    """Recomendación mecánica por potencial; el analista la confirma o la cambia."""
    if potencial >= UMBRAL_COMPRAR:
        return "Comprar"
    if potencial <= UMBRAL_VENDER:
        return "Vender"
    return "Mantener"
