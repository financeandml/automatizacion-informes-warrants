"""Libro del motor para banca, seguros, REIT y BDC (decisión D4, 2026-10-14): la valoración de la B2 con fórmulas
vivas y la hoja de comparables de la plantilla (`trading-comps`), con los múltiplos del sector.

Hojas: Portada, Entradas, Datos del perfil (partidas de la SEC y métricas como fórmulas), Comps (múltiplos del sector,
estadísticas sin negativos ni no significativos y precio implícito por mínimo, media, mediana y máximo), Valoración
(valor contable justificado de Gordon, descuento de dividendos y comparables, como en calculo/valoracion_sectorial),
Síntesis y Controles. El valor de cada método del libro se contrasta con el de calculo/valoracion_sectorial: si no
coinciden, aviso (no bloquea).
"""

import math
from dataclasses import dataclass, field
from datetime import date

from ..valoracion_sectorial import MULTIPLO_PRINCIPAL
from .libro import LibroModelo, col, ref
from .modelo import avisos_de_calculo

# Métricas del perfil como fórmulas de Excel ({entrada} = su celda de la hoja Datos del perfil)
FORMULAS = {
    "nim": "={margen_intereses}/{activos}", "eficiencia": "={gastos_no_intereses}/({margen_intereses}+{ingresos_no_intereses})",
    "coste_riesgo": "={provisiones}/{prestamos}", "prestamos_depositos": "={prestamos}/{depositos}",
    "roa": "={beneficio}/{activos}",
    "rote": "=({beneficio}-{dividendos_preferentes})/({patrimonio}-{preferentes}-{fondo_comercio}-{intangibles})",
    "patrimonio_tangible": "={patrimonio}-{preferentes}-{fondo_comercio}-{intangibles}",
    "siniestralidad": "={siniestros}/{primas}", "gastos": "=({gastos_adquisicion}+{otros_gastos_suscripcion})/{primas}",
    "combinado": "=({siniestros}+{gastos_adquisicion}+{otros_gastos_suscripcion})/{primas}",
    "rendimiento_inversiones": "={ingresos_inversion}/{activos}",
    "ffo": "={beneficio}+{amortizacion}+{deterioros}-{ganancias_venta}",
    "payout_ffo": "={dividendos}/({beneficio}+{amortizacion}+{deterioros}-{ganancias_venta})", "ltv": "={deuda}/{activos}",
    "nav_por_accion": "={nav_por_accion}", "cobertura_dividendo": "={ingreso_neto_inversion}/{dividendos}",
    "apalancamiento": "={deuda}/{patrimonio}", "rentabilidad_nii": "={ingreso_neto_inversion}/{patrimonio}",
}
ROE = {"banco": "=({beneficio}-{dividendos_preferentes})/({patrimonio}-{preferentes})",
       "aseguradora": "=({beneficio}-{dividendos_preferentes})/({patrimonio}-{preferentes})",
       "reit": "={beneficio}/{patrimonio}", "inversion": "={beneficio}/{patrimonio}"}
POR_ACCION_USD = {"nav_por_accion"}


@dataclass
class ModeloSectorial:
    libro: LibroModelo
    valores: dict
    celdas: dict
    avisos: list[str] = field(default_factory=list)
    salidas: dict = field(default_factory=dict)


def construir(perfil, historico: dict, ltm, empresa: str, ticker: str, fecha: date, precio: float, acciones: float, rf: float, erp: float,
              beta: float, g: float, sostenible: float | None, origen_sostenible: str, comparables: list[dict], del_analista: bool,
              valoracion: dict, pesos: dict, metodos: tuple[str, ...], principal: str, base_nombre: str) -> ModeloSectorial:
    """Libro sectorial calculado y contrastado con la valoración de calculo/valoracion_sectorial (`valoracion`)."""
    libro = LibroModelo()
    celdas: dict[str, tuple] = {}
    anios = sorted(historico)
    periodos = [(f"FY{a}", historico[a]) for a in anios] + ([("LTM", ltm)] if ltm else [])
    r = ltm or historico[anios[-1]]
    # Portada y entradas
    portada = libro.hoja("Portada")
    portada.poner(2, 2, f"Modelo de valoración · {perfil.nombre} · Warrants & Co.", "titulo")
    portada.poner(4, 2, f"{empresa} ({ticker})")
    portada.poner(5, 2, fecha, "", "fecha")
    portada.poner(7, 2, perfil.valoracion)
    portada.poner(9, 2, "Entradas en azul; importes en millones de USD; precio y NAV por acción en USD. Datos: SEC (EDGAR) y mercado.")
    e = libro.hoja("Entradas")
    e.poner(2, 2, "Entradas del analista", "titulo")
    filas = [(4, "Cotización (USD)", precio, "usd", "yfinance"), (5, "Acciones en circulación (mn)", acciones / 1e6, "acc", "SEC (dei)"),
             (6, "Tipo libre de riesgo", rf, "pct", "Revisar"), (7, "Prima de riesgo de mercado", erp, "pct", "Revisar"),
             (8, "Beta (5 años, semanal)", beta, "num", "Revisar"), (9, "Crecimiento a perpetuidad (g)", g, "pct", "Revisar"),
             (11, "Rentabilidad sostenible del valor contable justificado", sostenible, "pct", f"{origen_sostenible} · Revisar")]
    for f, t, v, formato, nota in filas:
        e.poner(f, 2, t, "etiqueta")
        e.poner(f, 3, v if v is not None else "--", "entrada", formato, nota)
    e.poner(10, 2, "Coste del capital (Ke) = Rf + β × prima", "total")
    e.poner(10, 3, "=C6+C8*C7", "total", "pct")
    for i, n in enumerate(metodos):
        e.poner(13 + i, 2, f"Peso: {n}", "etiqueta")
        e.poner(13 + i, 3, pesos.get(n, 0.0), "entrada", "pct")
    # Datos del perfil: partidas de la SEC y métricas como fórmulas
    d = libro.hoja("Datos del perfil")
    d.poner(1, 1, f"{empresa} ({ticker}) · {perfil.nombre}", "titulo")
    d.fila(3, 2, [e for e, _ in periodos], "cabecera")
    from ..perfiles import NOMBRES_ENTRADAS
    fila = {}
    for i, clave in enumerate(perfil.entradas):
        f = 5 + i
        fila[clave] = f
        d.poner(f, 1, NOMBRES_ENTRADAS.get(clave, clave), "etiqueta")
        for j, (_, res) in enumerate(periodos):
            dato = res.datos.get(clave)
            if dato is None:
                continue
            escala = 1 if clave in POR_ACCION_USD else 1e6
            d.poner(f, 2 + j, dato.valor / escala, "entrada", "usd" if clave in POR_ACCION_USD else "mn",
                    f"{dato.concepto} · {dato.accession}" if dato.concepto else "Partida opcional no declarada: 0")
    f0 = 6 + len(perfil.entradas)
    d.poner(f0, 1, "Métricas del perfil", "seccion")
    fila_metrica = {}
    for i, m in enumerate(perfil.metricas):
        f = f0 + 1 + i
        fila_metrica[m.id] = f
        d.poner(f, 1, m.nombre, "etiqueta")
        plantilla = ROE[perfil.id] if m.id == "roe" else FORMULAS.get(m.id)
        for j in range(len(periodos)):
            c = 2 + j
            celdas_entrada = {k: ref(fila[k], c) for k in perfil.entradas}
            formula = plantilla.format(**celdas_entrada)
            formato = "usd" if m.id in POR_ACCION_USD else ("mn" if m.id in ("ffo", "patrimonio_tangible") else "pct")
            d.poner(f, c, f'=IFERROR({formula[1:]},"n.d.")', "", formato)
    ultima = 1 + len(periodos)  # columna del periodo de la valoración (LTM o último ejercicio)
    # Comparables (Trading Comps, múltiplos del sector)
    cp = libro.hoja("Comps")
    cp.poner(2, 2, "Comps Tables", "titulo")
    cab = {2: "Ticker", 3: "Company Name", 4: "Price", 5: "Shares (mn)", 6: "Market Cap", 7: "Book value (common)",
           8: "Base del múltiplo principal",
           9: "Net Income", 10: "Dividends", 12: "P / Book value", 13: principal, 14: "P / E", 15: "Dividend yield"}
    for c, t in cab.items():
        cp.poner(10, c, t, "cabecera")
    filas_cp = [(None, 12)] + [(x, 14 + i) for i, x in enumerate(comparables)]
    for x, f in filas_cp:
        if x is None:
            vals, tk, nombre, pr, acc = {k: dd.valor for k, dd in r.datos.items()}, ticker, empresa, precio, acciones
            metr = r.metricas
        else:
            vals, tk, nombre, metr = x.get("valores") or {}, x["ticker"], x["nombre"], x["metricas"]
            pr, acc = x.get("precio"), x.get("acciones")
        cp.poner(f, 2, tk, "total" if x is None else "etiqueta")
        cp.poner(f, 3, nombre)
        if pr is None or not acc:  # sin datos de partida: el múltiplo ya calculado, como entrada trazada
            mx = x.get("multiplos") or {} if x is not None else {}
            for c, clave in ((12, "p_bv"), (13, MULTIPLO_PRINCIPAL[perfil.id]), (14, "per")):
                if mx.get(clave) is not None:
                    cp.poner(f, c, mx[clave], "entrada", "x", "Múltiplo del cálculo del informe (comparable sin datos de partida)")
            continue
        cp.poner(f, 4, pr, "entrada", "usd")
        cp.poner(f, 5, acc / 1e6, "entrada", "acc")
        cp.poner(f, 6, f"=D{f}*E{f}", "", "mn")
        comun = (vals.get("patrimonio") or 0) - (vals.get("preferentes") or 0)
        cp.poner(f, 7, comun / 1e6, "entrada", "mn", "Patrimonio − preferentes (SEC)")
        base = {"banco": metr.get("patrimonio_tangible"), "aseguradora": comun, "reit": metr.get("ffo"),
                "inversion": (metr.get("nav_por_accion") or 0) * acc}.get(perfil.id)
        if base is not None and not (isinstance(base, float) and math.isnan(base)):
            cp.poner(f, 8, base / 1e6, "entrada", "mn", "Patrimonio tangible, FFO o NAV × acciones (perfil)")
        beneficio = (vals.get("beneficio") or 0) - (vals.get("dividendos_preferentes") or 0)
        cp.poner(f, 9, beneficio / 1e6, "entrada", "mn")
        if vals.get("dividendos"):
            cp.poner(f, 10, vals["dividendos"] / 1e6, "entrada", "mn")
        for c, numerador, den in ((12, "F", "G"), (13, "F", "H"), (14, "F", "I")):
            xx = f"{numerador}{f}/{den}{f}"  # solo positivos (la regla de la valoración sectorial B2)
            cp.poner(f, c, f'=IF(ISERROR({xx}),"n.s.",IF({xx}>0,{xx},"n.s."))', "", "x")
        cp.poner(f, 15, f'=IF(ISERROR(J{f}/F{f}),"--",J{f}/F{f})', "", "pct")
    u = 13 + len(comparables)
    estadisticas = (("Minimum", u + 2, "MIN"), ("Mean", u + 3, "AVERAGE"), ("Median", u + 4, "MEDIAN"), ("Maximum", u + 5, "MAX"))
    for etiqueta, k, funcion in estadisticas:
        cp.poner(k, 2, etiqueta, "total" if etiqueta == "Median" else "etiqueta")
        for c in (12, 13, 14):
            rango = f"{col(c)}14:{col(c)}{u}"
            cp.poner(k, c, f'=IF(COUNT({rango})<3,"--",{funcion}({rango}))' if comparables else '="--"', "", "x")
        cp.poner(k, 17, f'=IF(ISNUMBER(M{k}),M{k}*$H$12/Entradas!$C$5,"--")', "", "usd")  # precio implícito
    cp.poner(u + 1, 17, "Implied price (USD)", "cabecera")
    celdas["comps_mediana"] = ("Comps", u + 4, 17)
    # Valoración (B2 con fórmulas)
    v = libro.hoja("Valoración")
    v.poner(2, 2, f"Valoración {perfil.nombre}", "titulo")
    v.poner(4, 2, "Método", "cabecera")
    v.poner(4, 3, "Valor (USD)", "cabecera")
    v.poner(4, 4, "Bajo (Ke + 1 pp)", "cabecera")
    v.poner(4, 5, "Alto (Ke − 1 pp)", "cabecera")
    v.poner(4, 6, "Peso", "cabecera")
    celda = lambda clave: f"'Datos del perfil'!{ref(fila[clave], ultima)}"  # noqa: E731
    if perfil.id == "banco":
        base_accion = f"'Datos del perfil'!{ref(fila_metrica['patrimonio_tangible'], ultima)}/Entradas!C5"
    elif perfil.id == "aseguradora":
        base_accion = f"({celda('patrimonio')}{'-' + celda('preferentes') if 'preferentes' in fila else ''})/Entradas!C5"
    elif perfil.id == "inversion":
        base_accion = celda("nav_por_accion")
    else:
        base_accion = "0"
    v.poner(6, 2, f"Base por acción ({base_nombre})", "etiqueta")
    v.poner(6, 3, f"={base_accion}", "", "usd")
    for i, n in enumerate(metodos):
        f = 8 + i
        v.poner(f, 2, n, "etiqueta")
        v.poner(f, 6, f"=Entradas!C{13 + i}", "", "pct")
        if n == "Valor contable justificado":
            def gordon(ke):
                return (f'IF(OR(Entradas!$C$11<=Entradas!$C$9,{ke}<=Entradas!$C$9),"--",'
                        f'(Entradas!$C$11-Entradas!$C$9)/({ke}-Entradas!$C$9)*$C$6)')
            v.poner(f, 3, f"={gordon('Entradas!$C$10')}", "", "usd")
            v.poner(f, 4, f"={gordon('(Entradas!$C$10+0.01)')}", "", "usd")
            v.poner(f, 5, f"={gordon('(Entradas!$C$10-0.01)')}", "", "usd")
        elif n == "Descuento de dividendos":
            dpa = f"'Datos del perfil'!{ref(fila['dividendos'], ultima)}/Entradas!$C$5"
            ddm = lambda ke, dpa=dpa: f'IF(OR({dpa}<=0,{ke}<=Entradas!$C$9),"--",{dpa}*(1+Entradas!$C$9)/({ke}-Entradas!$C$9))'  # noqa: E731
            v.poner(f, 3, f"={ddm('Entradas!$C$10')}", "", "usd")
            v.poner(f, 4, f"={ddm('(Entradas!$C$10+0.01)')}", "", "usd")
            v.poner(f, 5, f"={ddm('(Entradas!$C$10-0.01)')}", "", "usd")
        else:
            v.poner(f, 3, f'=IF({str(del_analista).upper()},Comps!Q{u + 4},"--")', "", "usd")
            v.poner(f, 4, f'=IF({str(del_analista).upper()},Comps!Q{u + 2},"--")', "", "usd")
            v.poner(f, 5, f'=IF({str(del_analista).upper()},Comps!Q{u + 5},"--")', "", "usd")
        celdas[f"metodo_{n}"] = ("Valoración", f, 3)
    fin = 8 + len(metodos) - 1
    v.poner(fin + 2, 2, "Precio objetivo del modelo (media ponderada de los métodos con valor)", "total")
    numerador = "+".join(f"IF(ISNUMBER(C{f}),C{f}*F{f},0)" for f in range(8, fin + 1))
    denominador = "+".join(f"IF(ISNUMBER(C{f}),F{f},0)" for f in range(8, fin + 1))
    v.poner(fin + 2, 3, f'=IFERROR(({numerador})/({denominador}),"--")', "total", "usd")
    celdas["precio_modelo"] = ("Valoración", fin + 2, 3)
    s = libro.hoja("Síntesis")
    s.poner(2, 2, "Síntesis (USD por acción)", "titulo")
    s.poner(4, 2, "Cotización", "etiqueta")
    s.poner(4, 3, "=Entradas!C4", "", "usd")
    s.poner(5, 2, "Precio objetivo del modelo", "total")
    s.poner(5, 3, f"=Valoración!C{fin + 2}", "total", "usd")
    s.poner(6, 2, "Potencial", "etiqueta")
    s.poner(6, 3, '=IF(ISNUMBER(C5),C5/C4-1,"--")', "", "pct")
    # Valores en Python y contraste con calculo/valoracion_sectorial
    valores, marcadas, errores = libro.calcular()
    discrepancias = []
    for n in metodos:
        en_libro = valores.get(celdas[f"metodo_{n}"])
        en_python = (valoracion.get("metodos") or {}).get(n, {}).get("valor")
        a = en_libro if isinstance(en_libro, float) else None
        if (a is None) != (en_python is None) or (a is not None and not math.isclose(a, en_python, rel_tol=1e-6)):
            discrepancias.append(f"Motor de valoración: «{n}» da {a} en el libro y {en_python} en el cálculo del informe")
    for m in perfil.metricas:
        en_libro = valores.get(("Datos del perfil", fila_metrica[m.id], ultima))
        en_python = r.metricas.get(m.id)
        if isinstance(en_libro, float) and en_python is not None and not math.isnan(en_python):
            escala = 1 if m.id in POR_ACCION_USD else (1e6 if m.id in ("ffo", "patrimonio_tangible") else 1)
            if not math.isclose(en_libro * escala, en_python, rel_tol=1e-6):
                discrepancias.append(f"Motor de valoración: la métrica «{m.nombre}» no coincide entre el libro y el perfil")
    ctl = libro.hoja("Controles")
    ctl.poner(2, 2, "Controles", "titulo")
    ctl.poner(4, 2, "Métodos y métricas del libro = cálculo del informe", "etiqueta")
    ctl.poner(4, 3, not discrepancias and not errores)
    avisos = avisos_de_calculo(marcadas, errores) + discrepancias
    ctl.poner(5, 2, "Ke > g", "etiqueta")
    ctl.poner(5, 3, "=Entradas!C10>Entradas!C9")
    valores = libro.calcular()[0]
    return ModeloSectorial(libro, valores, celdas, avisos, {k: valores.get(c) for k, c in celdas.items()})

