"""Del contexto del informe (informe/construir.py) al HTML y al PDF.

La misma plantilla HTML sirve para la vista previa y para el PDF. Aquí solo se da formato: todas
las cifras vienen ya calculadas del motor matemático.
"""

from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from ..calculo.definiciones import DEFINICIONES
from ..calculo.normalizador import LTM, PARTIDAS
from ..calculo.valoracion_relativa import MULTIPLOS, significativo
from ..visual import graficos
from .plantillas import MARCADOR, _num, _pct, _var

DIR = Path(__file__).resolve().parent.parent / "plantillas"
DIR_INFORME = DIR / "informe"
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")

_env = Environment(loader=FileSystemLoader(DIR_INFORME), undefined=StrictUndefined, autoescape=True)
_env.filters.update(num=_num, pct=_pct, var=_var)


def _md(texto: str) -> Markup:
    """Markdown → HTML; cada marcador [[ANALISTA: …]] queda como recuadro visible del borrador."""
    con_marcas = MARCADOR.sub(lambda m: f'<span class="pendiente">{m.group(1).strip()}</span>', texto)
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
        ("Crecimiento", hist("crecimiento_ingresos", _pct) + [_pct(g) for g in est.crecimiento_ventas[:len(p)]]),
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
                      "crecimiento": _pct(f.get("crecimiento_ingresos")), "margen": _pct(f.get("margen_ebitda")), "multiplos": celdas})
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
    }


def html(c: dict) -> str:
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
    legal = (DIR / "legal" / "descargo.md").read_text(encoding="utf-8").replace("{{ anio }}", str(date.today().year))
    ltm = etiqueta_ltm(c)
    return _env.get_template("informe.html.j2").render(
        c=c, f=c["fundamentales"][ejercicio], fl=c["fund_ltm"], t={k: _md(v) for k, v in c["textos"].items()},
        g=_graficos(c), fecha_larga=_fecha_larga(c["fecha"]), etiqueta_ltm=ltm,
        anios_est=c["etiquetas_estimadas"], resumen=_resumen(c), resumen_cabecera=[f"FY{a}" for a in c["ejercicios"][-2:]] + [ltm],
        estimados_portada=c["etiquetas_estimadas"][:ESTIMADOS_PORTADA], proyeccion=_proyeccion(c),
        comparables=_comparables(c), multiplos_def=MULTIPLOS, definiciones=DEFINICIONES,
        estados=[{"titulo": t, "filas": _filas(c, filas)} for t, filas in ESTADOS], trazas=trazas,
        horizontes=["1m", "3m", "12m", "YTD", "3a", "5a"], claves_horizonte=["1m", "3m", "12m", "ytd", "3a", "5a"],
        sens_w=sorted({w for w, _ in claves_sens}), sens_g=sorted({g for _, g in claves_sens}),
        sens_c=sorted({x for x, _ in claves_op}), sens_m=sorted({m for _, m in claves_op}),
        legal=Markup(markdown.markdown(legal)),
        etiquetas_comportamiento={k: "Absoluta" if k == "absoluta" else "Relativa " + k.replace("SPY", "S&P 500")
                                  for k in c["comportamiento"]},
    )


def pdf(c: dict, destino: Path) -> Path:
    from ..visual.pdf import html_a_pdf

    contenido = html(c)
    destino = Path(destino)
    destino.with_suffix(".html").write_text(contenido, encoding="utf-8")  # misma plantilla: vista previa
    html_a_pdf(contenido, destino, base_url=DIR_INFORME)
    return destino

