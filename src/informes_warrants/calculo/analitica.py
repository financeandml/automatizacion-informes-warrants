"""Analítica determinista: de dónde viene la variación del margen, apalancamiento operativo y uso del capital.

Ningún repo base la hacía (inventario, carencia 5): edgar_analytics y FinRobot calculan ratios, pero no
explican su variación. Aquí se descompone por código, sin IA, para que las plantillas redacten el «por qué».

  Puente del margen operativo (puntos básicos, pb = 0,01 %):
    Δ margen operativo = Δ margen bruto − Δ (I+D / ventas) − Δ (gastos generales / ventas) − Δ otros
    («otros» es el resto, para que el puente cuadre siempre con la variación total)
  Apalancamiento operativo = variación % del EBIT / variación % de las ventas
  Uso del capital (suma del periodo): dividendos + recompras sobre FCF tras remuneración en acciones;
    variación de las acciones diluidas; capex / D&A
  Contribución de cada segmento al crecimiento: pendiente (docs/rigor-del-contenido.md, carencia 4)
"""

PB = 10_000  # de tanto por uno a puntos básicos


def _ratio(valor, ventas):
    return None if valor is None or not ventas else valor / ventas


def puente_margen(inicio: dict, fin: dict, gasto_inicio: dict, gasto_fin: dict) -> dict | None:
    """`inicio`/`fin`: fundamentales de dos periodos; `gasto_*`: {"id": …, "gastos_generales": …} en USD.

    Devuelve las contribuciones en pb (positivo = mejora el margen operativo) o None si faltan márgenes.
    """
    mo0, mo1, mb0, mb1 = inicio.get("margen_operativo"), fin.get("margen_operativo"), inicio.get("margen_bruto"), fin.get("margen_bruto")
    if None in (mo0, mo1, mb0, mb1):
        return None
    total = (mo1 - mo0) * PB
    bruto = (mb1 - mb0) * PB
    contribucion = {"margen bruto": bruto}
    for clave, nombre in (("id", "I+D"), ("gastos_generales", "gastos generales y de venta")):
        r0, r1 = _ratio(gasto_inicio.get(clave), inicio["ingresos"]), _ratio(gasto_fin.get(clave), fin["ingresos"])
        if r0 is not None and r1 is not None:
            contribucion[nombre] = -(r1 - r0) * PB
    contribucion["otros"] = total - sum(contribucion.values())
    principal = max(contribucion, key=lambda k: abs(contribucion[k]))
    return {"total": total, "contribuciones": contribucion, "principal": principal}


def apalancamiento_operativo(inicio: dict, fin: dict) -> float | None:
    v0, v1, e0, e1 = inicio.get("ingresos"), fin.get("ingresos"), inicio.get("ebit"), fin.get("ebit")
    if None in (v0, v1, e0, e1) or v0 <= 0 or e0 <= 0 or v1 == v0:
        return None
    return (e1 / e0 - 1) / (v1 / v0 - 1)


def uso_del_capital(estados, ejercicios: list[int], fundamentales: dict[int, dict]) -> dict:
    """Sumas del periodo (ejercicios fiscales completos)."""
    def total(clave, fuente="e"):
        valores = [estados.valor(clave, a) if fuente == "e" else fundamentales[a].get(clave) for a in ejercicios]
        return None if any(v is None for v in valores) else sum(valores)

    fcf = total("fcf_tras_sbc", "f")
    retribucion = (total("dividendos") or 0.0) + (total("recompras") or 0.0)
    acciones = [estados.valor("acciones_diluidas", a) for a in (ejercicios[0], ejercicios[-1])]
    capex, da = total("capex"), total("amortizacion")
    return {
        "anios": len(ejercicios), "fcf": fcf, "retribucion": retribucion,
        "retribucion_sobre_fcf": retribucion / fcf if fcf and fcf > 0 else None,
        "variacion_acciones": acciones[1] / acciones[0] - 1 if None not in acciones and acciones[0] else None,
        "capex_sobre_da": capex / da if capex is not None and da else None,
    }


def autonomia_de_caja(f_ltm: dict, estados_ltm, clave: int, acciones_inicio: float | None, anios: int) -> dict | None:
    """Autonomía de caja (R2), solo si la empresa consume caja: meses que cubre su liquidez al ritmo del LTM.

    meses = (caja + inversiones financieras a corto) / −(flujo operativo − capex del LTM) · 12
    dilución = variación anual compuesta de las acciones diluidas en `anios` años (financiación con acciones).
    """
    fcf = f_ltm.get("fcf")
    if fcf is None or fcf >= 0:
        return None
    caja = estados_ltm.valor("caja", clave)
    if caja is None:
        return None
    liquidez = caja + (estados_ltm.valor("inversiones_cp", clave) or 0.0)
    acciones = estados_ltm.valor("acciones_diluidas", clave)
    dilucion = None
    if acciones_inicio and acciones and anios > 0:
        dilucion = (acciones / acciones_inicio) ** (1 / anios) - 1
    return {"liquidez": liquidez, "consumo_anual": -fcf, "meses": liquidez / -fcf * 12, "dilucion_anual": dilucion,
            "anios_dilucion": anios}


def contribucion_segmentos(miembros: dict[str, dict[int, float]], inicio: int, fin: int) -> dict | None:
    """Puntos de crecimiento de las ventas que aporta cada segmento entre dos ejercicios validados.

    contribución_i = (ventas_i,fin − ventas_i,inicio) / ventas_totales,inicio ; suman el crecimiento total.
    Solo con segmentos presentes en ambos años (si cambió la clasificación, None: no se mezclan definiciones).
    """
    comunes = [n for n, s in miembros.items() if inicio in s and fin in s]
    en_inicio = [n for n, s in miembros.items() if inicio in s]
    en_fin = [n for n, s in miembros.items() if fin in s]
    if not comunes or len(comunes) != len(en_inicio) or len(comunes) != len(en_fin):  # misma clasificación en ambos años
        return None
    total_inicio = sum(miembros[n][inicio] for n in comunes)
    if not total_inicio:
        return None
    contribucion = {n: (miembros[n][fin] - miembros[n][inicio]) / total_inicio for n in comunes}
    principal = max(contribucion, key=lambda n: abs(contribucion[n]))
    return {"contribuciones": contribucion, "total": sum(contribucion.values()), "principal": principal}
