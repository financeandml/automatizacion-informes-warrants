"""DCF de flujos libres para la empresa (FCFF), escenarios, DCF inverso y beta, como funciones puras.

Origen de cada pieza (ver docs/inventario/README.md):
- WACC y sensibilidad: patrón de financial-research-analyst-agent `src/tools/dcf_model.py`, con sus
  errores corregidos (resta la deuda neta, proyecta con las estimaciones del analista, sin infinitos).
- Convergencia lineal del crecimiento hacia g tras los años explícitos: idea del mismo `dcf_model.py`.
- Flujo terminal normalizado y DCF inverso (crecimiento y WACC implícitos por bisección, con código de
  resultado cuando no hay solución): adaptado de FinRobot `finrobot_desktop/finrobot/engine/compute/
  operators/dcf.py` (`_terminal_fcf`, `solve_for_implied_growth`, `solve_for_implied_wacc`),
  AI4Finance Foundation (AI4Finance-Foundation/FinRobot), licencia Apache-2.0. Cambios: funciones sobre nuestras
  `Estimaciones`, años de convergencia y resultado tipado en español.

  FCFF_t   = EBIT_t · (1 − t) + D&A_t − capex_t − ΔCirculante_t
             El EBIT es el contable (GAAP), que ya resta la remuneración en acciones como gasto: el FCFF
             no la vuelve a sumar, así que la trata como coste (criterio institucional habitual).
  Años     = n explícitos (estimaciones del analista) + k de convergencia lineal del crecimiento hacia g
             con el margen del último año explícito.
  Terminal = FCF_T · (1 + g) / (WACC − g), con FCF_T normalizado: capex de mantenimiento =
             min(D&A, capex) · (1 + g) y circulante solo por el crecimiento g. Si FCF_T ≤ 0, el DCF no
             es aplicable (error explícito, nunca un valor terminal negativo).
  Ke       = Rf + β · ERP ;  Kd neto = coste de la deuda · (1 − t)
  WACC     = Ke · E/(D+E) + Kd neto · D/(D+E)   (pesos a valor de mercado)
  Equity   = EV − DFN − minoritarios ; valor por acción = Equity / acciones
"""

from dataclasses import dataclass, replace

from ..informe.estimaciones import Escenarios, Estimaciones


@dataclass(frozen=True)
class ResultadoDCF:
    wacc: float
    ke: float
    flujos: list[float]  # FCFF proyectados: años explícitos + años de convergencia
    ingresos: list[float]
    valor_terminal: float
    ev: float
    equity: float
    valor_por_accion: float
    sensibilidad: dict[tuple[float, float], float]  # (wacc, g) → valor por acción
    explicitos: int = 0  # cuántos de `flujos` son años explícitos (el resto, convergencia)
    ebitda: tuple[float, ...] = ()
    va_flujos: float = 0.0  # valor actual de los flujos explícitos + convergencia
    va_terminal: float = 0.0
    sensibilidad_operativa: dict[tuple[float, float], float] | None = None  # (Δcrecimiento, Δmargen) → valor por acción


@dataclass(frozen=True)
class ResultadoInverso:
    """Resultado del DCF inverso. `codigo`: resuelto, por_encima (el precio exige más de lo que cabe en el
    intervalo), por_debajo, no_converge o no_aplicable (FCF terminal ≤ 0)."""

    valor: float | None
    codigo: str
    intervalo: tuple[float, float]
    precio_bajo: float | None = None
    precio_alto: float | None = None


@dataclass(frozen=True)
class ResultadoEscenarios:
    resultados: dict[str, ResultadoDCF]  # «Pesimista», «Base», «Optimista»
    probabilidades: dict[str, float]
    valor_ponderado: float


def wacc(est: Estimaciones, capitalizacion: float, deuda: float) -> tuple[float, float]:
    ke = est.coste_equity()
    peso_deuda = deuda / (deuda + capitalizacion) if deuda + capitalizacion > 0 else 0.0
    return ke * (1 - peso_deuda) + est.coste_deuda * (1 - est.tasa_fiscal) * peso_deuda, ke


def proyeccion(est: Estimaciones, ingresos_base: float, crecimientos: list[float] | None = None):
    """Ventas, EBITDA, D&A, EBIT y FCFF de cada año (explícitos + convergencia). Sin descontar."""
    crec = list(crecimientos if crecimientos is not None else est.crecimiento_ventas)
    margenes = list(est.margen_ebitda)
    ultimo_g, ultimo_m, k = crec[-1], margenes[-1], est.anios_convergencia
    crec += [ultimo_g + (est.g - ultimo_g) * j / k for j in range(1, k + 1)]
    margenes += [ultimo_m] * k
    filas, previo = [], ingresos_base
    for c, m in zip(crec, margenes, strict=True):
        ventas = previo * (1 + c)
        ebitda, da = ventas * m, ventas * est.da_sobre_ventas
        ebit = ebitda - da
        fcff = ebit * (1 - est.tasa_fiscal) + da - ventas * est.capex_sobre_ventas - (ventas - previo) * est.circulante_sobre_ventas
        filas.append({"ventas": ventas, "ebitda": ebitda, "amortizacion": da, "ebit": ebit, "fcff": fcff, "margen": m})
        previo = ventas
    return filas


def _fcf_terminal(est: Estimaciones, ventas: float, margen: float, g: float) -> float:
    """FCF de estado estacionario (FinRobot `_terminal_fcf`): no capitaliza el capex de la fase de crecimiento."""
    ancla = min(est.da_sobre_ventas, est.capex_sobre_ventas) * ventas
    ebit = ventas * margen - ancla
    return ebit * (1 - est.tasa_fiscal) + ancla - ancla * (1 + g) - ventas * g * est.circulante_sobre_ventas


def _valor(est, ingresos_base, w, g, dfn, minoritarios, acciones, crecimientos=None, delta_margen=0.0):
    e = est if not delta_margen else replace(est, margen_ebitda=[m + delta_margen for m in est.margen_ebitda])
    filas = proyeccion(e, ingresos_base, crecimientos)
    flujos = [f["fcff"] for f in filas]
    fcf_t = _fcf_terminal(e, filas[-1]["ventas"], filas[-1]["margen"], g)
    if fcf_t <= 0:
        raise ValueError("El flujo terminal normalizado es ≤ 0: el DCF no es aplicable (usar valoración relativa)")
    terminal = fcf_t * (1 + g) / (w - g)
    descuento = [(1 + w) ** (i + 1) for i in range(len(flujos))]
    va_flujos = sum(f / d for f, d in zip(flujos, descuento, strict=True))
    va_terminal = terminal / descuento[-1]
    equity = va_flujos + va_terminal - dfn - minoritarios
    return filas, terminal, va_flujos, va_terminal, equity, equity / acciones


def dcf(est: Estimaciones, ingresos_base: float, dfn: float, deuda: float, minoritarios: float, acciones: float,
        capitalizacion: float) -> ResultadoDCF:
    errores = est.validar()
    if errores:
        raise ValueError("Estimaciones no válidas: " + " ".join(errores))
    w, ke = wacc(est, capitalizacion, deuda)
    if est.g >= w:
        raise ValueError(f"g ({est.g:.2%}) debe ser menor que el WACC ({w:.2%})")
    filas, terminal, va_f, va_t, equity, por_accion = _valor(est, ingresos_base, w, est.g, dfn, minoritarios, acciones)

    def _seguro(**kw):
        try:
            return _valor(est, ingresos_base, kw.pop("w", w), kw.pop("g", est.g), dfn, minoritarios, acciones, **kw)[5]
        except ValueError:
            return None

    sensibilidad = {}
    for dw in (-0.01, -0.005, 0.0, 0.005, 0.01):
        for dg in (-0.005, 0.0, 0.005):
            if est.g + dg < w + dw:  # nunca valores infinitos ni negativos por g ≥ WACC
                valor = _seguro(w=w + dw, g=est.g + dg)
                if valor is not None:
                    sensibilidad[(round(w + dw, 4), round(est.g + dg, 4))] = valor
    operativa = {}
    for dc in (-0.02, -0.01, 0.0, 0.01, 0.02):  # idea de FinRobot `sensitivity_analyzer`: crecimiento × margen
        for dm in (-0.02, 0.0, 0.02):
            valor = _seguro(crecimientos=[c + dc for c in est.crecimiento_ventas], delta_margen=dm)
            if valor is not None:
                operativa[(dc, dm)] = valor
    return ResultadoDCF(w, ke, [f["fcff"] for f in filas], [f["ventas"] for f in filas], terminal, va_f + va_t, equity,
                        por_accion, sensibilidad, len(est.crecimiento_ventas), tuple(f["ebitda"] for f in filas), va_f, va_t,
                        operativa)


def valorar_escenarios(esc: Escenarios, ingresos_base: float, dfn: float, deuda: float, minoritarios: float, acciones: float,
                       capitalizacion: float) -> ResultadoEscenarios:
    """DCF de cada escenario y valor ponderado por sus probabilidades."""
    errores = esc.validar()
    if errores:
        raise ValueError("Escenarios no válidos: " + " ".join(errores))
    resultados = {n: dcf(e, ingresos_base, dfn, deuda, minoritarios, acciones, capitalizacion) for n, e, _ in esc.items()}
    probabilidades = {n: p for n, _, p in esc.items()}
    ponderado = sum(resultados[n].valor_por_accion * p for n, p in probabilidades.items())
    return ResultadoEscenarios(resultados, probabilidades, ponderado)


def _biseccion(precio_en, objetivo: float, bajo: float, alto: float, creciente: bool, tolerancia=1e-5, max_iter=100):
    try:
        p_bajo, p_alto = precio_en(bajo), precio_en(alto)
    except ValueError:
        return ResultadoInverso(None, "no_aplicable", (bajo, alto))
    minimo, maximo = (p_bajo, p_alto) if creciente else (p_alto, p_bajo)
    if objetivo > maximo:
        return ResultadoInverso(None, "por_encima", (bajo, alto), p_bajo, p_alto)
    if objetivo < minimo:
        return ResultadoInverso(None, "por_debajo", (bajo, alto), p_bajo, p_alto)
    lo, hi = bajo, alto
    for _ in range(max_iter):
        medio = (lo + hi) / 2
        if (precio_en(medio) < objetivo) == creciente:
            lo = medio
        else:
            hi = medio
        if hi - lo < tolerancia:
            return ResultadoInverso((lo + hi) / 2, "resuelto", (bajo, alto), p_bajo, p_alto)
    return ResultadoInverso((lo + hi) / 2, "no_converge", (bajo, alto), p_bajo, p_alto)


def crecimiento_implicito(est: Estimaciones, ingresos_base: float, dfn: float, deuda: float, minoritarios: float,
                          acciones: float, capitalizacion: float, precio: float,
                          intervalo: tuple[float, float] = (-0.10, 0.50)) -> ResultadoInverso:
    """Crecimiento anual constante de ventas en los años explícitos que iguala el valor al precio (resto igual)."""
    w, _ = wacc(est, capitalizacion, deuda)
    n = len(est.crecimiento_ventas)
    return _biseccion(lambda c: _valor(est, ingresos_base, w, est.g, dfn, minoritarios, acciones, [c] * n)[5],
                      precio, *intervalo, creciente=True)


def wacc_implicito(est: Estimaciones, ingresos_base: float, dfn: float, minoritarios: float, acciones: float,
                   precio: float, intervalo: tuple[float, float] = (0.03, 0.25)) -> ResultadoInverso:
    """Tasa de descuento que iguala el valor del escenario al precio: la rentabilidad anual implícita de comprar hoy."""
    bajo = max(intervalo[0], est.g + 0.001)
    return _biseccion(lambda w: _valor(est, ingresos_base, w, est.g, dfn, minoritarios, acciones)[5],
                      precio, bajo, intervalo[1], creciente=False)


def beta(rent_activo, rent_indice) -> float:
    """Beta = cov(activo, índice) / var(índice) sobre rentabilidades del mismo periodo (p. ej. semanales)."""
    import numpy as np

    a, i = np.asarray(rent_activo, dtype=float), np.asarray(rent_indice, dtype=float)
    if len(a) != len(i) or len(a) < 20:
        raise ValueError("Se necesitan al menos 20 rentabilidades alineadas")
    return float(np.cov(a, i, ddof=1)[0, 1] / np.var(i, ddof=1))


def atribucion_secuencial(anterior: Estimaciones, actual: Estimaciones, datos: dict, valor_anterior: float,
                          grupos: tuple[tuple[str, tuple[str, ...]], ...]) -> dict:
    """Cuánto explica cada grupo de supuestos el cambio del valor por acción del DCF (R16).

    Se cambian por orden: los datos de partida (`datos` actuales con las estimaciones anteriores), cada grupo y,
    al final, el resto de supuestos. Cada impacto es el valor tras el paso menos el anterior, así que la suma
    cuadra exactamente con el cambio total (la atribución de un factor cada vez deja un residuo de interacción).
    """
    pasos, previo = [], valor_anterior
    valor = dcf(anterior, **datos).valor_por_accion
    pasos.append({"grupo": "Datos de partida (LTM, balance, acciones, cotización)", "impacto": valor - previo})
    previo, est = valor, anterior
    for nombre, claves in grupos:
        est = replace(est, **{k: getattr(actual, k) for k in claves})
        valor = dcf(est, **datos).valor_por_accion
        pasos.append({"grupo": nombre, "impacto": valor - previo})
        previo = valor
    valor = dcf(actual, **datos).valor_por_accion
    pasos.append({"grupo": "Resto de supuestos", "impacto": valor - previo})
    return {"pasos": pasos, "total": valor - valor_anterior}
