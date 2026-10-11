"""Del contexto del informe (informe/construir.py) al HTML y al PDF.

La misma plantilla HTML sirve para la vista previa y para el PDF. Aquí solo se da formato: todas
las cifras vienen ya calculadas del motor matemático.
"""

from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from ..calculo.normalizador import PARTIDAS
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


def _filas(c, filas):
    salida = []
    for nombre, fuente, clave, formato, clase in filas:
        valores = []
        for a in c["ejercicios"]:
            v = c["estados"].valor(clave, a) if fuente == "e" else c["fundamentales"][a][clave]
            valores.append(_pct(v) if formato == "%" else _num(v, 2) if formato == "x2" else _mn(v))
        salida.append({"nombre": nombre, "valores": valores, "clase": clase})
    return salida


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
        ("Flujo de caja libre (FCF)", "f", "fcf", "mn", "total"), ("Amortizaciones (D&A)", "e", "amortizacion", "mn", ""),
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


def _resumen(c):
    ej = c["ejercicios"][-3:]
    fund, d = c["fundamentales"], c["dcf"]
    est = c["estimaciones"]
    ebitda_est = [v * m for v, m in zip(d.ingresos, est.margen_ebitda, strict=True)]
    filas = [
        ("Ingresos", [_mn(fund[a]["ingresos"]) for a in ej] + [_mn(v) for v in d.ingresos]),
        ("Crecimiento", [_pct(fund[a]["crecimiento_ingresos"]) for a in ej] + [_pct(g) for g in est.crecimiento_ventas]),
        ("EBITDA", [_mn(fund[a]["ebitda"]) for a in ej] + [_mn(v) for v in ebitda_est]),
        ("Margen EBITDA", [_pct(fund[a]["margen_ebitda"]) for a in ej] + [_pct(m) for m in est.margen_ebitda]),
        ("Beneficio neto", [_mn(fund[a]["beneficio_neto"]) for a in ej] + ["—"] * len(d.ingresos)),
        ("BPA diluido (USD)", [_num(fund[a]["bpa_diluido"], 2) for a in ej] + ["—"] * len(d.ingresos)),
        ("FCF (FCFF en e)", [_mn(fund[a]["fcf"]) for a in ej] + [_mn(v) for v in d.flujos]),
        ("Deuda neta / EBITDA", [_num(fund[a]["dfn_ebitda"], 2) for a in ej] + ["—"] * len(d.ingresos)),
        ("ROIC", [_pct(fund[a]["roic"]) for a in ej] + ["—"] * len(d.ingresos)),
    ]
    return [{"nombre": n, "valores": v} for n, v in filas]


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
    claves_sens = sorted(c["dcf"].sensibilidad)
    legal = (DIR / "legal" / "descargo.md").read_text(encoding="utf-8").replace("{{ anio }}", str(date.today().year))
    return _env.get_template("informe.html.j2").render(
        c=c, f=c["fundamentales"][ejercicio], t={k: _md(v) for k, v in c["textos"].items()},
        g=_graficos(c), fecha_larga=_fecha_larga(c["fecha"]),
        anios_est=[ejercicio + i + 1 for i in range(len(c["dcf"].flujos))], resumen=_resumen(c),
        estados=[{"titulo": t, "filas": _filas(c, filas)} for t, filas in ESTADOS], trazas=trazas,
        horizontes=["1m", "3m", "12m", "YTD", "3a", "5a"], claves_horizonte=["1m", "3m", "12m", "ytd", "3a", "5a"],
        sens_w=sorted({w for w, _ in claves_sens}), sens_g=sorted({g for _, g in claves_sens}),
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

