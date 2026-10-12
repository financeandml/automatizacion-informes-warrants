"""Puntuaciones de riesgo contable: Altman Z (quiebra), Beneish M (manipulación) y Piotroski F (solidez).

Fórmulas publicadas (Altman 1968 y Z'' de 1995; Beneish 1999; Piotroski 2000), con la selección de
modelo, los umbrales y las convenciones de edgar_analytics `edgar_analytics/scores.py`
(`AltmanZScore`, `BeneishMScore`, `PiotroskiScore`), Copyright (c) 2025 Zohar Babin, licencia MIT.
Reimplementadas sobre las partidas del normalizador SEC (regla 9: una sola fuente de partidas), no
sobre los DataFrames por etiqueta de edgar_analytics. No se aplican a bancos, aseguradoras ni REIT
(su balance no tiene circulante ni inmovilizado comparables): ahí el resultado es None.

  Altman Z  (fabricación, ventas/activo > 0,5) = 1,2·CC/A + 1,4·RR/A + 3,3·EBIT/A + 0,6·Cap/P + 1,0·V/A
            zonas: > 2,99 segura; 1,81-2,99 gris; < 1,81 riesgo
  Altman Z'' (no fabricación) = 6,56·CC/A + 3,26·RR/A + 6,72·EBIT/A + 1,05·PN/P
            zonas: > 2,60 segura; 1,10-2,60 gris; < 1,10 riesgo
            (CC = activo − pasivo corriente; RR = beneficios retenidos; A = activo; P = pasivo; PN = patrimonio)
  Beneish M = −4,84 + 0,920·DSRI + 0,528·GMI + 0,404·AQI + 0,892·SGI + 0,115·DEPI − 0,172·SGAI
              + 4,679·TATA − 0,327·LVGI ; manipulación probable si M > −1,78
  Piotroski F = nº de 9 pruebas superadas (rentabilidad, apalancamiento y liquidez, eficiencia)
"""

from dataclasses import dataclass, field

from .normalizador import EstadosNormalizados


@dataclass(frozen=True)
class Puntuacion:
    nombre: str
    valor: float | None
    lectura: str  # zona o interpretación
    modelo: str = ""
    detalle: dict = field(default_factory=dict)
    faltan: tuple[str, ...] = ()


def _div(a, b):
    return None if a is None or b in (None, 0) else a / b


def altman(e: EstadosNormalizados, ej: int, capitalizacion: float | None) -> Puntuacion:
    v = lambda p: e.valor(p, ej)  # noqa: E731
    necesarios = ("activos", "activo_corriente", "pasivo_corriente", "reservas", "resultado_operativo", "pasivos", "ingresos")
    faltan = tuple(p for p in necesarios if v(p) is None)
    if faltan or not v("activos"):
        return Puntuacion("Altman Z", None, "no calculable", faltan=faltan)
    a = (v("activo_corriente") - v("pasivo_corriente")) / v("activos")
    b = v("reservas") / v("activos")
    c = v("resultado_operativo") / v("activos")
    rotacion = v("ingresos") / v("activos")
    if rotacion > 0.5 and capitalizacion and v("pasivos") > 0:
        d = capitalizacion / v("pasivos")
        z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * rotacion
        zona = "segura" if z > 2.99 else "gris" if z > 1.81 else "riesgo de insolvencia"
        return Puntuacion("Altman Z", z, zona, "Z (fabricación)", {"A": a, "B": b, "C": c, "D": d, "E": rotacion})
    if v("patrimonio") is None or v("pasivos") <= 0:
        return Puntuacion("Altman Z", None, "no calculable", faltan=("patrimonio",))
    d = v("patrimonio") / v("pasivos")
    z = 6.56 * a + 3.26 * b + 6.72 * c + 1.05 * d
    zona = "segura" if z > 2.60 else "gris" if z > 1.10 else "riesgo de insolvencia"
    return Puntuacion("Altman Z", z, zona, "Z'' (no fabricación)", {"A": a, "B": b, "C": c, "D": d})


def beneish(e: EstadosNormalizados, ej: int, previo: int) -> Puntuacion:
    def v(p, x=ej):
        return e.valor(p, x)

    necesarios = ("ingresos", "clientes", "activos", "activo_corriente", "inmovilizado", "amortizacion", "beneficio_neto",
                  "flujo_operativo", "pasivo_corriente")
    faltan = tuple(sorted({p for p in necesarios for x in (ej, previo) if v(p, x) is None}))
    bruto = {x: v("beneficio_bruto", x) if v("beneficio_bruto", x) is not None else
             (v("ingresos", x) - v("coste_ventas", x) if v("coste_ventas", x) is not None and v("ingresos", x) is not None else None)
             for x in (ej, previo)}
    if bruto[ej] is None or bruto[previo] is None:
        faltan += ("beneficio_bruto",)
    if faltan or not v("ingresos", previo) or not v("activos", previo):
        return Puntuacion("Beneish M", None, "no calculable", faltan=faltan)

    def ratio(x):  # partidas relativas de cada año
        dl = v("deuda_lp", x) or 0.0
        return {
            "clientes": v("clientes", x) / v("ingresos", x), "margen": bruto[x] / v("ingresos", x),
            "blandos": 1 - (v("activo_corriente", x) + v("inmovilizado", x)) / v("activos", x),
            "depreciacion": v("amortizacion", x) / (v("amortizacion", x) + v("inmovilizado", x)),
            "sga": _div(v("gastos_generales", x), v("ingresos", x)),
            "apalancamiento": (v("pasivo_corriente", x) + dl) / v("activos", x),
        }

    r, r0 = ratio(ej), ratio(previo)
    gmi = r0["margen"] / r["margen"] if r["margen"] > 0 else (r0["margen"] - r["margen"]) / 0.001 if r0["margen"] > r["margen"] else 1.0
    indices = {
        "DSRI": _div(r["clientes"], r0["clientes"]) or 1.0, "GMI": gmi, "AQI": _div(r["blandos"], r0["blandos"]) or 1.0,
        "SGI": v("ingresos") / v("ingresos", previo), "DEPI": _div(r0["depreciacion"], r["depreciacion"]) or 1.0,
        "SGAI": _div(r["sga"], r0["sga"]) or 1.0,  # sin gastos generales declarados: índice neutro (1)
        "LVGI": _div(r["apalancamiento"], r0["apalancamiento"]) or 1.0,
        "TATA": (v("beneficio_neto") - v("flujo_operativo")) / v("activos"),
    }
    m = (-4.84 + 0.920 * indices["DSRI"] + 0.528 * indices["GMI"] + 0.404 * indices["AQI"] + 0.892 * indices["SGI"]
         + 0.115 * indices["DEPI"] - 0.172 * indices["SGAI"] + 4.679 * indices["TATA"] - 0.327 * indices["LVGI"])
    lectura = "manipulación probable (M > −1,78)" if m > -1.78 else "sin indicios (M ≤ −1,78)"
    return Puntuacion("Beneish M", m, lectura, "8 índices", indices)


def piotroski(e: EstadosNormalizados, ej: int, previo: int) -> Puntuacion:
    def v(p, x=ej):
        return e.valor(p, x)

    def bruto(x):
        if v("beneficio_bruto", x) is not None:
            return v("beneficio_bruto", x)
        return None if v("coste_ventas", x) is None or v("ingresos", x) is None else v("ingresos", x) - v("coste_ventas", x)

    roa, roa0 = _div(v("beneficio_neto"), v("activos")), _div(v("beneficio_neto", previo), v("activos", previo))
    liq, liq0 = _div(v("activo_corriente"), v("pasivo_corriente")), _div(v("activo_corriente", previo), v("pasivo_corriente", previo))
    mb, mb0 = _div(bruto(ej), v("ingresos")), _div(bruto(previo), v("ingresos", previo))
    rot, rot0 = _div(v("ingresos"), v("activos")), _div(v("ingresos", previo), v("activos", previo))
    dl, dl0 = v("deuda_lp") or 0.0, v("deuda_lp", previo) or 0.0
    pruebas = {
        "ROA > 0": None if roa is None else roa > 0,
        "Flujo operativo > 0": None if v("flujo_operativo") is None else v("flujo_operativo") > 0,
        "ROA creciente": None if None in (roa, roa0) else roa > roa0,
        "Flujo operativo > beneficio neto": None if None in (v("flujo_operativo"), v("beneficio_neto"))
        else v("flujo_operativo") > v("beneficio_neto"),
        "Deuda a largo plazo decreciente": dl < dl0 if (v("activos") and v("activos", previo)) else None,
        "Liquidez creciente": None if None in (liq, liq0) else liq > liq0,
        "Sin dilución": None if None in (v("acciones_diluidas"), v("acciones_diluidas", previo))
        else v("acciones_diluidas") <= v("acciones_diluidas", previo),
        "Margen bruto creciente": None if None in (mb, mb0) else mb > mb0,
        "Rotación de activos creciente": None if None in (rot, rot0) else rot > rot0,
    }
    evaluables = {k: ok for k, ok in pruebas.items() if ok is not None}
    puntos = sum(evaluables.values())
    lectura = ("sólida" if puntos >= 7 else "intermedia" if puntos >= 4 else "débil") + f" ({len(evaluables)}/9 pruebas evaluables)"
    return Puntuacion("Piotroski F", float(puntos), lectura, "9 pruebas", pruebas,
                      tuple(k for k, ok in pruebas.items() if ok is None))
