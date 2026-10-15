"""Estimaciones que el analista puede ajustar (bloque editable) y sus escenarios.

Son los supuestos que mueven la proyección, el BPA estimado y el DCF. El resto de cifras del informe
son históricas y no se tocan. Origen de cada supuesto y de su valor por defecto:
  - Horizonte: 5 años explícitos + 5 de convergencia lineal hacia g (idea de financial-research-analyst-
    agent `dcf_model.py`); g = 2,5 % (informe de referencia, docs/estructura-informe.md, §7).
  - Rf: bono del Tesoro a 10 años (FRED DGS10, ingesta/mercado.py); ERP = 5,5 % y tasa fiscal = 21 %:
    valores por defecto de financial-research-analyst-agent `src/tools/dcf_model.py`.
  - Crecimiento, márgenes, D&A, capex, resultado financiero, minoritarios, variación de acciones y
    pay-out: medias históricas de 3 años (informe/construir.py); la beta, del histórico de precios.
  - Escenarios: base = estimaciones; pesimista y optimista = base ∓ 1 desviación típica histórica del
    crecimiento y del margen (últimos 3 ejercicios + LTM), acotada entre 2 y 5 puntos (crecimiento) y entre
    1 y 3 puntos (margen) para que un año atípico (p. ej. el rebote de 2021) no la desborde.
    Probabilidades 25/50/25. Todo editable.
"""

from dataclasses import dataclass, field, replace

UMBRAL_COMPRAR = 0.15  # potencial mínimo para proponer «Comprar»
UMBRAL_VENDER = -0.10  # potencial máximo para proponer «Vender»
ANIOS_EXPLICITOS = 5
PROBABILIDADES = (0.25, 0.50, 0.25)  # pesimista, base, optimista
# Peso de cada método en el precio objetivo (calculo/sintesis.py); se renormalizan entre los que tienen valor.
PESOS_POR_DEFECTO = {"DCF": 0.5, "DCF por escenarios": 0.0, "Comparables": 0.5, "Múltiplos históricos": 0.0, "Suma de partes": 0.0,
                     "DDM": 0.0, "Ingreso residual": 0.0}  # P19: complementarios (peso 0 hasta que el analista lo cambie)
SIGMA_MIN_CRECIMIENTO, SIGMA_MIN_MARGEN = 0.02, 0.01
SIGMA_MAX_CRECIMIENTO, SIGMA_MAX_MARGEN = 0.05, 0.03


@dataclass
class Estimaciones:
    crecimiento_ventas: list[float] = field(default_factory=lambda: [0.05] * ANIOS_EXPLICITOS)
    margen_ebitda: list[float] = field(default_factory=lambda: [0.20] * ANIOS_EXPLICITOS)
    da_sobre_ventas: float = 0.04
    capex_sobre_ventas: float = 0.05
    circulante_sobre_ventas: float = 0.10  # inversión en circulante sobre el incremento de ventas
    tasa_fiscal: float = 0.21
    rf: float = 0.045
    erp: float = 0.055
    beta: float = 1.0
    coste_deuda: float = 0.05
    g: float = 0.025
    pesos: dict[str, float] = field(default_factory=lambda: dict(PESOS_POR_DEFECTO))  # métodos del precio objetivo
    precio_objetivo_analista: float | None = None  # si se fija, sustituye al calculado; el potencial lo recalcula el código
    # Plantillas sectoriales (B2): ROE (ROTE, NII) sostenible del valor contable justificado; None = media de los ejercicios
    rentabilidad_sostenible: float | None = None
    # Motor de valoración (B1): entradas del analista del libro (crecimientos y márgenes por segmento, % del valor terminal
    # por perpetuidad, convención de descuento, LBO); vacío = los valores por defecto del motor, marcados «Revisar»
    motor: dict = field(default_factory=dict)
    anios_convergencia: int = 5  # años tras los explícitos en los que el crecimiento converge linealmente a g
    # Proyección hasta el BPA (calculo/proyeccion.py)
    resultado_financiero_sobre_ventas: float = 0.0  # (BAI − EBIT) / ventas: intereses netos y otros resultados
    cuota_minoritarios: float = 0.0  # parte del beneficio después de impuestos que va a minoritarios
    variacion_acciones: float = 0.0  # variación anual de las acciones diluidas (negativa = recompras netas)
    payout: float = 0.0  # dividendos / beneficio neto
    # Proyección del flujo de caja y del balance (R12)
    sbc_sobre_ventas: float = 0.0  # remuneración en acciones / ventas
    recompras_sobre_fcf: float = 0.0  # recompras / FCF tras remuneración en acciones (si el FCF es positivo)
    multiplos_sotp: dict[str, float] = field(default_factory=dict)  # EV/EBIT por segmento (R14); vacío = mediana de comparables
    # Calendario de catalizadores del analista (A4): [{"evento", "fecha" (AAAA-MM-DD o vacía), "base"}]; vacío = borrador del SaaS
    calendario: list[dict] = field(default_factory=list)
    # Catalizadores del analista (A4): [{"resumen", "cita"}]; vacío = la propuesta de la IA sobre el MD&A
    catalizadores: list[dict] = field(default_factory=list)

    def validar(self) -> list[str]:
        """Errores de coherencia; una lista vacía significa que se pueden usar."""
        errores = []
        if len(self.crecimiento_ventas) != len(self.margen_ebitda) or not self.crecimiento_ventas:
            errores.append("Crecimiento de ventas y margen EBITDA deben cubrir los mismos años (al menos uno).")
        for nombre in ("da_sobre_ventas", "capex_sobre_ventas", "tasa_fiscal", "rf", "erp", "coste_deuda", "cuota_minoritarios",
                       "sbc_sobre_ventas"):
            if not 0 <= getattr(self, nombre) <= 1:
                errores.append(f"{nombre} debe estar entre 0 y 1.")
        if any(not -0.5 <= c <= 1 for c in self.crecimiento_ventas):
            errores.append("El crecimiento anual de ventas debe estar entre -50 % y 100 %.")
        if any(not -1 <= m <= 1 for m in self.margen_ebitda):
            errores.append("El margen EBITDA debe estar entre -100 % y 100 %.")
        if not 0 < self.beta <= 4:
            errores.append("La beta debe estar entre 0 y 4.")
        if not 0 <= self.anios_convergencia <= 15:
            errores.append("Los años de convergencia deben estar entre 0 y 15.")
        if not -0.5 <= self.resultado_financiero_sobre_ventas <= 0.5:
            errores.append("El resultado financiero sobre ventas debe estar entre -50 % y 50 %.")
        if not -0.2 <= self.variacion_acciones <= 0.2:
            errores.append("La variación anual de acciones debe estar entre -20 % y 20 %.")
        if not 0 <= self.payout <= 3:
            errores.append("El pay-out debe estar entre 0 y 300 %.")
        if not 0 <= self.recompras_sobre_fcf <= 3:
            errores.append("Las recompras sobre el FCF deben estar entre 0 y 300 %.")
        if any(p < 0 for p in self.pesos.values()) or not sum(self.pesos.values()):
            errores.append("Los pesos de los métodos deben ser positivos y no sumar cero.")
        if any(m <= 0 for m in self.multiplos_sotp.values()):
            errores.append("Los múltiplos de la suma de partes deben ser positivos.")
        if self.precio_objetivo_analista is not None and self.precio_objetivo_analista <= 0:
            errores.append("El precio objetivo del analista debe ser positivo.")
        if self.rentabilidad_sostenible is not None and not -1 < self.rentabilidad_sostenible < 1:
            errores.append("La rentabilidad sostenible debe estar entre -100 % y 100 %.")
        errores += self._validar_motor()
        if self.g >= self.coste_equity():
            errores.append("g debe ser menor que el coste del capital.")
        return errores

    def _validar_motor(self) -> list[str]:
        m, errores = self.motor or {}, []
        if any(not -0.5 <= x <= 1 for v in (m.get("crecimientos") or {}).values() for x in v):
            errores.append("Motor: el crecimiento anual de cada segmento debe estar entre -50 % y 100 %.")
        if any(not -1 <= x <= 1 for v in (m.get("margenes") or {}).values() for x in v):
            errores.append("Motor: el margen EBIT de cada segmento debe estar entre -100 % y 100 %.")
        if m.get("pct_perpetuidad") is not None and not 0 <= m["pct_perpetuidad"] <= 1:
            errores.append("Motor: el peso del valor terminal por perpetuidad debe estar entre 0 y 100 %.")
        if m.get("convencion") is not None and m["convencion"] not in (1, 2):
            errores.append("Motor: la convención de descuento es 1 (mitad de año) o 2 (fin de año).")
        return errores

    def coste_equity(self) -> float:
        return self.rf + self.beta * self.erp


@dataclass
class Escenarios:
    """Tres juegos de estimaciones con su probabilidad; el analista puede editar cualquiera."""

    pesimista: Estimaciones
    base: Estimaciones
    optimista: Estimaciones
    probabilidades: tuple[float, float, float] = PROBABILIDADES
    # Qué tendría que pasar en cada escenario (R9): texto del analista; vacío = descripción automática de sus supuestos
    desencadenantes: dict[str, str] = field(default_factory=dict)

    def items(self) -> tuple[tuple[str, Estimaciones, float], ...]:
        p = self.probabilidades
        return (("Pesimista", self.pesimista, p[0]), ("Base", self.base, p[1]), ("Optimista", self.optimista, p[2]))

    def validar(self) -> list[str]:
        errores = [f"{n}: {e}" for n, est, _ in self.items() for e in est.validar()]
        if any(p < 0 for p in self.probabilidades) or abs(sum(self.probabilidades) - 1) > 1e-6:
            errores.append("Las probabilidades deben ser positivas y sumar 100 %.")
        return errores


def escenarios_por_defecto(base: Estimaciones, sigma_crecimiento: float | None, sigma_margen: float | None) -> Escenarios:
    """Pesimista y optimista: base ∓ 1 desviación típica histórica (con mínimo) del crecimiento y del margen."""
    dc = min(max(sigma_crecimiento or 0.0, SIGMA_MIN_CRECIMIENTO), SIGMA_MAX_CRECIMIENTO)
    dm = min(max(sigma_margen or 0.0, SIGMA_MIN_MARGEN), SIGMA_MAX_MARGEN)

    def desplazar(signo):
        return replace(base, crecimiento_ventas=[round(max(-0.5, min(1.0, c + signo * dc)), 4) for c in base.crecimiento_ventas],
                       margen_ebitda=[round(max(-1.0, min(1.0, m + signo * dm)), 4) for m in base.margen_ebitda],
                       precio_objetivo_analista=None)

    return Escenarios(desplazar(-1), base, desplazar(+1))


def recomendacion_propuesta(potencial: float) -> str:
    """Recomendación mecánica por potencial; el analista la confirma o la cambia."""
    if potencial >= UMBRAL_COMPRAR:
        return "Comprar"
    if potencial <= UMBRAL_VENDER:
        return "Vender"
    return "Mantener"
