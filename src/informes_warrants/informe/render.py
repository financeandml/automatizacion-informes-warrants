"""Del contexto del informe (informe/construir.py) al HTML y al PDF.

La misma plantilla HTML sirve para la vista previa y para el PDF. Aquí solo se da formato: todas
las cifras vienen ya calculadas del motor matemático.
"""

import functools
from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from ..calculo.definiciones import DEFINICIONES
from ..calculo.historico import METRICAS as METRICAS_HISTORICAS
from ..calculo.normalizador import LTM, MEDIDAS_SEGMENTO, PARTIDAS
from ..calculo.valoracion_relativa import MULTIPLOS, significativo
from ..visual import graficos
from .estimaciones import UMBRAL_COMPRAR, UMBRAL_VENDER
from .indice import APARTADOS, INDICE, SECCIONES
from .plantillas import MARCADOR, MARCADOR_IA, _num, _pct, _var

DIR = Path(__file__).resolve().parent.parent / "plantillas"
DIR_INFORME = DIR / "informe"
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")

_env = Environment(loader=FileSystemLoader(DIR_INFORME), undefined=StrictUndefined, autoescape=True)
_env.filters.update(num=_num, pct=_pct, var=_var, veces=lambda v, d=2: "n.d." if v is None else f"{_num(v, d)}x")


def _md(texto: str) -> Markup:
    """Markdown → HTML; cada marcador [[ANALISTA: …]] queda como recuadro visible del borrador.

    Los textos traen contenido de terceros (10-K, IA, analista): el HTML que contengan se muestra como texto y
    nunca se ejecuta (Markdown deja pasar HTML en bruto). Las plantillas de sección no usan HTML propio."""
    seguro = texto.replace("&", "&amp;").replace("<", "&lt;")
    con_marcas = MARCADOR.sub(lambda m: f'<span class="pendiente">{m.group(1).strip()}</span>', seguro)
    con_marcas = MARCADOR_IA.sub(lambda m: f'<span class="borrador-ia"><span class="etiqueta-ia">Borrador de la IA · el analista debe '
                                           f'revisarlo</span> {m.group(2).strip()}</span>', con_marcas)
    return Markup(markdown.markdown(con_marcas))


def _fecha_larga(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _mn(v, decimales=0):
    return _num(None if v is None else v / 1e6, decimales)


def _formato(v, formato):
    return _pct(v) if formato == "%" else _num(v, 2) if formato == "x2" else _mn(v)


def _filas(c, filas):
    """Filas de los estados: los 5 ejercicios fiscales y, al final, la columna LTM."""
    salida = []
    for nombre, fuente, clave, formato, clase in filas:
        valores = []
        for a in c["ejercicios"]:
            v = c["estados"].valor(clave, a) if fuente == "e" else c["fundamentales"][a][clave]
            valores.append(_formato(v, formato))
        v = c["estados_ltm"].valor(clave, LTM) if fuente == "e" else c["fund_ltm"].get(clave)
        valores.append(_formato(v, formato))
        salida.append({"nombre": nombre, "valores": valores, "clase": clase})
    return salida


def etiqueta_ltm(c) -> str:
    if not c.get("fecha_ltm"):
        return f"LTM (FY{c['filing']['ejercicio']})"
    d = date.fromisoformat(c["fecha_ltm"])
    return f"LTM {MESES[d.month - 1][:3]}-{d.year % 100:02d}"


ESTADOS = (
    ("Cuenta de resultados", (
        ("Ingresos", "e", "ingresos", "mn", "total"), ("Coste de ventas", "e", "coste_ventas", "mn", ""),
        ("Beneficio bruto", "f", "beneficio_bruto", "mn", "total"), ("I+D", "e", "id", "mn", ""),
        ("Gastos generales y de venta", "e", "gastos_generales", "mn", ""), ("EBITDA", "f", "ebitda", "mn", "total"),
        ("Resultado operativo (EBIT)", "e", "resultado_operativo", "mn", "total"),
        ("Beneficio antes de impuestos", "e", "bai", "mn", ""), ("Impuesto sobre beneficios", "e", "impuestos", "mn", ""),
        ("Beneficio neto", "e", "beneficio_neto", "mn", "total"), ("BPA diluido (USD)", "e", "bpa_diluido", "x2", ""),
    )),
    ("Balance", (
        ("Caja y equivalentes", "e", "caja", "mn", ""), ("Inversiones financieras a corto plazo", "e", "inversiones_cp", "mn", ""),
        ("Activo corriente", "e", "activo_corriente", "mn", ""), ("Activo total", "e", "activos", "mn", "total"),
        ("Pasivo corriente", "e", "pasivo_corriente", "mn", ""), ("Deuda financiera a corto plazo", "e", "deuda_cp", "mn", ""),
        ("Deuda financiera a largo plazo", "e", "deuda_lp", "mn", ""), ("Pasivo total", "e", "pasivos", "mn", "total"),
        ("Patrimonio neto", "e", "patrimonio", "mn", "total"), ("Deuda financiera neta", "f", "dfn", "mn", "total"),
    )),
    ("Flujos de caja", (
        ("Flujo de caja operativo", "e", "flujo_operativo", "mn", "total"), ("Capex", "e", "capex", "mn", ""),
        ("Flujo de caja libre (FCF)", "f", "fcf", "mn", "total"),
        ("FCF tras remuneración en acciones", "f", "fcf_tras_sbc", "mn", "total"), ("Amortizaciones (D&A)", "e", "amortizacion", "mn", ""),
        ("Remuneración en acciones", "e", "pagos_basados_acciones", "mn", ""), ("Dividendos pagados", "e", "dividendos", "mn", ""),
        ("Recompra de acciones", "e", "recompras", "mn", ""),
    )),
    ("Ratios", (
        ("Crecimiento de ingresos", "f", "crecimiento_ingresos", "%", ""), ("Margen bruto", "f", "margen_bruto", "%", ""),
        ("Margen EBITDA", "f", "margen_ebitda", "%", ""), ("Margen operativo", "f", "margen_operativo", "%", ""),
        ("Margen neto", "f", "margen_neto", "%", ""), ("ROE", "f", "roe", "%", ""), ("ROIC", "f", "roic", "%", ""),
        ("ROCE", "f", "roce", "%", ""), ("Conversión de FCF (FCF / BN)", "f", "conversion_fcf", "%", ""),
        ("Deuda neta / EBITDA", "f", "dfn_ebitda", "x2", ""), ("Tipo impositivo efectivo", "f", "tipo_efectivo", "%", ""),
        ("Pay-out", "f", "payout", "%", ""),
    )),
)


ESTIMADOS_PORTADA = 3  # columnas estimadas en la portada (la proyección completa está en la valoración)


def _resumen(c):
    """Portada: los 2 últimos ejercicios fiscales, el LTM y los 3 primeros periodos estimados."""
    ej = c["ejercicios"][-2:]
    fund, f_ltm, est = c["fundamentales"], c["fund_ltm"], c["estimaciones"]
    p = c["proyeccion"][:ESTIMADOS_PORTADA]
    hist = lambda clave, fmt: [fmt(fund[a][clave]) for a in ej] + [fmt(f_ltm.get(clave))]  # noqa: E731
    filas = [
        ("Ingresos", hist("ingresos", _mn) + [_mn(a.ventas) for a in p]),
        ("Crecimiento", hist("crecimiento_ingresos", _crecimiento) + [_pct(g) for g in est.crecimiento_ventas[:len(p)]]),
        ("EBITDA", hist("ebitda", _mn) + [_mn(a.ebitda) for a in p]),
        ("Margen EBITDA", hist("margen_ebitda", _pct) + [_pct(m) for m in est.margen_ebitda[:len(p)]]),
        ("Beneficio neto", hist("beneficio_neto", _mn) + [_mn(a.beneficio_neto) for a in p]),
        ("BPA diluido (USD)", hist("bpa_diluido", lambda v: _num(v, 2)) + [_num(a.bpa, 2) for a in p]),
        ("FCF tras SBC (FCFF en e)", hist("fcf_tras_sbc", _mn) + [_mn(a.fcff) for a in p]),
        ("Deuda neta / EBITDA", hist("dfn_ebitda", lambda v: _num(v, 2)) + ["—"] * len(p)),
        ("ROIC", hist("roic", _pct) + ["—"] * len(p)),
    ]
    return [{"nombre": n, "valores": v} for n, v in filas]


def _proyeccion(c):
    """Tabla de la proyección hasta el BPA: LTM real + años explícitos."""
    f, ltm, p = c["fund_ltm"], c["estados_ltm"], c["proyeccion"]
    v = lambda clave: ltm.valor(clave, LTM)  # noqa: E731
    bai, ebit = v("bai"), v("resultado_operativo")
    filas = (
        ("Ingresos", _mn(v("ingresos")), [_mn(a.ventas) for a in p], "total"),
        ("EBITDA", _mn(f.get("ebitda")), [_mn(a.ebitda) for a in p], ""),
        ("Amortizaciones (D&A)", _mn(v("amortizacion")), [_mn(a.amortizacion) for a in p], ""),
        ("Resultado operativo (EBIT)", _mn(ebit), [_mn(a.ebit) for a in p], "total"),
        ("Resultado financiero y otros", _mn(None if None in (bai, ebit) else bai - ebit), [_mn(a.resultado_financiero) for a in p], ""),
        ("Beneficio antes de impuestos", _mn(bai), [_mn(a.bai) for a in p], ""),
        ("Impuesto sobre beneficios", _mn(v("impuestos")), [_mn(a.impuestos) for a in p], ""),
        ("Beneficio neto atribuible", _mn(v("beneficio_neto")), [_mn(a.beneficio_neto) for a in p], "total"),
        ("Acciones diluidas (mn)", _num(None if v("acciones_diluidas") is None else v("acciones_diluidas") / 1e6, 0),
         [_num(a.acciones / 1e6, 0) for a in p], ""),
        ("BPA diluido (USD)", _num(f.get("bpa_diluido"), 2), [_num(a.bpa, 2) for a in p], "total"),
        ("Dividendo por acción (USD)", "—", [_num(a.dpa, 2) for a in p], ""),
        ("FCF del accionista por acción (USD)", "—", [_num(a.fcf_por_accion, 2) for a in p], ""),
    )
    return [{"nombre": n, "ltm": l_, "valores": e, "clase": k} for n, l_, e, k in filas]


def _comparables(c):
    """Filas de la tabla de comparables; los múltiplos no significativos se marcan (no entran en la mediana)."""
    filas = []
    for comp in c["comparables"]:
        m, f = comp["multiplos"], comp["fundamentales"]
        celdas = []
        for clave, _, limite, _, _ in MULTIPLOS:
            valor = m.get(clave)
            no_significativo = valor is not None and not significativo(valor, limite)
            celdas.append(_num(valor, 1) + ("x" if valor is not None else "") + (" n.s." if no_significativo else ""))
        filas.append({"ticker": comp["ticker"], "nombre": comp["nombre"], "capitalizacion": _num(m["capitalizacion"] / 1e9, 1),
                      "crecimiento": _pct(f.get("crecimiento_ingresos")), "margen": _pct(f.get("margen_ebitda")), "multiplos": celdas,
                      "tacc_ventas": _pct(comp.get("tacc_ventas_3a")), "tacc_bpa": _pct(comp.get("tacc_bpa_3a"))})
    return filas


TITULOS_SEGMENTOS = (("negocio", "Ingresos por segmento"), ("producto", "Ingresos por producto o servicio"),
                     ("geografia", "Ingresos por geografía"))
MAX_SERIES_GRAFICO = 5  # el resto se agrupa en «Resto» solo en el gráfico (la tabla los muestra todos)


def _mes_anio(d) -> str:
    return f"{MESES[d.month - 1][:3]}-{d.year % 100:02d}"


def _crecimiento(v) -> str:
    """Crecimiento ≥ 1.000 % (desde una base casi nula, p. ej. la primera venta de una biotecnológica): n.s."""
    return "n.s." if v is not None and abs(v) >= 10 else _pct(v)


def _segmentos(c) -> list[dict]:
    """Tablas de los desgloses validados (R14): cada columna suma los ingresos consolidados del ejercicio."""
    tablas = []
    for clave, titulo in TITULOS_SEGMENTOS:
        d = c["segmentos"].get(clave)
        if not d:
            continue
        ultimo = d.ejercicios[-1]
        total = {a: c["estados"].valor("ingresos", a) for a in d.ejercicios}
        conciliacion = getattr(d, "conciliacion", set()) or set()  # P21: corporativo y eliminaciones, al final
        orden = sorted(d.miembros.items(), key=lambda kv: (kv[0] in conciliacion, -(kv[1].get(ultimo) or 0)))
        filas = [{"nombre": n, "valores": [_mn(s.get(a)) for a in d.ejercicios],
                  "peso": _pct(s[ultimo] / total[ultimo]) if ultimo in s and total[ultimo] else "—"} for n, s in orden]
        resultado = []
        if d.resultado_operativo:
            for n, s in orden:
                if n in d.resultado_operativo:
                    r = d.resultado_operativo[n]
                    resultado.append({"nombre": n, "valores": [_mn(r.get(a)) for a in d.ejercicios],
                                      "margen": _pct(r[ultimo] / s[ultimo]) if ultimo in r and s.get(ultimo) else "—"})
        rechazados = ", ".join(f"FY{a}" for a in sorted(d.rechazados))
        for fila, (n, _) in zip(filas, orden, strict=True):  # LTM provisional (F7): solo si cuadró con el total LTM
            fila["ltm"] = _mn(d.ltm.get(n)) if d.ltm else None
        tablas.append({"clave": clave, "titulo": titulo, "ejercicios": d.ejercicios, "filas": filas,
                       "total": [_mn(total[a]) for a in d.ejercicios], "resultado": resultado, "rechazados": rechazados,
                       "origen": d.origen, "ltm": bool(d.ltm), "total_ltm": _mn(sum(d.ltm.values())) if d.ltm else None,
                       "ltm_origen": d.ltm_origen,
                       "medida": MEDIDAS_SEGMENTO.get(getattr(d, "medida", "OperatingIncomeLoss"), "Resultado operativo")})
    return tablas


def _concentracion(c) -> dict | None:
    """Clientes con concentración declarada (A3): los 3 últimos ejercicios con dato."""
    filas = c["concentracion"]
    if not filas:
        return None
    anios = sorted({a for f in filas for a in f["valores"]})[-3:]
    return {"anios": anios, "filas": [{"cliente": f["cliente"], "base": f["base"], "detalle": f["detalle"] or "—",
                                       "valores": [_pct(f["valores"].get(a), 0) if a in f["valores"] else "—" for a in anios]}
                                      for f in filas]}


def _calendario(c) -> list[dict]:
    """Calendario de catalizadores: el del analista o el borrador del SaaS (fechas ya posteriores a la emisión)."""
    filas = []
    for e in (c.get("catalizadores") or {}).get("calendario") or []:
        fecha = e.get("fecha")
        if isinstance(fecha, str) and fecha:
            fecha = date.fromisoformat(fecha[:10])
        filas.append({"evento": e.get("evento", ""), "fecha": fecha.strftime("%d/%m/%Y") if fecha else "—", "base": e.get("base", "")})
    return filas


def _publicaciones(c) -> list[dict]:
    filas = []
    for p in reversed(c.get("publicaciones") or []):
        t, r = p["trimestre"], p["reaccion"]
        filas.append({"fecha": p["fecha"].strftime("%d/%m/%Y"), "trimestre": _mes_anio(t["fin"]) if t else "—",
                      "ingresos": _mn(t["ingresos"]) if t else "—", "variacion": _var(t["crecimiento_interanual"]) if t else "—",
                      "bpa": _num(t["bpa"], 2) if t else "—", "sesion": r["primera_sesion"].strftime("%d/%m/%Y") if r else "—",
                      "reaccion": _var(r["reaccion"]) if r else "en curso"})
    return filas


FACTORES_DUPONT = (("margen_neto", "Margen neto (BN / ventas)", "%"), ("rotacion", "Rotación de activos (ventas / activo)", "x"),
                   ("apalancamiento", "Apalancamiento (activo / patrimonio)", "x"), ("roe", "ROE", "%"),
                   ("carga_fiscal", "Carga fiscal (BN / BAI)", "x"), ("carga_financiera", "Carga financiera (BAI / EBIT)", "x"),
                   ("margen_operativo", "Margen operativo (EBIT / ventas)", "%"))


def _dupont(c) -> dict | None:
    periodos = {k: v for k, v in (c.get("dupont") or {}).items() if v}
    if not periodos:
        return None
    fmt = lambda v, tipo: "—" if v is None else _pct(v) if tipo == "%" else _num(v, 2)  # noqa: E731
    return {"cabecera": [etiqueta_ltm(c) if k == "LTM" else k for k in periodos],
            "filas": [{"nombre": n, "valores": [fmt(d[k], t) for d in periodos.values()], "clase": "total" if k == "roe" else ""}
                      for k, n, t in FACTORES_DUPONT]}


MAX_OPERACIONES_INSIDERS = 10


def _insiders(c) -> dict | None:
    """Apartado 18: tablas formateadas (las cifras ya vienen calculadas en calculo/insiders.py)."""
    ins = c.get("insiders")
    if not ins:
        return None
    mayores = sorted(ins["operaciones"], key=lambda o: -(o["importe"] or 0))[:MAX_OPERACIONES_INSIDERS]
    return {
        "operaciones": [{"fecha": o["fecha"].strftime("%d/%m/%Y"), "nombre": o["nombre"], "cargo": o["cargo"] or "—",
                         "tipo": o["tipo"], "acciones": _num(o["acciones"], 0), "precio": _num(o["precio"], 2),
                         "importe": _num(o["importe"] / 1e6, 1) if o["importe"] else "—", "plan": "Sí" if o["plan_10b5_1"] else "No"}
                        for o in sorted(mayores, key=lambda o: o["fecha"], reverse=True)],
        "proxy": [{"nombre": a["nombre"], "acciones": _num(a["acciones"] / 1e6, 1) if a["acciones"] else "—",
                   "porcentaje": _pct(a["porcentaje"])} for a in ins["accionistas"]["del_proxy"]],
        "declaraciones": [{"nombre": d["nombre"], "porcentaje": _pct(d["porcentaje"]), "fecha": d["fecha_hecho"],
                           "formulario": d["formulario"]} for d in ins["accionistas"]["declaraciones"]],
    }


def _trimestres(c) -> dict | None:
    t = c["trimestres"]
    if not t:
        return None
    filas = (("Ingresos", [_mn(x["ingresos"]) for x in t], "total"),
             ("Variación interanual", [_var(x["crecimiento_interanual"]) for x in t], ""),
             ("Resultado operativo (EBIT)", [_mn(x["ebit"]) for x in t], ""),
             ("Margen operativo", [_pct(x["margen_operativo"]) for x in t], ""),
             ("Beneficio neto", [_mn(x["beneficio_neto"]) for x in t], ""),
             ("BPA diluido (USD)", [_num(x["bpa"], 2) for x in t], "total"))
    return {"cabecera": [_mes_anio(x["fin"]) for x in t], "filas": [{"nombre": n, "valores": v, "clase": k} for n, v, k in filas]}


def _flujo_balance(c) -> dict:
    """Flujo de caja y balance proyectados (R12): LTM real + años explícitos, solo con datos del propio informe."""
    p, ltm, f = c["proyeccion"], c["estados_ltm"], c["fund_ltm"]
    v = lambda clave: ltm.valor(clave, LTM)  # noqa: E731
    flujo = (
        ("Flujo de caja operativo", _mn(v("flujo_operativo")), [_mn(a.flujo_operativo) for a in p], "total"),
        ("Capex", _mn(v("capex")), [_mn(a.capex) for a in p], ""),
        ("Remuneración en acciones (SBC)", _mn(v("pagos_basados_acciones")), [_mn(a.sbc) for a in p], ""),
        ("FCF tras remuneración en acciones", _mn(f.get("fcf_tras_sbc")), [_mn(a.fcf_tras_sbc) for a in p], "total"),
        ("Dividendos pagados", _mn(v("dividendos")), [_mn(a.dividendos) for a in p], ""),
        ("Recompra de acciones", _mn(v("recompras")), [_mn(a.recompras) for a in p], ""),
        ("Variación de caja", "—", [_mn(a.variacion_caja) for a in p], "total"),
    )
    b = c["balance_base"]  # el mismo balance del LTM del que parte la proyección (calculo/proyeccion.balance_inicial)
    balance = ()
    if b and p and p[0].caja is not None:
        balance = (
            ("Caja e inversiones a corto plazo", _mn(b["caja"]), [_mn(a.caja) for a in p], ""),
            ("Activos operativos netos", _mn(b["activos_operativos_netos"]), [_mn(a.activos_operativos_netos) for a in p], ""),
            ("Deuda financiera", _mn(f.get("deuda_bruta")), [_mn(a.deuda) for a in p], ""),
            ("Patrimonio neto", _mn(v("patrimonio")), [_mn(a.patrimonio) for a in p], "total"),
            ("Deuda financiera neta", _mn(f.get("dfn")), [_mn(a.dfn) for a in p], "total"),
            ("Deuda neta / EBITDA", _num(f.get("dfn_ebitda"), 2), [_num(a.dfn_ebitda, 2) for a in p], ""),
        )
    serie = lambda filas: [{"nombre": n, "ltm": l_, "valores": e, "clase": k} for n, l_, e, k in filas]  # noqa: E731
    return {"flujo": serie(flujo), "balance": serie(balance)}


def _historicos(c) -> list[dict]:
    filas = []
    for clave, nombre in METRICAS_HISTORICAS.items():
        b = c["bandas"].get(clave)
        if not b or not b.n:
            continue
        implicito = c["historicos"].get(clave, {}).get("mediana")
        filas.append({"nombre": nombre, "actual": _num(b.actual, 1), "mediana": _num(b.mediana, 1), "p25": _num(b.p25, 1),
                      "p75": _num(b.p75, 1), "p90": _num(b.p90, 1), "percentil": _pct(b.percentil_actual, 0),
                      "implicito": _num(implicito, 2), "n": b.n})
    return filas


def _graficos(c):
    ej = c["ejercicios"]
    fund = c["fundamentales"]
    etiquetas = [f"FY{a % 100:02d}" for a in ej]
    mn = lambda clave: [(fund[a][clave] or 0) / 1e6 for a in ej]  # noqa: E731
    serie = lambda clave: [fund[a][clave] for a in ej]  # noqa: E731
    return {
        "ingresos": Markup(graficos.barras_y_linea(etiquetas, mn("ingresos"), serie("margen_ebitda"), "Ingresos", "Margen EBITDA")),
        "fcf": Markup(graficos.barras_pareadas(etiquetas, mn("beneficio_neto"), mn("fcf"), "Beneficio neto", "FCF")),
        "rentabilidad": Markup(graficos.lineas(etiquetas, {"ROIC": serie("roic"), "ROCE": serie("roce")})),
        "margenes": Markup(graficos.lineas(etiquetas, {"Bruto": serie("margen_bruto"), "Operativo": serie("margen_operativo"),
                                                       "Neto": serie("margen_neto")})),
        "base_100": Markup(graficos.base_100(c["series_bolsa"])),
        **_graficos_extra(c),
    }


def _graficos_extra(c) -> dict:
    graficos_extra = {}
    if c.get("cascada"):
        graficos_extra["cascada"] = Markup(graficos.cascada([(n, v / 1e6, k) for n, v, k in c["cascada"]]))
    venc = c.get("vencimientos") or {}
    if venc.get("importes"):
        ej = c["filing"]["ejercicio"]
        etiquetas = [f"FY{(ej + i) % 100:02d}" for i in range(1, 6)] + ["Posterior"]
        importes = [None if v is None else v / 1e6 for v in venc["importes"]]
        graficos_extra["vencimientos"] = Markup(graficos.vencimientos(etiquetas, importes))
    principal = next((c["segmentos"][k] for k in ("negocio", "producto") if k in c["segmentos"]), None)
    if principal:
        fuera = getattr(principal, "conciliacion", set()) or set()  # el gráfico, sin corporativo ni eliminaciones
        orden = sorted(((n, s) for n, s in principal.miembros.items() if n not in fuera),
                       key=lambda kv: -(kv[1].get(principal.ejercicios[-1]) or 0))
        series = {n: [(s.get(a) or 0) / 1e6 for a in principal.ejercicios] for n, s in orden[:MAX_SERIES_GRAFICO]}
        if len(orden) > MAX_SERIES_GRAFICO:
            series["Resto"] = [sum((s.get(a) or 0) for _, s in orden[MAX_SERIES_GRAFICO:]) / 1e6 for a in principal.ejercicios]
        graficos_extra["segmentos"] = Markup(graficos.barras_apiladas([f"FY{a % 100:02d}" for a in principal.ejercicios], series))
    graficos_extra.update(_grafico_rangos(c))
    clave_hist = next((k for k in ("ev_ebitda", "per") if c["bandas"].get(k) and c["bandas"][k].n), None)
    if clave_hist:
        b = c["bandas"][clave_hist]
        graficos_extra["historico"] = Markup(graficos.serie_multiplo(b.serie, b.mediana, b.p25, b.p75, b.actual,
                                                                     METRICAS_HISTORICAS[clave_hist]))
        graficos_extra["historico_nombre"] = METRICAS_HISTORICAS[clave_hist]
    p = c["proyeccion"]
    if p:
        ej = c["ejercicios"][-3:]
        # Etiquetas cortas (8 barras en medio ancho): «LTM» y «27e» = doce meses hasta jun-27 (la tabla da el mes)
        etiquetas = [f"FY{a % 100:02d}" for a in ej] + ["LTM"] + [e.split("-")[-1] for e in c["etiquetas_estimadas"]]
        fund, fl, ltm = c["fundamentales"], c["fund_ltm"], c["estados_ltm"]
        fcf = [(fund[a]["fcf_tras_sbc"] or 0) / 1e6 for a in ej] + [(fl.get("fcf_tras_sbc") or 0) / 1e6] + [x.fcf_tras_sbc / 1e6 for x in p]
        retrib = ([(fund[a]["retribucion_accionista"] or 0) / 1e6 for a in ej] + [(fl.get("retribucion_accionista") or 0) / 1e6]
                  + [x.retribucion / 1e6 for x in p])
        graficos_extra["flujo"] = Markup(graficos.barras_pareadas(etiquetas, fcf, retrib, "FCF tras SBC", "Dividendos + recompras",
                                                                  separar_en=len(ej) + 1))
        if p[0].caja is not None:
            dfn = [(fund[a]["dfn"] or 0) / 1e6 for a in ej] + [(fl.get("dfn") or 0) / 1e6] + [x.dfn / 1e6 for x in p]
            pat = [(c["estados"].valor("patrimonio", a) or 0) / 1e6 for a in ej] + [(ltm.valor("patrimonio", LTM) or 0) / 1e6] + \
                  [x.patrimonio / 1e6 for x in p]
            graficos_extra["balance"] = Markup(graficos.barras_pareadas(etiquetas, dfn, pat, "Deuda financiera neta", "Patrimonio neto",
                                                                        separar_en=len(ej) + 1))
    graficos_extra.update(_grafico_historial(c))
    return graficos_extra


def _grafico_rangos(c) -> dict:
    rangos = [(m.nombre, m.valor, m.bajo, m.alto) for m in c["metodos"]]
    rangos.append(("Cotización 12 meses", c["cotizacion"].medio_12m, c["cotizacion"].minimo_12m, c["cotizacion"].maximo_12m))
    if not any(r[1] is not None for r in rangos[:-1]):
        return {}
    return {"rangos": Markup(graficos.rangos_valoracion(rangos, c["cotizacion"].precio, c["precio_objetivo"]))}


def _grafico_historial(c) -> dict:
    if not (c.get("historial") and c.get("precios_semanales")):
        return {}
    import pandas as pd

    # Cierres sin ajustar por dividendos: los precios objetivo de cada informe se fijaron sobre ellos
    precios = pd.Series([p for _, p in c["precios_semanales"]], index=pd.to_datetime([f for f, _ in c["precios_semanales"]]))
    puntos = [(pd.Timestamp(h["fecha"]), h["precio_objetivo"]) for h in c["historial"]]
    return {"historial": Markup(graficos.historial_recomendacion(precios, puntos))}


def _motor(c: dict) -> dict | None:
    """Sección «Modelo de valoración» (B1): cifras del libro del motor (ya calculadas en calculo/motor), con formato."""
    m = (c.get("motor") or {}).get("modelo")
    if m is None:
        return None
    v, s, d = m.valores, m.salidas, c["motor"]["datos"]
    x = lambda h, f, col: v.get((h, f, col))  # noqa: E731
    num = lambda val, dec=0: _num(val, dec) if isinstance(val, (int, float)) and not isinstance(val, bool) else "—"  # noqa: E731
    pct = lambda val: _pct(val) if isinstance(val, (int, float)) and not isinstance(val, bool) else "—"  # noqa: E731
    segmentos = []
    for seg in d.segmentos:
        hoja = next(h.nombre for h in m.libro.hojas if h.nombre.startswith("DCF ") and x(h.nombre, 2, 2) == f"{seg.nombre} DCF")
        con_multiplo = isinstance(x(hoja, 47, 11), float)  # sin comparables no hay valor terminal por múltiplo
        segmentos.append({"nombre": seg.nombre, "perpetuidad": num(x(hoja, 49, 7)),
                          "multiplo": num(x(hoja, 50, 11)) if con_multiplo else "—",
                          "ev": num(x(hoja, 41, 11)), "tv": pct(x(hoja, 52, 7))})
    puente = [(n, num(x("Consolidated", f, 11))) for f, n in ((41, "Valor de empresa (EV)"), (42, "+ Caja e inversiones a corto plazo"),
                                                             (43, "− Deuda financiera"), (44, "− Acciones preferentes"),
                                                             (45, "− Intereses minoritarios"), (46, "− Pensiones (pasivo neto)"),
                                                             (47, "− Patrimonio temporal"), (48, "− Arrendamientos financieros"))
              if f in (41, 42, 43) or (x("Consolidated", f, 11) or 0)]
    puente += [("Valor del patrimonio", num(x("Consolidated", 49, 11))),
               ("Acciones totalmente diluidas (mn)", num(x("Consolidated", 51, 11), 1)),
               ("Valor por acción (USD)", num(x("Consolidated", 52, 11), 2))]
    sensibilidad = {"wacc": [pct(w) for w in s.get("sensibilidad_wacc") or []], "tgr": [pct(g) for g in s.get("sensibilidad_tgr") or []],
                    "filas": [[num(val, 1) for val in fila] for fila in s.get("sensibilidad") or []]}
    primera = next(h.nombre for h in m.libro.hojas if h.nombre.startswith("DCF "))
    multiplo = x(primera, 47, 11)
    supuestos = [("Tipo libre de riesgo", pct(x("Entradas", 10, 3))), ("Prima de riesgo de mercado", pct(x("Entradas", 11, 3))),
                 ("Beta", num(x("WACC", 12, 6), 2) + (" (comparables, desapalancada y reapalancada)" if d.comparables else " (propia)")),
                 ("Coste del capital (Ke)", pct(x("WACC", 10, 6))), ("Coste de la deuda (antes de imp.)", pct(x("WACC", 17, 6))),
                 ("Tipo impositivo", pct(x("WACC", 18, 6))), ("WACC", pct(x("WACC", 22, 6))),
                 ("Crecimiento a perpetuidad (g)", pct(x("Entradas", 12, 3))),
                 ("Valor terminal por perpetuidad / múltiplo", f"{pct(x(primera, 46, 3))} / {pct(x(primera, 47, 3))}"),
                 ("Múltiplo de salida (EV/EBITDA mediano)",
                  num(multiplo, 1) + "x" if isinstance(multiplo, float) else "— (sin comparables)"),
                 ("Convención de descuento", "mitad de año" if x("Entradas", 14, 3) == 1 else "fin de año"),
                 ("Periodo parcial del ejercicio en curso", num(x("Consolidated", 35, 6), 2))]
    lbo = None
    if s.get("lbo_tir") is not None:
        lbo = [("Precio de la oferta (USD)", num(s.get("lbo_precio"), 2)), ("Prima sobre la cotización", pct(x("LBO", 14, 11))),
               ("EV / EBITDA de entrada", num(s.get("lbo_multiplo"), 1) + "x"), ("Deuda / EBITDA", num(x("LBO", 34, 6), 1) + "x"),
               ("MOIC", num(s.get("lbo_moic"), 2) + "x"), ("TIR del comprador financiero", pct(s.get("lbo_tir")))]
    fallos = [n.split("«")[1].rstrip("»") for n in m.avisos if "falla el control" in n]
    return {"segmentos": segmentos, "puente": puente, "sensibilidad": sensibilidad, "supuestos": supuestos, "lbo": lbo,
            "controles_ok": not fallos, "fallos": fallos, "potencial": pct(s.get("potencial_dcf")),
            "motivo": c["motor"].get("motivo", ""), "formulas": sum(1 for h in m.libro.hojas for celda in h.celdas.values()
                                                                   if isinstance(celda.valor, str) and celda.valor.startswith("="))}


def _comunes(c: dict) -> dict:
    """Variables de las piezas compartidas por la plantilla general y la sectorial."""
    legal = (DIR / "legal" / "descargo.md").read_text(encoding="utf-8").replace("{{ anio }}", str(date.today().year))
    return dict(
        c=c, t={k: _md(v) for k, v in c["textos"].items()}, fecha_larga=_fecha_larga(c["fecha"]), insiders=_insiders(c),
        indice=INDICE, secciones=SECCIONES, apartados=APARTADOS,  # B6: índice A-I (tabla de contenidos y numeración)
        calendario=_calendario(c), umbral_comprar=UMBRAL_COMPRAR, umbral_vender=UMBRAL_VENDER, legal=Markup(markdown.markdown(legal)),
        horizontes=["1m", "3m", "12m", "YTD", "3a", "5a"], claves_horizonte=["1m", "3m", "12m", "ytd", "3a", "5a"],
        etiquetas_comportamiento={k: "Absoluta" if k == "absoluta" else "Relativa " + k.replace("SPY", "S&P 500")
                                  for k in c["comportamiento"]},
    )


# Gráficos del perfil sectorial: barras + línea (importe y rentabilidad) y hasta tres ratios ((claves), en %)
GRAFICOS_SECTORIALES = {
    "banco": (("beneficio", "Beneficio neto", "rote", "ROTE"), (("roe", "rote", "eficiencia"), True)),
    "aseguradora": (("beneficio", "Beneficio neto", "roe", "ROE"), (("combinado", "siniestralidad", "gastos"), True)),
    "reit": (("ffo", "FFO", "ltv", "LTV"), (("payout_ffo", "ltv", "roe"), True)),
    "inversion": (("ingreso_neto_inversion", "Ingreso neto de inversiones", "rentabilidad_nii", "NII / patrimonio"),
                  (("cobertura_dividendo", "apalancamiento"), False)),
}


def _serie_sectorial(r, clave):
    v = r.metricas.get(clave)
    if v is None and clave in r.datos:
        v = r.datos[clave].valor
    return None if v is None or (isinstance(v, float) and v != v) else v


def _sectorial(c: dict) -> dict:
    """Tablas, gráficos, comparables, trazas y definiciones de la plantilla sectorial (cifras ya calculadas)."""
    from ..calculo.definiciones import COMUNES_SECTORIALES, DEFINICIONES_SECTORIALES
    from ..calculo.perfiles import IMPORTES, NOMBRES_ENTRADAS, POR_ACCION
    from ..calculo.valoracion_sectorial import MULTIPLO_PRINCIPAL, RENTABILIDAD
    from ..calculo.valoracion_sectorial import NOMBRES as NOMBRES_MULTIPLOS
    from .sectorial import CLAVE_SITUACION, CLAVES_PORTADA, formato_metrica

    p, h, ltm, r = c["perfil_def"], c["historico"], c["ltm"], c["resultado_periodo"]
    periodos = [(f"FY{a}", h[a]) for a in c["ejercicios"]] + ([(c["periodo"], ltm)] if ltm else [])

    def partida(res, k):
        d = res.datos.get(k)
        if d is None:
            return "n.d."
        if d.concepto is None:
            return "—"  # opcional y no declarada: cuenta como 0
        return _num(d.valor, 2) if k in POR_ACCION else _mn(d.valor)

    metricas = [{"nombre": m.nombre.replace("(USD)", "(USD mn)") if m.id in IMPORTES else m.nombre,
                 "valores": [formato_metrica(m.id, res.metricas.get(m.id), unidades=False) for _, res in periodos],
                 "clase": "total" if m.esencial else ""} for m in p.metricas]
    partidas = [{"nombre": NOMBRES_ENTRADAS[k] if k in POR_ACCION else f"{NOMBRES_ENTRADAS[k]} (USD mn)",
                 "valores": [partida(res, k) for _, res in periodos]} for k in p.entradas]
    por_id = {m.id: m for m in p.metricas}
    kpis = [{"valor": formato_metrica(k, r.metricas[k], unidades=False),
             "nombre": por_id[k].nombre.replace("(USD)", "(USD mn)") if k in IMPORTES else por_id[k].nombre} for k in CLAVES_PORTADA[p.id]]
    principal = MULTIPLO_PRINCIPAL[p.id]
    rent = RENTABILIDAD.get(p.id) or CLAVE_SITUACION[p.id]
    comparables = [{"nombre": x["nombre"], "ticker": x["ticker"], "ejercicio": x["ejercicio"],
                    "capitalizacion": _num(x["multiplos"]["capitalizacion"] / 1e9, 1) if x["multiplos"]["capitalizacion"] else "n.d.",
                    "rentabilidad": formato_metrica(rent, x["metricas"].get(rent)),
                    "principal": _env.filters["veces"](x["multiplos"].get(principal)),
                    "p_bv": _env.filters["veces"](x["multiplos"].get("p_bv")), "per": _env.filters["veces"](x["multiplos"].get("per"), 1),
                    "dividendo": _pct(x["multiplos"].get("rentabilidad_dividendo"))} for x in c["comparables"]]
    etiquetas = [f"FY{a % 100:02d}" for a in c["ejercicios"]]
    (barra, nombre_barra, linea, nombre_linea), (lineas, en_pct) = GRAFICOS_SECTORIALES[p.id]
    anuales = [h[a] for a in c["ejercicios"]]
    serie_barra = [(_serie_sectorial(x, barra) or 0) / 1e6 for x in anuales]
    g = {"base_100": Markup(graficos.base_100(c["series_bolsa"])),
         "principal": Markup(graficos.barras_y_linea(etiquetas, serie_barra, [_serie_sectorial(x, linea) for x in anuales],
                                                     nombre_barra, nombre_linea)),
         "ratios": Markup(graficos.lineas(etiquetas, {por_id[k].nombre: [_serie_sectorial(x, k) for x in anuales] for k in lineas},
                                          porcentaje=en_pct)),
         "titulo_principal": f"{nombre_barra} (USD mn) y {nombre_linea}",
         "titulo_ratios": " · ".join(por_id[k].nombre for k in lineas),
         **_grafico_rangos(c), **_grafico_historial(c)}
    trazas = [{"nombre": NOMBRES_ENTRADAS[k], "concepto": d.concepto or "— (no declarada: 0)",
               "valor": partida(r, k), "origen": d.accession or "—"} for k, d in r.datos.items()]
    definiciones = ([d for d in DEFINICIONES if (d[0], d[1]) in COMUNES_SECTORIALES] + list(DEFINICIONES_SECTORIALES)
                    + [(p.nombre, m.nombre, m.descripcion or m.nombre) for m in p.metricas])
    return dict(tabla={"cabecera": [e for e, _ in periodos], "metricas": metricas, "partidas": partidas}, kpis=kpis, g=g,
                comparables=comparables, trazas=trazas, definiciones=definiciones, nombre_principal=NOMBRES_MULTIPLOS[principal],
                nombre_rentabilidad=por_id[rent].nombre, rentabilidad_propia=formato_metrica(rent, r.metricas.get(rent)),
                principal=principal)


def html_sectorial(c: dict) -> str:
    return _env.get_template("informe_sectorial.html.j2").render(**_comunes(c), **_sectorial(c))


def html(c: dict) -> str:
    if c.get("perfil"):  # banca, seguros, REIT y BDC (B2)
        return html_sectorial(c)
    ejercicio = c["filing"]["ejercicio"]
    ultimo = ejercicio
    def _valor_traza(pid):
        v = c["estados"].valor(pid, ultimo)
        return _num(v, 2) if pid == "bpa_diluido" else _num(v / 1e6, 0) if pid == "acciones_diluidas" else _mn(v)

    trazas = [{"nombre": p.nombre, "concepto": c["estados"].datos[p.id][ultimo].concepto, "valor": _valor_traza(p.id),
               "origen": c["estados"].datos[p.id][ultimo].origen}
              for p in PARTIDAS if ultimo in c["estados"].datos.get(p.id, {})]
    claves_sens = sorted(c["dcf"].sensibilidad) if c["dcf"] else []
    claves_op = sorted(c["dcf"].sensibilidad_operativa or {}) if c["dcf"] else []
    ltm = etiqueta_ltm(c)
    return _env.get_template("informe.html.j2").render(
        **_comunes(c), f=c["fundamentales"][ejercicio], fl=c["fund_ltm"], g=_graficos(c), etiqueta_ltm=ltm, motor=_motor(c),
        ns_portada=any(v == "n.s." for fila in _resumen(c) for v in fila["valores"]),
        anios_est=c["etiquetas_estimadas"], resumen=_resumen(c), resumen_cabecera=[f"FY{a}" for a in c["ejercicios"][-2:]] + [ltm],
        estimados_portada=c["etiquetas_estimadas"][:ESTIMADOS_PORTADA], proyeccion=_proyeccion(c),
        comparables=_comparables(c), multiplos_def=MULTIPLOS, definiciones=DEFINICIONES, segmentos=_segmentos(c),
        trimestres=_trimestres(c), concentracion=_concentracion(c), publicaciones=_publicaciones(c), dupont=_dupont(c),
        flujo_balance=_flujo_balance(c), historicos=_historicos(c),
        estados=[{"titulo": t, "filas": _filas(c, filas)} for t, filas in ESTADOS], trazas=trazas,
        sens_w=sorted({w for w, _ in claves_sens}), sens_g=sorted({g for _, g in claves_sens}),
        sens_c=sorted({x for x, _ in claves_op}), sens_m=sorted({m for _, m in claves_op}),
    )


def pdf(c: dict, destino: Path) -> Path:
    from ..visual.pdf import html_a_pdf

    contenido = html(c)
    destino = Path(destino)
    destino.with_suffix(".html").write_text(contenido, encoding="utf-8")  # misma plantilla: vista previa
    html_a_pdf(contenido, destino, base_url=DIR_INFORME)
    return destino



@functools.lru_cache(maxsize=1)
def _recursos_incrustados() -> tuple[str, dict[str, str]]:
    """Hoja de estilos con las fuentes incrustadas y logos como data URI (una vez por proceso)."""
    import base64

    css = (DIR_INFORME / "estilo.css").read_text(encoding="utf-8")
    for fuente in ("Inter", "Montserrat"):
        datos = base64.b64encode((DIR / "fuentes" / f"{fuente}.ttf").read_bytes()).decode()
        css = css.replace(f'url("../fuentes/{fuente}.ttf")', f'url("data:font/ttf;base64,{datos}")')
    logos = {f"../marca/{n}.svg": "data:image/svg+xml;base64," + base64.b64encode((DIR / "marca" / f"{n}.svg").read_bytes()).decode()
             for n in ("logo", "nombre")}
    return css, logos


def html_autonomo(c: dict) -> str:
    """El mismo HTML del informe, autónomo (estilos, fuentes y logos dentro): vista previa de la interfaz (A12)."""
    css, logos = _recursos_incrustados()
    contenido = html(c).replace('<link rel="stylesheet" href="estilo.css">', f"<style>{css}</style>")
    for ruta, uri in logos.items():
        contenido = contenido.replace(f'src="{ruta}"', f'src="{uri}"')
    return contenido
