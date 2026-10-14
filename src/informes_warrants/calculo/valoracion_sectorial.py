"""Valoración de los perfiles sectoriales (B2): múltiplos sobre patrimonio, FFO o NAV; sin EV, EBITDA ni DCF de FCFF.

Lo que dice cada perfil (`calculo/perfiles.py`, campo `valoracion`) y los métodos del precio objetivo:
- Banca: P/TBV frente al ROTE. Valor contable justificado: P/TBV = (ROTE − g) / (Ke − g), × TBV por acción.
- Seguros: P/BV frente al ROE. Valor contable justificado: P/BV = (ROE − g) / (Ke − g), × valor contable por acción.
- REIT: P/FFO y rentabilidad por dividendo (la amortización no es caja: ni PER ni DCF de FCFF). Descuento de
  dividendos: DPA × (1 + g) / (Ke − g).
- BDC y fondos cerrados: P/NAV, con el ROE del resultado total de las operaciones (NII ± ganancias y pérdidas de la
  cartera: el NII solo mide la capacidad de pagar el dividendo) como ROE sostenible; y descuento de dividendos. g = 0 por
  defecto: reparten casi todo el beneficio (régimen RIC, ≥ 90 %), así que el NAV y el dividendo apenas crecen.
- Valor contable, PER y rentabilidad: los de los accionistas ordinarios (sin las acciones preferentes ni sus dividendos).
- Todos: comparables del analista = mediana de su múltiplo principal × la base por acción propia (rango P25-P75).
Ke = Rf + β · prima de riesgo (las mismas estimaciones editables del informe general). El valor contable
justificado es el modelo de Gordon sobre el patrimonio: un ROE sostenible por encima de Ke justifica cotizar por
encima del valor contable. ROE sostenible por defecto: la media de los ejercicios del informe (a lo largo del ciclo, no el
del último año, que puede ser un pico); el analista puede fijar el suyo. Rango de los métodos de Gordon: Ke ± 1 punto.

Ideas reutilizadas: la síntesis ponderada de métodos es la de `calculo/sintesis.py` (patrón de FinRobot,
Apache-2.0); la mediana con mínimo de comparables, la de `calculo/valoracion_relativa.py`. Ningún repo base
valora bancos, aseguradoras, REIT o BDC (inventario, verificado con grep en los 9).
"""

import math
import statistics

MULTIPLO_PRINCIPAL = {"banco": "p_tbv", "aseguradora": "p_bv", "reit": "p_ffo", "inversion": "p_nav"}
NOMBRES = {"p_bv": "P / Valor contable", "p_tbv": "P / Valor contable tangible", "per": "PER", "p_ffo": "P / FFO",
           "p_nav": "P / NAV", "rentabilidad_dividendo": "Rentabilidad por dividendo"}
# Rentabilidad sostenible del método de Gordon y su base por acción
RENTABILIDAD = {"banco": "rote", "aseguradora": "roe", "inversion": "roe"}  # BDC: el resultado total, no solo el NII
# g por defecto distinto del general: las BDC reparten casi todo su beneficio (RIC, ≥ 90 %): el NAV y el dividendo no crecen
G_POR_DEFECTO = {"inversion": 0.0}
VALOR_CONTABLE, DIVIDENDOS, COMPARABLES = "Valor contable justificado", "Descuento de dividendos", "Comparables"
METODOS = {"banco": (VALOR_CONTABLE, COMPARABLES), "aseguradora": (VALOR_CONTABLE, COMPARABLES),
           "reit": (DIVIDENDOS, COMPARABLES), "inversion": (VALOR_CONTABLE, DIVIDENDOS, COMPARABLES)}
PESOS_POR_DEFECTO = {VALOR_CONTABLE: 0.5, DIVIDENDOS: 0.5, COMPARABLES: 0.5}  # se renormalizan entre los que tienen valor
MINIMO_COMPARABLES = 3
SENSIBILIDAD_KE = 0.01


def _valido(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def _div(a, b):
    return a / b if _valido(a) and _valido(b) and b else None


def patrimonio_comun(valores: dict) -> float | None:
    """Patrimonio de los accionistas ordinarios: el total menos las acciones preferentes (si la empresa las declara)."""
    patrimonio, preferentes = valores.get("patrimonio"), valores.get("preferentes")
    if not _valido(patrimonio):
        return None
    return patrimonio - preferentes if _valido(preferentes) else patrimonio


def multiplos(perfil_id: str, precio: float | None, acciones: float | None, valores: dict, metricas: dict) -> dict:
    """Múltiplos del perfil con la cotización de hoy y las cifras del periodo (LTM o último ejercicio)."""
    capitalizacion = precio * acciones if precio and acciones else None
    beneficio, dividendos, comun = valores.get("beneficio"), valores.get("dividendos"), patrimonio_comun(valores)
    if _valido(beneficio) and _valido(valores.get("dividendos_preferentes")):
        beneficio -= valores["dividendos_preferentes"]  # beneficio de los ordinarios (base del PER)
    salida = {"capitalizacion": capitalizacion, "p_bv": _div(capitalizacion, comun) if comun and comun > 0 else None,
              "per": _div(capitalizacion, beneficio) if _valido(beneficio) and beneficio > 0 else None,
              "rentabilidad_dividendo": _div(dividendos, capitalizacion) if _valido(dividendos) and dividendos > 0 else None}
    tangible, ffo, nav = metricas.get("patrimonio_tangible"), metricas.get("ffo"), metricas.get("nav_por_accion")
    if perfil_id == "banco":
        salida["p_tbv"] = _div(capitalizacion, tangible) if _valido(tangible) and tangible > 0 else None
    if perfil_id == "reit":
        salida["p_ffo"] = _div(capitalizacion, ffo) if _valido(ffo) and ffo > 0 else None
    if perfil_id == "inversion":
        salida["p_nav"] = _div(precio, nav) if _valido(nav) and nav > 0 else None
    return salida


def multiplo_justo(rentabilidad: float | None, ke: float, g: float) -> float | None:
    """(ROE − g) / (Ke − g): None si Ke ≤ g, falta la rentabilidad o no llega a g (valor nulo o negativo)."""
    if not _valido(rentabilidad) or ke <= g or rentabilidad <= g:
        return None
    return (rentabilidad - g) / (ke - g)


def descuento_dividendos(dpa: float | None, ke: float, g: float) -> float | None:
    """Gordon sobre el dividendo: DPA × (1 + g) / (Ke − g)."""
    if not _valido(dpa) or dpa <= 0 or ke <= g:
        return None
    return dpa * (1 + g) / (ke - g)


def por_accion(perfil_id: str, valores: dict, metricas: dict, acciones: float | None) -> float | None:
    """Base por acción del múltiplo principal: valor contable (tangible en banca), FFO o NAV."""
    if not acciones:
        return None
    if perfil_id == "banco":
        return _div(metricas.get("patrimonio_tangible"), acciones)
    if perfil_id == "reit":
        return _div(metricas.get("ffo"), acciones)
    if perfil_id == "inversion":
        return metricas.get("nav_por_accion") if _valido(metricas.get("nav_por_accion")) else None
    return _div(patrimonio_comun(valores), acciones)


def _cuartil(valores: list[float], q: float) -> float:
    ordenados = sorted(valores)
    posicion = q * (len(ordenados) - 1)  # interpolación lineal, como numpy.percentile
    bajo, alto = math.floor(posicion), math.ceil(posicion)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (posicion - bajo)


def valor_por_comparables(perfil_id: str, comparables: list[dict], base_por_accion: float | None) -> dict | None:
    """Mediana (y P25-P75) del múltiplo principal de los comparables con valor positivo × la base por acción propia."""
    clave = MULTIPLO_PRINCIPAL[perfil_id]
    validos = [c["multiplos"][clave] for c in comparables if _valido(c["multiplos"].get(clave)) and c["multiplos"][clave] > 0]
    if len(validos) < MINIMO_COMPARABLES or not base_por_accion or base_por_accion <= 0:
        return None
    mediana = statistics.median(validos)
    return {"multiplo": clave, "mediana": mediana, "n": len(validos), "valor": mediana * base_por_accion,
            "bajo": _cuartil(validos, 0.25) * base_por_accion, "alto": _cuartil(validos, 0.75) * base_por_accion}


def rentabilidad_del_ciclo(valores: list) -> float | None:
    """Rentabilidad sostenible por defecto: la media de los ejercicios con dato (evita valorar sobre un año pico)."""
    validos = [v for v in valores if _valido(v)]
    return statistics.fmean(validos) if validos else None


def valorar(perfil_id: str, precio: float, acciones: float | None, valores: dict, metricas: dict, ke: float, g: float,
            comparables: list[dict], comparables_del_analista: bool, rentabilidad_sostenible: float | None = None) -> dict:
    """Múltiplos actuales, métodos del perfil (valor y rango por acción) y datos de cada uno.

    Los comparables solo dan valor con la lista del analista (la propuesta automática es orientativa): sin ella,
    `valor` del método es None y `orientativo` lleva el cálculo para la tabla. El valor contable justificado usa la
    `rentabilidad_sostenible` (la del ciclo o la del analista); sin ella, la del periodo."""
    actuales = multiplos(perfil_id, precio, acciones, valores, metricas)
    base = por_accion(perfil_id, valores, metricas, acciones)
    metodos = {}
    clave_rentabilidad = RENTABILIDAD.get(perfil_id)
    rentabilidad = metricas.get(clave_rentabilidad) if clave_rentabilidad else None
    rentabilidad = rentabilidad if _valido(rentabilidad) else None
    if VALOR_CONTABLE in METODOS[perfil_id]:
        sostenible = rentabilidad_sostenible if _valido(rentabilidad_sostenible) else rentabilidad
        justo = multiplo_justo(sostenible, ke, g)
        base_contable = base if perfil_id != "inversion" else metricas.get("nav_por_accion")
        valor = justo * base_contable if justo is not None and _valido(base_contable) and base_contable > 0 else None
        extremos = [multiplo_justo(sostenible, k, g) for k in (ke + SENSIBILIDAD_KE, ke - SENSIBILIDAD_KE)]
        metodos[VALOR_CONTABLE] = {
            "valor": valor, "multiplo_justo": justo, "rentabilidad": sostenible, "base_por_accion": base_contable,
            "bajo": extremos[0] * base_contable if valor is not None and extremos[0] is not None else None,
            "alto": extremos[1] * base_contable if valor is not None and extremos[1] is not None else None}
    if DIVIDENDOS in METODOS[perfil_id]:
        dpa = _div(valores.get("dividendos"), acciones) if _valido(valores.get("dividendos")) else None
        valor = descuento_dividendos(dpa, ke, g)
        metodos[DIVIDENDOS] = {"valor": valor, "dpa": dpa,
                               "bajo": descuento_dividendos(dpa, ke + SENSIBILIDAD_KE, g) if valor is not None else None,
                               "alto": descuento_dividendos(dpa, ke - SENSIBILIDAD_KE, g) if valor is not None else None}
    comps = valor_por_comparables(perfil_id, comparables, base)
    metodos[COMPARABLES] = {**(comps if comps and comparables_del_analista else {"valor": None, "bajo": None, "alto": None}),
                            "orientativo": comps if comps and not comparables_del_analista else None}
    principal = actuales.get(MULTIPLO_PRINCIPAL[perfil_id])
    justo = metodos.get(VALOR_CONTABLE, {}).get("multiplo_justo")
    return {"multiplos": actuales, "base_por_accion": base, "ke": ke, "g": g, "metodos": metodos,
            "rentabilidad": rentabilidad, "diferencial": rentabilidad - ke if rentabilidad is not None else None,
            "multiplo_principal": principal,
            # P/NAV justificado frente al actual en BDC; P/TBV o P/BV en banca y seguros
            "prima_sobre_justo": principal / justo - 1 if principal and justo else None}


def potencial(precio_objetivo: float | None, precio: float) -> float | None:
    return precio_objetivo / precio - 1 if precio_objetivo and precio else None
