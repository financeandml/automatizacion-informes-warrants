"""Motor matemático: definiciones únicas de las métricas del informe (plantilla general).

Todas las fórmulas del proyecto están aquí y solo aquí; operan sobre partidas canónicas del
normalizador (calculo/normalizador.py). Definiciones (corrigen las de edgar_analytics, cuyo
`EBITDA (standard)` incluye resultados no operativos; ver docs/inventario/README.md):

  EBIT          = resultado operativo declarado (OperatingIncomeLoss)
  EBITDA        = EBIT + amortizaciones del estado de flujos
  FCF           = flujo de caja operativo − capex
  FCF tras SBC  = FCF − remuneración en acciones (el flujo operativo la suma como gasto no monetario;
                  aquí se trata como coste, criterio institucional habitual). Base de P/FCF y FCF yield.
  DFN           = deuda CP + deuda LP − caja − inversiones financieras CP   (negativa = caja neta)
  Capital empl. = activo total − pasivo corriente
  Capital inv.  = patrimonio + minoritarios + DFN
  Tipo efectivo = impuestos / BAI
  ROIC          = EBIT · (1 − tipo efectivo) / capital invertido
  ROCE          = EBIT / capital empleado
  Ajustes EV    = preferentes + pensiones (pasivo neto) + patrimonio temporal + arrendamientos financieros
                  (estos, solo si la deuda declarada no los incluye ya). Sin arrendamientos OPERATIVOS: en US
                  GAAP su coste está dentro del EBITDA (sumarlos descuadraría el EV/EBITDA). Idea de FinRobot
                  `multiples.calculate_ev` y `audit/ev_bridge` (Apache-2.0).
  DFN ajustada  = DFN + ajustes EV (lo que se resta al EV para llegar al valor del patrimonio)
  EV            = market cap + DFN ajustada + minoritarios

Ningún valor se inventa: si falta un dato, la métrica es None y el informe muestra «n.d.».
"""

from dataclasses import dataclass

from .normalizador import EstadosNormalizados


def _div(a, b):
    return None if a is None or b in (None, 0) else a / b


def ratio_de_sumas(pares: list[tuple[float, float]]) -> float | None:
    """Σ numerador / Σ denominador (None sin datos o si el denominador suma ≤ 0). Para supuestos sobre ventas: con
    ventas pequeñas en algún año, la media de ratios se dispara (IOVA: intereses de la caja > 20 % de las ventas)."""
    denominador = sum(d for _, d in pares)
    return sum(n for n, _ in pares) / denominador if pares and denominador > 0 else None


def _suma(*valores):
    return None if any(v is None for v in valores) else sum(valores)


@dataclass(frozen=True)
class Mercado:
    """Datos de mercado a la fecha del informe (capa 1)."""

    precio: float
    acciones: float  # acciones en circulación (portada del último filing)
    fecha: str

    @property
    def capitalizacion(self) -> float:
        return self.precio * self.acciones


def fundamentales(e: EstadosNormalizados, ejercicio: int) -> dict[str, float | None]:
    """Métricas de un ejercicio que no dependen de la cotización."""
    v = lambda p: e.valor(p, ejercicio)  # noqa: E731
    v0 = lambda p: e.valor(p, ejercicio) or 0.0  # noqa: E731  (solo para partidas opcionales de balance)
    previo = ejercicio - 1

    ingresos, ebit = v("ingresos"), v("resultado_operativo")
    bruto = v("beneficio_bruto")
    if bruto is None and ingresos is not None and v("coste_ventas") is not None:
        bruto = ingresos - v("coste_ventas")  # no declarado: se calcula (y calidad.py lo contrasta si se declara)
    ebitda = _suma(ebit, v("amortizacion"))
    fcf = _suma(v("flujo_operativo"), -v("capex") if v("capex") is not None else None)
    deuda = v0("deuda_cp") + v0("deuda_lp")
    dfn = deuda - (v("caja") or 0.0) - v0("inversiones_cp") if v("caja") is not None else None
    tipo = _div(v("impuestos"), v("bai"))
    cap_invertido = _suma(v("patrimonio"), v0("minoritarios"), dfn)
    cap_empleado = _suma(v("activos"), -v("pasivo_corriente") if v("pasivo_corriente") is not None else None)

    return {
        "ajustes_ev": ajustes_ev(e, ejercicio),
        "deuda_neta_ajustada": None if dfn is None else dfn + ajustes_ev(e, ejercicio),
        "ingresos": ingresos,
        "crecimiento_ingresos": _div(_suma(ingresos, -e.valor("ingresos", previo)) if e.valor("ingresos", previo) else None,
                                     e.valor("ingresos", previo)),
        "beneficio_bruto": bruto,
        "margen_bruto": _div(bruto, ingresos),
        "ebitda": ebitda,
        "margen_ebitda": _div(ebitda, ingresos),
        "ebit": ebit,
        "margen_operativo": _div(ebit, ingresos),
        "beneficio_neto": v("beneficio_neto"),
        "margen_neto": _div(v("beneficio_neto"), ingresos),
        "bpa_diluido": v("bpa_diluido"),
        "fcf": fcf,
        "fcf_tras_sbc": _suma(fcf, -v("pagos_basados_acciones") if v("pagos_basados_acciones") is not None else None),
        "conversion_fcf": _div(fcf, v("beneficio_neto")),
        "fcf_sobre_ebitda": _div(fcf, ebitda),
        "deuda_bruta": deuda,
        "dfn": dfn,
        "dfn_ebitda": _div(dfn, ebitda) if ebitda is not None and ebitda > 0 else None,  # con EBITDA ≤ 0 no significa nada
        "cobertura_intereses": _div(ebit, v("gasto_intereses")) if v("gasto_intereses") else None,
        "liquidez": _div(v("activo_corriente"), v("pasivo_corriente")),
        "tipo_efectivo": tipo,
        "roe": _div(v("beneficio_neto"), v("patrimonio")),
        "roa": _div(v("beneficio_neto"), v("activos")),
        "roic": _div(ebit * (1 - tipo) if ebit is not None and tipo is not None else None, cap_invertido),
        "roce": _div(ebit, cap_empleado),
        "capex_sobre_ventas": _div(v("capex"), ingresos),
        "id_sobre_ventas": _div(v("id"), ingresos) if v("id") is not None else None,
        "payout": _div(v("dividendos"), v("beneficio_neto")) if v("dividendos") is not None else None,
        "retribucion_accionista": _suma(v0("dividendos"), v0("recompras")),
    }


def componentes_ev(e: EstadosNormalizados, ejercicio: int) -> dict[str, float]:
    """Componentes del EV además de la DFN (los no declarados cuentan 0: el informe lista cuáles se declararon)."""
    v0 = lambda p: e.valor(p, ejercicio) or 0.0  # noqa: E731
    conceptos_deuda = " ".join(e.datos.get(p, {}).get(ejercicio).concepto for p in ("deuda_cp", "deuda_lp")
                               if e.datos.get(p, {}).get(ejercicio))
    incluye_arrendamientos = "Lease" in conceptos_deuda  # p. ej. LongTermDebtAndCapitalLeaseObligations
    return {
        "Acciones preferentes": v0("preferentes"),
        "Pensiones (pasivo neto)": v0("pensiones"),
        "Patrimonio temporal": v0("patrimonio_temporal"),
        "Arrendamientos financieros": 0.0 if incluye_arrendamientos else v0("arrendamientos_financieros"),
    }


def ajustes_ev(e: EstadosNormalizados, ejercicio: int) -> float:
    return sum(componentes_ev(e, ejercicio).values())


def valoracion(e: EstadosNormalizados, ejercicio: int, m: Mercado) -> dict[str, float | None]:
    """Múltiplos con la cotización del informe sobre las cifras de un ejercicio."""
    f = fundamentales(e, ejercicio)
    v0 = lambda p: e.valor(p, ejercicio) or 0.0  # noqa: E731
    mc = m.capitalizacion
    ev = (mc + v0("deuda_cp") + v0("deuda_lp") + v0("minoritarios") - v0("caja") - v0("inversiones_cp")
          + ajustes_ev(e, ejercicio))
    dividendos = e.valor("dividendos", ejercicio)
    return {
        "capitalizacion": mc,
        "ev": ev,
        "per": _div(mc, f["beneficio_neto"]),
        "p_bv": _div(mc, e.valor("patrimonio", ejercicio)),
        "ev_ventas": _div(ev, f["ingresos"]),
        "ev_ebitda": _div(ev, f["ebitda"]),
        "ev_ebit": _div(ev, f["ebit"]),
        "p_fcf": _div(mc, f["fcf_tras_sbc"]),
        "fcf_yield": _div(f["fcf_tras_sbc"], mc),
        "rentabilidad_dividendo": _div(dividendos, mc) if dividendos is not None else None,
    }


def cagr(inicial: float | None, final: float | None, anios: int) -> float | None:
    if inicial is None or final is None or inicial <= 0 or final <= 0 or anios <= 0:
        return None
    return (final / inicial) ** (1 / anios) - 1
