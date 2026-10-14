"""Hojas LBO, LBO Shares y Acreción-dilución del modelo de valoración (plantillas `advanced-lbo-part-3` y
`accretion-dilution`, fila a fila, con las entradas en azul dentro de su hoja, como en las plantillas).

LBO: TIR y MOIC de un comprador financiero que paga la cotización + prima. Caso 1 (conservador) con los márgenes
de la historia y sus escalones; caso 2 (dirección) = el escenario del propio modelo operativo (ventas, EBIT y D&A),
que en la plantilla era el plan de la dirección tecleado. Valores por defecto: las proporciones de la plantilla
(Burger King, 2010): deuda por tramos en veces EBITDA, tipos, comisiones, plazos, prima, comisiones de la operación
y caja mínima; los escalones de márgenes de la plantilla eran del plan de Burger King: por defecto, 0 (Revisar).

Correcciones del LBO (además de E1, E2 y E10 del modelo): E21 EBIT conservador sin autorreferencia; E22 intangibles
sin circularidad (compras 0); E23 signo de otros activos y pasivos a largo plazo en el flujo de caja; E24 amortización
total de la deuda con los pagos obligatorios y el PIK; E25 tipo PIK en todos los años; E26 acciones diluidas con
opciones y RSU; E27 depreciación del inmovilizado = la del caso elegido; E28 amortización de las comisiones de
financiación como gasto financiero no monetario; E29 «otros usos» como coste de la operación (la plantilla los
activaba en el balance de apertura y no los arrastraba). Con E27-E29 el balance pro forma cuadra (el de la plantilla no:
−32,7 a −37,8 al año). E30: la comprobación de la deuda (inicial − amortización = final) con tolerancia relativa, no
igualdad exacta: sobre valores de un cálculo iterativo, la igualdad exacta depende del residuo de la iteración. E31: las
preferentes que la operación no amortiza se mantienen en el balance proyectado (la plantilla no tenía preferentes).
E11 (proveedores sobre el coste de ventas) no se aplica: el caso de la dirección no tiene coste de ventas; se mantiene
la plantilla (sobre ventas).

Acreción-dilución: el comprador es la empresa del informe; el objetivo, el que indique el analista. E13: el BPA
recurrente *pro forma* no resta las comisiones de la operación (son únicas: van en fuentes y usos).
"""

from dataclasses import dataclass, field

# Proporciones de la plantilla LBO (valores que guardó Excel en `advanced-lbo-part-3`)
TRAMOS = (  # nombre, veces EBITDA, tipo, comisión, plazo
    ("Revolver", 0.0, 0.045, 0.0, 5), ("Term loan A", 3.396311291048136, 0.0682, 0.027, 6),
    ("Term loan B", 0.7516869095816471, 0.0711, 0.0251, 6), ("Senior notes", 1.7993702204228534, 0.1019, 0.0251, 8),
    ("Subordinated notes", 0.0, 0.10, 0.0, 5))
PIK_TIPO = 0.05
PRIMA = 0.27253446447507956  # 24 / 18,86 − 1
COMISIONES_OPERACION = 91.2 / 3893.2354080000005  # sobre el EV de entrada
OTROS_USOS = 32.32617199999959 / 3893.2354080000005
CAJA_MINIMA = 118.19999999999999 / 2502.2  # sobre las ventas del último ejercicio
REVOLVER_MAXIMO = 150 / 444.5999999999996  # veces EBITDA
BARRIDO = (1.0, 1.0, 0.0)  # Term loan A, Term loan B, Senior notes


@dataclass
class EntradasAD:
    """Acreción-dilución: términos de la operación (los pone el analista)."""

    objetivo: str
    precio: float
    acciones: float  # millones
    bpa: float
    prima: float = 0.25
    acciones_pct: float = 1 / 3
    deuda_pct: float = 1 / 3
    plazo: int = 5
    tipo: float = 0.07
    comisiones_financiacion_pct: float = 100 / (100 * 1.25 * 50 / 3)  # plantilla: 100 sobre 2.083 de deuda nueva
    comisiones_operacion_pct: float = 50 / (100 * 1.25 * 50)  # plantilla: 50 sobre 6.250 de precio
    tipo_impositivo: float = 0.20
    sinergias: float = 0.0
    interes_caja: float = 0.015
    valor_contable: float = 0.0
    valor_razonable: float = 0.0
    vida_util: int = 15
    bpa_comprador: float | None = None
    otros: dict = field(default_factory=dict)


def hojas_lbo(k) -> None:
    """`k`: el `_Constructor` del modelo (datos, celdas de las hojas de datos y utilidades de trazabilidad)."""
    d = k.d
    h = k.libro.hoja("LBO")
    est = d.estados
    anios = [d.ejercicio - 2, d.ejercicio - 1, d.ejercicio]  # D, E, F
    hist = dict(zip((4, 5, 6), anios, strict=True))
    proy = (7, 8, 9, 10, 11)  # G..K = FY+1..FY+5 ↔ modelo operativo H..L
    om = "'Operating Model'!"
    dato = lambda p, a: est.datos.get(p, {}).get(a)  # noqa: E731

    def valor(fila, c, partida, signo=1):
        a = hist[c]
        x = dato(partida, a)
        if x is not None:
            h.poner(fila, c, signo * x.valor / 1e6, "entrada", "mn", f"{x.concepto} · {x.origen}")
            k.trazas.append(("LBO", f"{chr(64 + c)}{fila}", partida, x.concepto, f"FY{a}", x.origen, signo * x.valor / 1e6))

    h.poner(2, 2, "LBO", "titulo")
    h.poner(4, 2, "Switches", "seccion")
    filas = [(6, "Circuit breaker", "OFF", None, "OFF = intereses sobre saldos medios (cálculo circular); ON = sin intereses"),
             (7, "Case", 2, '=IF(E7=1,"Conservative","Management")', "1 = conservador (márgenes de la historia); 2 = el modelo operativo"),
             (8, "Subordinated notes", 2, '=IF(E8=1,"Cash","PIK")', "1 = intereses en efectivo; 2 = PIK")]
    for f, t, v, formula, nota in filas:
        h.poner(f, 2, t, "etiqueta")
        h.poner(f, 5, v, "entrada", None, nota)
        if formula:
            h.poner(f, 6, formula)
    k.libro.validaciones += [("LBO", "E6", "ON,OFF"), ("LBO", "E7", "1,2"), ("LBO", "E8", "1,2")]
    k.libro.nombres.update(CASE="LBO!$E$7", CIRC="LBO!$E$6", PIK="LBO!$E$8")
    h.poner(6, 9, "IRR (for reference)", "etiqueta")
    h.poner(6, 11, "=K299", "", "pct")
    h.poner(7, 9, "Revolver Check", "etiqueta")
    h.poner(7, 11, "=G215")
    h.poner(10, 2, "Assumptions", "seccion")
    h.poner(12, 2, "Transaction Background", "cabecera")
    h.poner(12, 8, "Valuation at Entry", "cabecera")
    h.poner(13, 2, "Company name", "etiqueta")
    h.poner(13, 5, d.empresa)
    h.poner(14, 2, "Ticker", "etiqueta")
    h.poner(14, 5, d.ticker)
    h.poner(15, 2, "Latest closing share price", "etiqueta")
    h.poner(15, 5, "=Entradas!C7", "", "usd")
    h.poner(16, 2, "Latest closing share price date", "etiqueta")
    h.poner(16, 5, "=Entradas!C5", "", "fecha")
    h.poner(13, 8, "Offer value / share", "etiqueta")
    h.poner(13, 11, "=E15*(1+L14)", "", "usd")
    h.poner(14, 8, "% Premium / discount", "etiqueta")
    h.poner(14, 11, "=K13/E15-1", "", "pct")
    h.poner(14, 12, PRIMA, "entrada", "pct", "Prima de la plantilla (24 / 18,86 − 1) · Revisar")
    for f, t, formula, formato in ((16, "Offer value (Equity value)", "=K13*K17", "mn"), (17, "Diluted shares outstanding",
                                                                                          "='LBO Shares'!E16", "acc"),
                                   (19, "Debt", "=E21", "mn"), (20, "Cash", "=E22", "mn"), (22, "Enterprise Value", "=K16+K19-K20", "mn"),
                                   (23, "LTM EBITDA", "=E20", "mn"), (24, "Entry Multiple", "=K22/K23", "x")):
        h.poner(f, 8, t, "etiqueta")
        h.poner(f, 11, formula, "", formato)
    h.poner(19, 2, "Transaction Financials and Assumptions", "cabecera")
    h.poner(20, 2, "LTM EBITDA", "etiqueta")
    h.poner(20, 5, "=F98", "", "mn")
    # Balance del último ejercicio en todo el LBO (como la plantilla): el balance pro forma cuadra con su historia
    df = lambda p: dato(p, d.ejercicio)  # noqa: E731
    fy = f"FY{d.ejercicio}"
    h.poner(21, 2, "Debt", "etiqueta")
    k._teclear(h, 21, 5, [("Deuda a c/p", "deuda_cp", df("deuda_cp")), ("Deuda a l/p", "deuda_lp", df("deuda_lp"))], periodo=fy)
    h.poner(22, 2, "Cash", "etiqueta")
    k._teclear(h, 22, 5, [("Caja", "caja", df("caja")), ("Inversiones a c/p", "inversiones_cp", df("inversiones_cp"))], periodo=fy)
    h.poner(23, 2, "Minimum Cash", "etiqueta")
    h.poner(23, 5, "=MIN(E22,F61*F23)", "", "mn")
    h.poner(23, 6, CAJA_MINIMA, "entrada", "pct", "Caja mínima sobre ventas de la plantilla (118,2 / 2.502,2) · Revisar")
    h.poner(24, 2, "Exit Multiple", "etiqueta")
    h.poner(24, 5, "=K24", "", "x")
    h.poner(26, 2, "Capital Structure", "seccion")
    for c, t in ((5, "Amount"), (6, "xEBITDA"), (7, "Interest (%)"), (8, "Fees (%)"), (9, "Fee ($)"), (10, "Term"), (11, "Amortization")):
        h.poner(27, c, t, "cabecera")
    for i, (nombre, veces, tipo, comision, plazo) in enumerate(TRAMOS):
        f = 28 + i
        h.poner(f, 2, nombre, "etiqueta")
        h.poner(f, 5, f"=M{f}*$E$20", "", "mn")
        h.poner(f, 13, veces, "entrada", "x", "Veces EBITDA de la plantilla · Revisar")
        h.poner(f, 6, f"=E{f}/$E$20", "", "x")
        h.poner(f, 7, tipo, "entrada", "pct")
        h.poner(f, 8, comision, "entrada", "pct")
        h.poner(f, 9, f"=E{f}*H{f}", "", "mn")
        h.poner(f, 10, plazo, "entrada", "anio")
        h.poner(f, 11, f'=IF(ISERROR(I{f}/J{f}),"--",I{f}/J{f})', "", "mn")
    h.poner(27, 13, "xEBITDA (input)", "cabecera")
    h.poner(31, 12, "PIK")
    h.poner(32, 12, PIK_TIPO, "entrada", "pct", "Tipo PIK de la plantilla")
    h.poner(34, 2, "Total", "total")
    for c in (5, 6, 9, 11):
        h.poner(34, c, f"=SUM({chr(64 + c)}28:{chr(64 + c)}32)", "total", "x" if c == 6 else "mn")
    # Fuentes y usos
    h.poner(36, 2, "Sources and Uses", "seccion")
    h.poner(38, 2, "Sources", "cabecera")
    h.poner(38, 8, "Uses", "cabecera")
    for c, t in ((4, "Amount"), (5, "xEBITDA"), (6, "% Capital"), (9, "Amount"), (10, "xEBITDA"), (11, "% Capital")):
        h.poner(39, c, t, "cabecera")
    for i in range(4):
        f = 40 + i
        h.poner(f, 2, f"=B{28 + i}")
        h.poner(f, 4, f"=E{28 + i}", "", "mn")
    h.poner(44, 2, "Subordinated Notes")
    h.poner(44, 4, "=E32", "", "mn")
    h.poner(45, 2, "Cash on hand")
    h.poner(45, 4, "=E22-E23", "", "mn")
    h.poner(46, 2, "Sponsor equity", "total")
    h.poner(46, 4, "=D48-SUM(D40:D45)", "total", "mn")
    for f in range(40, 47):
        h.poner(f, 5, f"=D{f}/$E$20", "", "x")
        h.poner(f, 6, f"=D{f}/$D$48", "", "pct")
    usos = [(40, "Equity payment", "=K16"), (41, "Debt refinancing", "=E21"), (42, "Transaction fees", "=L42*K22"),
            (43, "Financing fees", "=I34"), (45, "Other", "=L45*K22")]
    for f, t, formula in usos:
        h.poner(f, 8, t, "etiqueta")
        h.poner(f, 9, formula, "", "mn")
        h.poner(f, 10, f"=I{f}/$E$20", "", "x")
        h.poner(f, 11, f"=I{f}/$I$48", "", "pct")
    h.poner(42, 12, COMISIONES_OPERACION, "entrada", "pct", "Comisiones de la operación sobre el EV de la plantilla (91,2 / 3.893)")
    h.poner(45, 12, OTROS_USOS, "entrada", "pct", "Otros usos sobre el EV de la plantilla (32,3 / 3.893)")
    h.poner(48, 2, "Total", "total")
    h.poner(48, 4, "=I48", "total", "mn")
    h.poner(48, 5, "=SUM(E40:E46)", "total", "x")
    h.poner(48, 6, "=SUM(F40:F46)", "total", "pct")
    h.poner(48, 8, "Total", "total")
    h.poner(48, 9, "=SUM(I40:I45)", "total", "mn")
    h.poner(48, 10, "=SUM(J40:J45)", "total", "x")
    h.poner(48, 11, "=SUM(K40:K45)", "total", "pct")
    # Modelo operativo del LBO
    h.poner(50, 2, f"Financials ({d.cierre_ejercicio.strftime('%d/%m')} FYE)", "seccion")

    def anios_fila(f):
        h.poner(f, 4, anios[0], "cabecera", "anio")
        for c in range(5, 12):
            h.poner(f, c, f"={chr(63 + c)}{f}+1", "cabecera", "anio")

    anios_fila(52)
    h.poner(52, 2, "Assumptions", "cabecera")
    h.poner(52, 13, "Step", "cabecera")
    h.poner(54, 2, "Revenue growth")
    h.poner(54, 4, "--")
    for c in range(5, 12):
        h.poner(54, c, f"={chr(64 + c)}61/{chr(63 + c)}61-1", "", "pct")
    for f, t, num, signo in ((55, "Gross margin", 67, "+"), (56, "OpEx margin", 70, "-")):
        h.poner(f, 2, t)
        for c in hist:
            h.poner(f, c, f"={chr(64 + c)}{num}/{chr(64 + c)}61", "", "pct")
        h.poner(f, 7, f"=F{f}", "", "pct")
        for c in range(8, 12):
            h.poner(f, c, f"={chr(63 + c)}{f}{signo}$M${f}", "", "pct")
    h.poner(57, 2, "Tax rate")
    for c in hist:
        h.poner(57, c, f"={chr(64 + c)}88/{chr(64 + c)}85", "", "pct")
    for c in proy:
        h.poner(57, c, f"={chr(63 + c)}57-$M$57", "", "pct")
    for f in (54, 55, 56, 57):
        h.poner(f, 13, 0.0, "entrada", "pct", "La plantilla traía los escalones del plan de Burger King (0; +1,75 pp; −2,2 pp; −0,5 pp): "
                "por defecto 0 (márgenes constantes) · Revisar")
    anios_fila(59)
    h.poner(59, 2, "Operating Model", "seccion")
    # Ventas, coste, beneficio bruto, gastos y EBIT
    h.poner(61, 2, "Revenue", "etiqueta")
    for c in hist:
        valor(61, c, "ingresos")
    for c in proy:
        h.poner(61, c, f"={om}{chr(64 + c + 1)}{k.om['ventas']}", "", "mn")
    h.poner(62, 2, "% growth")
    for c in range(4, 12):
        h.poner(62, c, f"={chr(64 + c)}54", "", "pct")
    h.poner(64, 2, "COGS", "etiqueta")
    for c in hist:
        valor(64, c, "coste_ventas")
    h.poner(65, 2, "% of sales")
    h.poner(67, 2, "Gross Profit", "etiqueta")
    h.poner(68, 2, "% of sales")
    h.poner(70, 2, "OpEx", "etiqueta")
    h.poner(71, 2, "% of sales")
    for c in hist:
        a = hist[c]
        h.poner(65, c, f"={chr(64 + c)}64/{chr(64 + c)}61", "", "pct")
        h.poner(67, c, f"={chr(64 + c)}61-{chr(64 + c)}64", "", "mn")
        h.poner(68, c, f"={chr(64 + c)}55", "", "pct")
        k._teclear(h, 70, c, [("Ingresos", "ingresos", dato("ingresos", a)), ("Coste de ventas",
                                                                              "coste_ventas", dato("coste_ventas", a), -1),
                              ("EBIT", "resultado_operativo", dato("resultado_operativo", a), -1)], periodo=f"FY{a}")
        h.poner(71, c, f"={chr(64 + c)}56", "", "pct")
    for c in proy:
        L = chr(64 + c)
        h.poner(64, c, f'=IF(CASE=2,"--",{L}61-{L}67)', "", "mn")
        h.poner(65, c, f'=IF(CASE=2,"--",{L}64/{L}61)', "", "pct")
        h.poner(67, c, f'=IF(CASE=2,"--",{L}68*{L}61)', "", "mn")
        h.poner(68, c, f'=IF(CASE=2,"--",{L}55)', "", "pct")
        h.poner(70, c, f'=IF(CASE=2,"--",{L}71*{L}61)', "", "mn")
        h.poner(71, c, f'=IF(CASE=2,"--",{L}56)', "", "pct")
    h.poner(73, 2, "EBIT", "total")
    h.poner(74, 2, "% of sales")
    for c in hist:
        h.poner(73, c, f"={chr(64 + c)}67-{chr(64 + c)}70", "total", "mn")
    for c in proy:
        L = chr(64 + c)
        h.poner(73, c, f"=CHOOSE(CASE,{L}76,{L}79)", "total", "mn")
        h.poner(76, c, f"={L}61*{L}55-{L}61*{L}56", "", "mn")  # E21: sin autorreferencia
        h.poner(77, c, f"={L}76/{L}61", "", "pct")
        h.poner(79, c, f"={om}{chr(64 + c + 1)}{k.om['ebit']}", "", "mn")
        h.poner(80, c, f"={L}79/{L}61", "", "pct")
    for c in range(4, 12):
        h.poner(74, c, f"={chr(64 + c)}73/{chr(64 + c)}61", "", "pct")
    h.poner(76, 2, "EBIT - Conservative")
    h.poner(77, 2, "% of sales")
    h.poner(79, 2, "EBIT - Management (Operating Model)")
    h.poner(80, 2, "% of sales")
    h.poner(82, 2, "Interest Expense", "etiqueta")
    h.poner(83, 2, "Interest Income", "etiqueta")
    for c in hist:
        valor(82, c, "gasto_intereses")
        valor(83, c, "ingresos_intereses")
    for c in proy:  # E28: la amortización de las comisiones de financiación es gasto financiero (no caja)
        h.poner(82, c, f"={chr(64 + c)}285+{chr(64 + c)}254", "", "mn")
        h.poner(83, c, f"={chr(64 + c)}264", "", "mn")
    h.poner(85, 2, "EBT", "etiqueta")
    h.poner(86, 2, "% of sales")
    h.poner(88, 2, "Taxes", "etiqueta")
    h.poner(89, 2, "% tax rate")
    h.poner(91, 2, "Net Income", "total")
    h.poner(92, 2, "% of sales")
    for c in hist:
        valor(88, c, "impuestos")
    for c in range(4, 12):
        L = chr(64 + c)
        h.poner(85, c, f"={L}73-{L}82+{L}83", "", "mn")
        h.poner(86, c, f"={L}85/{L}61", "", "pct")
        if c in proy:
            h.poner(88, c, f"={L}85*{L}89", "", "mn")
        h.poner(89, c, f"={L}57", "", "pct")
        h.poner(91, c, f"={L}85-{L}88", "total", "mn")
        h.poner(92, c, f"={L}91/{L}61", "", "pct")
    h.poner(94, 2, "EBITDA Reconciliation", "cabecera")
    for f, t in ((95, "EBIT"), (96, "D&A"), (97, "Adjustments"), (98, "EBITDA"), (99, "% of sales")):
        h.poner(f, 2, t, "total" if f == 98 else "")
    for c in hist:
        L = chr(64 + c)
        h.poner(95, c, f"={L}73", "", "mn")
        h.poner(96, c, f"={L}158", "", "mn")
        h.poner(97, c, 0.0, "entrada", "mn", "Ajustes no recurrentes del analista (la plantilla sumaba 3,5 en 2009)")
        h.poner(98, c, f"={L}95+{L}96+{L}97", "total", "mn")
        h.poner(99, c, f"={L}98/{L}61", "", "pct")
    h.poner(101, 2, "EBITDA", "total")
    h.poner(102, 2, "% of sales")
    h.poner(104, 2, "EBITDA - Conservative")
    h.poner(105, 2, "% of sales")
    h.poner(107, 2, "EBITDA - Management (Operating Model)")
    h.poner(108, 2, "% of sales")
    for c in hist:
        h.poner(101, c, f"={chr(64 + c)}98", "total", "mn")
        h.poner(102, c, f"={chr(64 + c)}99", "", "pct")
    for c in proy:
        L = chr(64 + c)
        h.poner(101, c, f"=CHOOSE(CASE,{L}104,{L}107)", "total", "mn")
        h.poner(102, c, f"={L}101/{L}61", "", "pct")
        h.poner(104, c, f"={L}76+{L}161", "", "mn")
        h.poner(105, c, f"={L}104/{L}61", "", "pct")
        h.poner(107, c, f"={L}79+{om}{chr(64 + c + 1)}{k.om['da']}", "", "mn")
        h.poner(108, c, f"={L}107/{L}61", "", "pct")
    # Capital circulante
    anios_fila(110)
    h.poner(110, 2, "Working Capital", "seccion")
    circulante = ((112, "Accounts Receivable", "promedio"), (115, "Inventories and Other Current Assets", "promedio"),
                  (118, "Accounts Payable", "ultimo"), (121, "Other Current Liabilities", "promedio"),
                  (124, "Other Accrued Liabilities", "ultimo"))
    for f, t, regla in circulante:
        h.poner(f, 2, t, "etiqueta")
        h.poner(f + 1, 2, "% of sales")
        for c in hist:
            a = hist[c]
            if f == 112:
                valor(f, c, "clientes")
            elif f == 115:
                k._teclear(h, f, c, [("Activo corriente", "activo_corriente", dato("activo_corriente", a)), ("Caja",
                                                                                                             "caja", dato("caja", a), -1),
                                     ("Inversiones a c/p", "inversiones_cp", dato("inversiones_cp", a), -1),
                                     ("Clientes", "clientes", dato("clientes", a), -1)], periodo=f"FY{a}")
            elif f == 118:
                valor(f, c, "proveedores")
            elif f == 121:
                k._teclear(h, f, c, [("Pasivo corriente", "pasivo_corriente", dato("pasivo_corriente", a)),
                                     ("Deuda a c/p", "deuda_cp", dato("deuda_cp", a), -1),
                                     ("Proveedores", "proveedores", dato("proveedores", a), -1)], periodo=f"FY{a}")
            else:
                h.poner(f, c, 0.0, "entrada", "mn", "Incluidos en otros pasivos corrientes (la SEC no los separa de forma uniforme)")
            h.poner(f + 1, c, f"={chr(64 + c)}{f}/{chr(64 + c)}61", "", "pct")
        h.poner(f + 1, 7, f"=AVERAGE(D{f + 1}:F{f + 1})" if regla == "promedio" else f"=F{f + 1}", "", "pct")
        for c in range(8, 12):
            h.poner(f + 1, c, f"={chr(63 + c)}{f + 1}", "", "pct")
        for c in proy:
            h.poner(f, c, f"={chr(64 + c)}{f + 1}*{chr(64 + c)}61", "", "mn")
    h.poner(119, 13, "La plantilla anota que debería ir sobre el coste de ventas (E11): no aplicable en el caso de la dirección")
    h.poner(127, 2, "Net Working Capital", "total")
    h.poner(128, 2, "% of sales")
    h.poner(130, 2, "Change in Net Working Capital")
    h.poner(131, 2, "% of sales")
    h.poner(130, 4, "--")
    h.poner(131, 4, "--")
    for c in range(4, 12):
        L = chr(64 + c)
        h.poner(127, c, f"={L}112+{L}115-{L}118-{L}121-{L}124", "total", "mn")
        h.poner(128, c, f"={L}127/{L}61", "", "pct")
        if c > 4:
            h.poner(130, c, f"={L}127-{chr(63 + c)}127", "", "mn")
            h.poner(131, c, f"={L}130/{L}61", "", "pct")
    # Activos a largo plazo
    anios_fila(133)
    h.poner(133, 2, "Long Lived Assets", "seccion")
    h.poner(135, 2, "Capital Expenditures", "etiqueta")
    h.poner(136, 2, "% of sales")
    h.poner(138, 2, "Depreciation", "etiqueta")
    h.poner(139, 2, "% of sales")
    h.poner(140, 2, "% of CapEx")
    for c in hist:
        a = hist[c]
        L = chr(64 + c)
        valor(135, c, "capex")
        k._teclear(h, 138, c, [("D&A", "amortizacion", dato("amortizacion", a)),
                               ("Amortización de intangibles", "amortizacion_intangibles", dato("amortizacion_intangibles", a), -1)],
                   periodo=f"FY{a}")
        h.poner(136, c, f"={L}135/{L}61", "", "pct")
        h.poner(139, c, f"={L}138/{L}61", "", "pct")
        h.poner(140, c, f"={L}138/{L}135", "", "pct")
    for f in (136, 139, 140):
        h.poner(f, 7, f"=AVERAGE(D{f}:F{f})", "", "pct")
        for c in range(8, 12):
            h.poner(f, c, f"={chr(63 + c)}{f}", "", "pct")
    for c in proy:
        L = chr(64 + c)
        h.poner(135, c, f"={L}136*{L}61", "", "mn")
        h.poner(138, c, f"={L}140*{L}135", "", "mn")
    h.poner(142, 2, "PP&E", "cabecera")
    for f, t in ((143, "Beginning Balance"), (144, "Capital Expenditures"), (145, "Depreciation"), (146, "Ending Balance")):
        h.poner(f, 2, t)
    previo = est.datos.get("inmovilizado", {}).get(d.ejercicio - 3)
    if previo is not None:
        h.poner(143, 4, previo.valor / 1e6, "entrada", "mn", f"{previo.concepto} · {previo.origen}")
    x = dato("inmovilizado", d.ejercicio - 2)
    if x is not None:
        h.poner(143, 5, x.valor / 1e6, "entrada", "mn", f"{x.concepto} · {x.origen}")
    h.poner(143, 6, "=F146+F145-F144", "", "mn")
    h.poner(146, 4, "=D143+D144-D145", "", "mn")
    valor(146, 5, "inmovilizado")
    valor(146, 6, "inmovilizado")
    for c in range(4, 12):
        L = chr(64 + c)
        h.poner(144, c, f"={L}135", "", "mn")
        # E27: la depreciación del inmovilizado es la del caso elegido (D&A del caso − amortización de intangibles)
        h.poner(145, c, f"={L}138" if c < 7 else f"={L}158-{L}151", "", "mn")
    for c in proy:
        L, P = chr(64 + c), chr(63 + c)
        h.poner(143, c, f"={P}146", "", "mn")
        h.poner(146, c, f"={L}143+{L}144-{L}145", "", "mn")
    h.poner(148, 2, "Intangible Assets", "cabecera")
    for f, t in ((149, "Beginning Balance"), (150, "Purchases / (Impairment)"), (151, "Amortization"), (152, "Ending Balance")):
        h.poner(f, 2, t)
    h.poner(149, 4, "=D152+D151-D150", "", "mn")
    h.poner(150, 4, 0.0, "entrada", "mn")
    for c in (5, 6):
        L, P = chr(64 + c), chr(63 + c)
        h.poner(149, c, f"={P}152", "", "mn")
        h.poner(150, c, f"={L}152+{L}151-{L}149", "", "mn")
    for c in hist:
        valor(151, c, "amortizacion_intangibles")
        valor(152, c, "intangibles")
    for c in proy:
        L, P = chr(64 + c), chr(63 + c)
        h.poner(149, c, f"={P}152", "", "mn")
        h.poner(150, c, 0.0, "entrada", "mn", "E22: sin compras ni deterioros proyectados (la plantilla era circular)")
        h.poner(151, c, f"=MIN({L}149,$F$151)", "", "mn")
        h.poner(152, c, f"={L}149+{L}150-{L}151", "", "mn")
    h.poner(154, 2, "Goodwill and Other Assets", "etiqueta")
    h.poner(156, 2, "Other Liabilities", "etiqueta")
    for c in hist:
        a = hist[c]
        k._teclear(h, 154, c, [("Activo total", "activos", dato("activos", a)), ("Activo corriente",
                                                                                 "activo_corriente", dato("activo_corriente", a), -1),
                               ("Inmovilizado", "inmovilizado", dato("inmovilizado", a), -1),
                               ("Intangibles", "intangibles", dato("intangibles", a), -1)], periodo=f"FY{a}")
        k._teclear(h, 156, c, [("Pasivo total", "pasivos", dato("pasivos", a)), ("Pasivo corriente",
                                                                                 "pasivo_corriente", dato("pasivo_corriente", a), -1),
                               ("Deuda a l/p", "deuda_lp", dato("deuda_lp", a), -1)], periodo=f"FY{a}")
    for c in proy:
        h.poner(154, c, f"={chr(63 + c)}154", "", "mn")
        h.poner(156, c, f"={chr(63 + c)}156", "", "mn")
    for f, t in ((158, "D&A"), (159, "% of sales"), (161, "D&A - Conservative"), (162, "% of sales"),
                 (164, "D&A - Management (Operating Model)"), (165, "% of sales"), (167, "CapEx"), (168, "% of sales")):
        h.poner(f, 2, t)
    for c in hist:
        L = chr(64 + c)
        h.poner(158, c, f"={L}138+{L}151", "", "mn")
    for c in proy:
        L = chr(64 + c)
        h.poner(158, c, f"=CHOOSE(CASE,{L}161,{L}164)", "", "mn")
        h.poner(161, c, f"={L}138+{L}151", "", "mn")
        h.poner(162, c, f"={L}161/{L}61", "", "pct")
        h.poner(164, c, f"={L}107-{L}79", "", "mn")
        h.poner(165, c, f"={L}164/{L}61", "", "pct")
    for c in range(4, 12):
        L = chr(64 + c)
        h.poner(159, c, f"={L}158/{L}61", "", "pct")
        h.poner(167, c, f"={L}135", "", "mn")
        h.poner(168, c, f"={L}136", "", "pct")
    # Flujo de caja
    anios_fila(170)
    h.poner(170, 2, "Cash Flow Statement", "seccion")
    filas_cf = [(172, "Net Income", "{L}91"), (173, "Depreciation and Amortization", "{L}158"), (174, "Changes in Working Capital",
                                                                                                 "{L}130"),
                (175, "Other Long-Term Assets and Liabilities", "({P}154-{L}154)+({L}156-{P}156)"),
                (176, "PIK Interest and Financing Fee Amortization", "{L}247+{L}254"),
                (177, "Cash From Operations", "{L}172+{L}173-{L}174+{L}175+{L}176"),  # E23: + otros activos y pasivos a largo
                (179, "Capital Expenditures", "{L}167"), (180, "Purchases of Intangible Assets", "{L}150"),
                (181, "Cash From Investing", "{L}179+{L}180"), (183, "Mandatory Debt Repayments", "{L}219+{L}228+{L}237+{L}246"),
                (184, "Pre-Revolver Cash Flow", "{L}177-{L}181-{L}183"), (186, "Revolver", "{L}212"),
                (187, "Post-Revolver Cash Flow", "{L}184+{L}186"), (190, "Term loan A", "{L}220"), (191, "Term loan B", "{L}229"),
                (192, "Senior notes", "{L}238"), (194, "Net Change in Cash", "{L}187-{L}190-{L}191-{L}192")]
    h.poner(189, 2, "Discretionary Payments", "cabecera")
    for f, t, patron in filas_cf:
        h.poner(f, 2, t, "total" if f in (177, 184, 194) else "")
        for c in proy:
            h.poner(f, c, "=" + patron.format(L=chr(64 + c), P=chr(63 + c)), "total" if f in (177, 184, 194) else "", "mn")
    # Deuda
    h.poner(196, 2, "Debt Schedule", "seccion")
    anios_fila(198)
    h.poner(198, 2, "Debt Paydown", "cabecera")
    h.poner(199, 2, "Cash", "cabecera")
    for f, t in ((200, "Beginning Balance"), (201, "Inflow / (Outflow)"), (202, "Ending Balance")):
        h.poner(f, 2, t)
    h.poner(200, 7, "=E23", "", "mn")
    h.celdas[(200, 7)].comentario = "Caja tras la operación (la mínima)"
    h.poner(202, 6, "=E22", "", "mn")
    for c in proy:
        L, P = chr(64 + c), chr(63 + c)
        if c > 7:
            h.poner(200, c, f"={P}202", "", "mn")
        h.poner(201, c, f"={L}194", "", "mn")
        h.poner(202, c, f"={L}200+{L}201", "", "mn")
    h.poner(204, 2, "=B28", "cabecera")
    for f, t, patron in ((205, "Beginning Cash Balance", "{L}200"), (206, "Minimum Cash", "$E$23"), (207, "Beginning Excess Cash",
                                                                                                     "{L}205-{L}206"),
                         (208, "Free Cash Flow Generated", "{L}184"), (209, "Cash Available to Paydown / (Draw From) Revolver",
                                                                       "{L}207+{L}208"),
                         (211, "Beginning Balance", "{P}213"), (212, "Increase / (Decrease)", "-MIN({L}209,{L}211)"),
                         (213, "Ending Balance", "{L}211+{L}212")):
        h.poner(f, 2, t)
        for c in proy:
            h.poner(f, c, "=" + patron.format(L=chr(64 + c), P=chr(63 + c)), "", "mn")
    h.poner(213, 6, "=D40", "", "mn")
    h.poner(214, 2, "Maximum Availability")
    h.poner(214, 7, "=$M$214*$E$20", "", "mn")
    h.poner(214, 13, REVOLVER_MAXIMO, "entrada", "x", "Disponibilidad del revolver en veces EBITDA de la plantilla (150 / 444,6)")
    for c in range(8, 12):
        h.poner(214, c, f"={chr(63 + c)}214", "", "mn")
    h.poner(215, 2, "CHECK")
    for c in proy:
        L = chr(64 + c)
        h.poner(215, c, f'=IF({L}213<{L}214,"OK","OVERDRAWN")')
    bloques = ((217, 29, 224, "{L}209+{L}212"), (226, 30, 233, "{L}209+{L}212-{L}220"), (235, 31, 242, "{L}209+{L}212-{L}220-{L}229"))
    for (f0, tramo, f_barrido, disponible), barrido in zip(bloques, BARRIDO, strict=True):
        h.poner(f0, 2, f"=B{tramo}", "cabecera")
        for f, t in ((f0 + 1, "Beginning Balance"), (f0 + 2, "Mandatory Paydown"), (f0 + 3, "Paydown From Excess Cash Flows"),
                     (f0 + 4, "Ending Balance"), (f0 + 6, "Mandatory Paydown (% of Initial Amount)"), (f_barrido, "Cash Sweep")):
            h.poner(f, 2, t)
        h.poner(f0 + 4, 6, f"=E{tramo}", "", "mn")
        h.poner(f_barrido, 5, "% of available")
        h.poner(f_barrido, 6, barrido, "entrada", "pct", "Barrido de caja de la plantilla")
        for c in proy:
            L, P = chr(64 + c), chr(63 + c)
            h.poner(f0 + 1, c, f"={P}{f0 + 4}", "", "mn")
            h.poner(f0 + 2, c, f"=MIN({L}{f0 + 1}*{L}{f0 + 6},{L}{f0 + 1})", "", "mn")
            h.poner(f0 + 3, c, f"=MIN({L}{f_barrido},{L}{f0 + 1}-{L}{f0 + 2})", "", "mn")
            h.poner(f0 + 4, c, f"={L}{f0 + 1}-{L}{f0 + 2}-{L}{f0 + 3}", "", "mn")
            h.poner(f0 + 6, c, 0.0, "entrada", "pct")
            h.poner(f_barrido, c, f"=$F${f_barrido}*({disponible.format(L=L)})", "", "mn")
    h.poner(244, 2, "=B32", "cabecera")
    for f, t in ((245, "Beginning Balance"), (246, "Mandatory Paydown"), (247, "PIK Interest"), (248, "Ending Balance"),
                 (250, "Mandatory Paydown (% of Initial Amount)")):
        h.poner(f, 2, t)
    h.poner(248, 6, "=E32", "", "mn")
    for c in proy:
        L, P = chr(64 + c), chr(63 + c)
        h.poner(245, c, f"={P}248", "", "mn")
        h.poner(246, c, f"=MIN({L}245*{L}250,{L}245)", "", "mn")
        h.poner(247, c, f"=IF(PIK=2,$L$32*({L}245-{L}246),0)", "", "mn")
        h.poner(248, c, f"={L}245-{L}246+{L}247", "", "mn")
        h.poner(250, c, 0.0, "entrada", "pct")
    h.poner(252, 2, "Capitalized Financing Fees", "cabecera")
    for f, t in ((253, "Beginning Balance"), (254, "Amortization"), (255, "Ending Balance")):
        h.poner(f, 2, t)
    h.poner(255, 6, "=I34", "", "mn")
    for c in proy:
        L, P = chr(64 + c), chr(63 + c)
        h.poner(253, c, f"={P}255", "", "mn")
        h.poner(254, c, f"=MIN($K$34,{L}253)", "", "mn")
        h.poner(255, c, f"={L}253-{L}254", "", "mn")
    h.poner(257, 2, "Total Debt", "cabecera")
    for f, t in ((258, "Beginning Balance"), (259, "Paydown"), (260, "Ending Balance"), (261, "CHECK")):
        h.poner(f, 2, t)
    for c in range(6, 12):
        L = chr(64 + c)
        h.poner(260, c, f"={L}213+{L}221+{L}230+{L}239+{L}248", "", "mn")
    for c in proy:
        L = chr(64 + c)
        h.poner(258, c, f"={L}211+{L}218+{L}227+{L}236+{L}245", "", "mn")
        h.poner(259, c, f"=-{L}212+{L}219+{L}220+{L}228+{L}229+{L}237+{L}238+{L}246-{L}247", "", "mn")  # E24
        h.poner(261, c, f"=ABS({L}258-{L}259-{L}260)<=0.00001*MAX(1,{L}258)")  # E30: con tolerancia (cálculo iterativo)
    # Intereses (circularidad: saldos medios)
    anios_fila(263)
    h.poner(263, 2, "Interest", "seccion")
    h.poner(264, 2, "Cash")
    h.poner(265, 2, "Interest income rate")
    h.poner(264, 6, "=F83", "", "mn")
    h.poner(265, 6, '=IF(ISERROR(F264/F202),0,F264/F202)', "", "pct")
    for c in proy:
        L, P = chr(64 + c), chr(63 + c)
        h.poner(264, c, f'=IF(CIRC="OFF",AVERAGE({L}200,{L}202)*{L}265,0)', "", "mn")
        h.poner(265, c, f"={P}265", "", "pct")
    for f, tramo, inicio, fin in ((267, 28, 211, 213), (270, 29, 218, 221), (273, 30, 227, 230), (276, 31, 236, 239)):
        h.poner(f, 2, f"=B{tramo}")
        h.poner(f + 1, 2, "Interest rate")
        for c in proy:
            L = chr(64 + c)
            h.poner(f, c, f'=IF(CIRC="OFF",{L}{f + 1}*AVERAGE({L}{inicio},{L}{fin}),0)', "", "mn")
            h.poner(f + 1, c, f"=$G${tramo}", "", "pct")
    h.poner(279, 2, "=B32")
    h.poner(280, 2, "Cash Interest rate")
    h.poner(282, 2, "=B32")
    h.poner(283, 2, "PIK Interest rate")
    for c in proy:
        L = chr(64 + c)
        h.poner(279, c, f'=IF(PIK=1,IF(CIRC="OFF",{L}280*AVERAGE({L}245,{L}248),0),0)', "", "mn")
        h.poner(280, c, "=$G$32", "", "pct")
        h.poner(282, c, f"={L}247", "", "mn")
        h.poner(283, c, "=$L$32", "", "pct")  # E25
    h.poner(285, 2, "Total interest expense", "total")
    h.poner(286, 2, "Blended interest rate")
    for c in proy:
        L = chr(64 + c)
        h.poner(285, c, f"={L}267+{L}270+{L}273+{L}276+{L}279+{L}282", "total", "mn")
        h.poner(286, c, f"={L}285/AVERAGE({L}260,{L}258)", "", "pct")
    # TIR
    h.poner(288, 2, "IRR", "seccion")
    for f, t, formula, formato in ((290, "LTM EBITDA at Exit", "=K101", "mn"), (291, "Exit Multiple", "=E24", "x"),
                                   (292, "Enterprise Value", "=K290*K291", "mn"), (293, "Net Debt", "=K260-K202", "mn"),
                                   (294, "Sponsor Equity Value", "=K292-K293", "mn"), (296, "Sponsor Equity at Entry", "=D46", "mn"),
                                   (298, "MOIC", "=K294/K296", "x"), (299, "IRR", "=K298^(1/COUNT(G52:K52))-1", "pct")):  # E10
        h.poner(f, 2, t, "total" if f == 299 else "")
        h.poner(f, 11, formula, "total" if f == 299 else "", formato)
    # Balance pro forma
    h.poner(301, 2, "Pro Forma Balance Sheet Adjustments", "seccion")
    h.poner(301, 7, d.ejercicio, "cabecera", "anio")
    for c, t in ((8, "Uses of funds"), (9, "Sources of funds"), (10, "Accounting"), (11, "Pro Forma")):
        h.poner(301, c, t, "cabecera")
    ajustes = [(303, "Cash", "=F202", {8: "=H314+H319-H307", 9: "=I314+I319+I318"}),
               (304, "Accounts Receivable", "=F112", {}), (305, "Inventories and Other Current Assets", "=F115", {}),
               (306, "PP&E", "=F146", {}), (307, "Intangible Assets", "=F152", {8: "=I43"}),
               (308, "Goodwill and Other Assets", "=F154", {10: "=K16-G319"}),
               (311, "Accounts Payable", "=F118", {}), (312, "Other Current Liabilities", "=F121", {}),
               (313, "Other Accrued Liabilities", "=F124", {}), (314, "Debt", "=E21", {8: "=-I41", 9: "=SUM(D40:D44)"}),
               (315, "Other liabilities", "=F156", {})]
    for f, t, inicial, extra in ajustes:
        h.poner(f, 2, t)
        h.poner(f, 7, inicial, "", "mn")
        for c, formula in extra.items():
            h.poner(f, c, formula, "", "mn")
        h.poner(f, 11, f"=SUM(G{f}:J{f})", "", "mn")
    h.poner(309, 2, "Total Assets", "total")
    h.poner(316, 2, "Total Liabilities", "total")
    for c in range(7, 11):
        L = chr(64 + c)
        h.poner(309, c, f"=SUM({L}303:{L}308)", "total", "mn")
        h.poner(316, c, f"=SUM({L}311:{L}315)", "total", "mn")
    h.poner(309, 11, "=SUM(G309:J309)", "total", "mn")
    h.poner(316, 11, "=SUM(G316:J316)", "total", "mn")
    h.poner(318, 2, "Preferred Stock")
    k._teclear(h, 318, 7, [("Preferentes", "preferentes", df("preferentes"))], periodo=fy)
    h.poner(318, 11, "=SUM(G318:J318)", "", "mn")
    h.poner(319, 2, "Equity (incl. minority interest and temporary equity)")
    k._teclear(h, 319, 7, [("Patrimonio", "patrimonio", df("patrimonio")), ("Preferentes", "preferentes", df("preferentes"), -1),
                           ("Minoritarios", "minoritarios", df("minoritarios")),
                           ("Patrimonio temporal", "patrimonio_temporal", df("patrimonio_temporal"))], periodo=fy)
    h.poner(319, 8, "=-(I40+I42+I45)", "", "mn")  # E29: otros usos, coste de la operación (como las comisiones)
    h.poner(319, 9, "=D46", "", "mn")
    h.poner(319, 10, "=J308", "", "mn")
    h.poner(319, 11, "=SUM(G319:J319)", "", "mn")
    h.poner(320, 2, "Total Equity", "total")
    h.poner(322, 2, "Check")
    for c in range(7, 12):
        L = chr(64 + c)
        h.poner(320, c, f"={L}318+{L}319", "total", "mn")
    h.poner(322, 7, "=G309-G316-G320", "", "mn")
    h.poner(322, 11, "=K309-K316-K320", "", "mn")
    h.poner(324, 2, "Pro Forma Balance Sheet", "seccion")
    h.poner(324, 6, d.ejercicio, "cabecera", "anio")
    for c in proy:
        h.poner(324, c, f"={chr(63 + c)}324+1", "cabecera", "anio")
    proforma = [(325, "Cash", 303, "{L}202"), (326, "Accounts Receivable", 304, "{L}112"),
                (327, "Inventories and Other Current Assets", 305, "{L}115"), (328, "PP&E", 306, "{L}146"),
                (329, "Intangible Assets", 307, "{L}152+{L}255"), (330, "Goodwill and Other Assets", 308, "{L}154+$J$308"),
                (333, "Accounts Payable", 311, "{L}118"), (334, "Other Current Liabilities", 312, "{L}121"),
                (335, "Other Accrued Liabilities", 313, "{L}124"), (336, "Debt", 314, "{L}260"), (337, "Other liabilities", 315, "{L}156")]
    for f, t, origen, patron in proforma:
        h.poner(f, 2, t)
        h.poner(f, 6, f"=K{origen}", "", "mn")
        for c in proy:
            h.poner(f, c, "=" + patron.format(L=chr(64 + c)), "", "mn")
    h.poner(331, 2, "Total Assets", "total")
    h.poner(338, 2, "Total Liabilities", "total")
    h.poner(340, 2, "Preferred Stock")
    h.poner(341, 2, "Equity")
    h.poner(342, 2, "Total Equity", "total")
    h.poner(344, 2, "Check")
    h.poner(340, 6, "=K318", "", "mn")
    h.poner(341, 6, "=K319", "", "mn")
    for c in range(6, 12):
        L = chr(64 + c)
        h.poner(331, c, f"=SUM({L}325:{L}330)", "total", "mn")
        h.poner(338, c, f"=SUM({L}333:{L}337)", "total", "mn")
        if c > 6:  # E31: las preferentes que la operación no amortiza siguen en el balance (la plantilla no las tenía)
            h.poner(340, c, f"={chr(63 + c)}340", "", "mn")
        h.poner(342, c, f"=SUM({L}340:{L}341)", "total", "mn")
        h.poner(344, c, f"={L}331-{L}338-{L}342", "", "mn")
    h.poner(346, 2, "Equity", "cabecera")
    for f, t in ((347, "Beginning Balance"), (348, "Net Income"), (349, "Dividends"), (350, "Ending Balance")):
        h.poner(f, 2, t)
    for c in proy:
        L, P = chr(64 + c), chr(63 + c)
        h.poner(341, c, f"={L}350", "", "mn")
        h.poner(347, c, f"={P}341", "", "mn")
        h.poner(348, c, f"={L}91", "", "mn")
        h.poner(350, c, f"={L}347+{L}348-{L}349", "", "mn")
    _acciones_lbo(k)
    k.celdas.update(lbo_tir=("LBO", 299, 11), lbo_moic=("LBO", 298, 11), lbo_precio=("LBO", 13, 11), lbo_ev=("LBO", 22, 11),
                    lbo_multiplo=("LBO", 24, 11), lbo_revolver=("LBO", 7, 11))
    k.controles_extra = [("LBO: el revolver no se excede", '=AND(LBO!G215="OK",LBO!H215="OK",LBO!I215="OK",LBO!J215="OK",LBO!K215="OK")'),
                         ("LBO: la deuda cuadra",  # tolerancia relativa: el cálculo iterativo de los intereses para con cambios < 0,001
                          "=AND(" + ",".join(f"ABS(LBO!{L}258-LBO!{L}259-LBO!{L}260)<=0.00001*MAX(1,LBO!{L}258)" for L in "GHIJK") + ")"),
                         ("LBO: balance pro forma cuadrado",
                          "=AND(" + ",".join(f"ABS(LBO!{L}344)<=0.00001*MAX(1,LBO!{L}331)" for L in "FGHIJK") + ")")]


def _acciones_lbo(k) -> None:
    """LBO Shares (plantilla): acciones diluidas al precio de la oferta (método del autocartera)."""
    d = k.d
    est = d.estados
    dato = lambda p: est.datos.get(p, {}).get(d.ejercicio)  # noqa: E731
    h = k.libro.hoja("LBO Shares")
    h.poner(2, 2, "Diluted Share Count Calculation", "titulo")
    h.poner(4, 2, "Fully Diluted Shares", "seccion")
    filas = [(6, "Offer price", "=LBO!K13", "usd"), (8, "In-the-money exercisable options", "=E32", "acc"),
             (9, "Total proceeds ($mm)", "=SUMPRODUCT(D21:D30,E21:E30)", "mn"), (10, "Total shares repurchased (mm)", "=E9/E6", "acc"),
             (11, "Net dilutive options", "=E8-E10", "acc"), (12, "Dilutive impact of shares from other securities (RSU)",
                                                              "=Shares!E12-Shares!E39", "acc"),
             (14, "Settled stock based comp", 0.0, "acc"), (16, "Net diluted shares outstanding", "=E7+E11+E12+E14", "acc")]  # E26
    for f, t, formula, formato in filas:
        h.poner(f, 2, t, "total" if f == 16 else "etiqueta")
        h.poner(f, 5, formula, "entrada" if not isinstance(formula, str) else ("total" if f == 16 else ""), formato)
    h.poner(7, 2, "Basic shares outstanding (latest filing)", "etiqueta")
    h.poner(7, 5, "=Shares!E7", "", "acc")
    h.celdas[(14, 5)].comentario = "La plantilla sumaba la SBC liquidada en la operación de Burger King (48,1 / precio): por defecto 0"
    h.poner(18, 2, "Options outstanding", "seccion")
    for c, t in ((3, "Outstanding"), (4, "Exercise price"), (5, "Dilutive Shares")):
        h.poner(20, c, t, "cabecera")
    for i, f in enumerate(range(21, 31)):
        h.poner(f, 2, i + 1 if i == 0 else f"=B{f - 1}+1")
        h.poner(f, 5, f"=IF(D{f}<$E$6,C{f})", "", "acc")
    opciones, precio = dato("opciones_ejercitables"), dato("precio_ejercicio_opciones")
    if opciones and precio:
        h.poner(21, 3, "=Shares!C19", "", "acc")
        h.poner(21, 4, "=Shares!D19", "", "usd")
    h.poner(32, 2, "Total", "total")
    h.poner(32, 5, "=SUM(E21:E30)", "total", "acc")


def hoja_acrecion(k, ad: EntradasAD) -> None:
    """Acreción-dilución (plantilla `accretion-dilution`, *Answer Key*): la empresa del informe compra a `ad.objetivo`."""
    d = k.d
    h = k.libro.hoja("Acreción-dilución")
    h.poner(2, 2, "Accretion / Dilution Model", "titulo")
    h.poner(4, 2, "Assumptions", "seccion")
    h.poner(6, 2, f"Acquirer: {d.empresa} ({d.ticker})", "cabecera")
    h.poner(6, 8, f"Target: {ad.objetivo}", "cabecera")
    entradas = [(7, 2, "Share price", 6, "=Entradas!C7", "usd"), (8, 2, "Diluted shares outstanding", 6, "=Shares!E14", "acc"),
                (9, 2, "Forward EPS", 6, ad.bpa_comprador if ad.bpa_comprador is not None else 0.0, "usd"),
                (10, 2, "Shares issued", 6, "=L11/F7*F15", "acc"), (12, 2, "Accretive / (Dilutive)", 6, "=I58", "usd"),
                (7, 8, "Share price", 12, ad.precio, "usd"), (8, 8, "% Offer premium", 12, ad.prima, "pct"),
                (9, 8, "Offer price", 12, "=L7*(1+L8)", "usd"), (10, 8, "Diluted shares outstanding", 12, ad.acciones, "acc"),
                (11, 8, "Purchase price", 12, "=L9*L10", "mn"), (12, 8, "Forward EPS", 12, ad.bpa, "usd")]
    for f, ce, t, cv, v, formato in entradas:
        h.poner(f, ce, t, "etiqueta")
        h.poner(f, cv, v, "entrada" if not isinstance(v, str) else "", formato)
    h.celdas[(9, 6)].comentario = "BPA de los próximos doce meses de la proyección del informe · Revisar"
    h.poner(14, 2, "Consideration", "cabecera")
    h.poner(14, 8, "Financials", "cabecera")
    for f, ce, t, cv, v, formato in ((15, 2, "% Stock", 6, ad.acciones_pct, "pct"), (16, 2, "% Debt", 6, ad.deuda_pct, "pct"),
                                     (17, 2, "% Cash", 6, "=1-SUM(F15:F16)", "pct"), (19, 2, "Debt", 6, None, None),
                                     (20, 2, "Term", 6, ad.plazo, "anio"), (21, 2, "Interest rate", 6, ad.tipo, "pct"),
                                     (22, 2, "Annual financing fee amortization", 6, "=K31/F20", "mn"),
                                     (15, 8, "Tax rate", 12, ad.tipo_impositivo, "pct"), (16, 8, "Synergies", 12, ad.sinergias, "mn"),
                                     (17, 8, "Interest on cash", 12, ad.interes_caja, "pct"), (19, 8, "Asset Write Up", 12, None, None),
                                     (20, 8, "Book value of target assets", 12, ad.valor_contable, "mn"),
                                     (21, 8, "Fair market value of target assets", 12, ad.valor_razonable, "mn"),
                                     (22, 8, "Asset write-up", 12, "=L21-L20", "mn"), (23, 8, "Useful life", 12, ad.vida_util, "anio"),
                                     (24, 8, "Incremental D&A expense", 12, "=L22/L23", "mn")):
        h.poner(f, ce, t, "etiqueta")
        if v is not None:
            h.poner(f, cv, v, "entrada" if not isinstance(v, str) else "", formato)
    h.poner(26, 2, "Sources and Uses", "seccion")
    h.poner(28, 2, "Sources", "cabecera")
    h.poner(28, 8, "Uses", "cabecera")
    for c, t in ((5, "Amount"), (6, "% Capital"), (11, "Amount"), (12, "% Capital")):
        h.poner(29, c, t, "cabecera")
    for f, t, formula in ((30, "Acquirer stock issued", "=F10*F7"), (31, "Net debt", "=F16*L11"), (32, "Cash (purchase price + fees)",
                                                                                                   "=E34-SUM(E30:E31)")):
        h.poner(f, 2, t)
        h.poner(f, 5, formula, "", "mn")
        h.poner(f, 6, f"=E{f}/$E$34", "", "pct")
    for f, t, formula in ((30, "Purchase price", "=L11"), (31, "Financing fees", "=M31*E31"), (32, "Transaction fees", "=M32*K30")):
        h.poner(f, 8, t)
        h.poner(f, 11, formula, "", "mn")
        h.poner(f, 12, f"=K{f}/$K$34", "", "pct")
    h.poner(31, 13, ad.comisiones_financiacion_pct, "entrada", "pct", "Plantilla: 100 sobre 2.083 de deuda nueva")
    h.poner(32, 13, ad.comisiones_operacion_pct, "entrada", "pct", "Plantilla: 50 sobre 6.250 de precio")
    h.poner(34, 2, "Total", "total")
    h.poner(34, 5, "=K34", "total", "mn")
    h.poner(34, 6, "=SUM(F30:F32)", "total", "pct")
    h.poner(34, 8, "Total", "total")
    h.poner(34, 11, "=SUM(K30:K32)", "total", "mn")
    h.poner(34, 12, "=SUM(L30:L32)", "total", "pct")
    h.poner(36, 2, "Accretion / Dilution Model", "seccion")
    for c, t in ((7, "Acquirer"), (8, "Target"), (9, "Pro Forma")):
        h.poner(38, c, t, "cabecera")
    h.poner(40, 2, "Accretion / dilution analysis", "cabecera")
    filas = [(41, "Standalone net income", {7: "=F9*F8", 8: "=L12*L10", 9: "=G41+H41"}),
             (42, "Pre-tax income", {7: "=G41/(1-L15)", 8: "=H41/(1-L15)", 9: "=G42+H42"}),
             (45, "Less: Interest expense from new debt", {9: "=E31*F21"}), (46, "Less: Foregone interest on cash", {9: "=E32*L17"}),
             (47, "Less: Incremental D&A expense", {9: "=L24"}), (48, "Less: Deal fees (one-off: not in recurring EPS)", {9: "=K32"}),
             (49, "Less: Financing fees amortization", {9: "=F22"}), (50, "Plus: Synergies", {9: "=L16"}),
             (51, "Pro forma pretax income - adjusted (recurring)", {9: "=I42-SUM(I45:I47)-I49+I50"}),  # E13
             (53, "Pro forma net income", {9: "=I51*(1-L15)"}), (54, "Pro forma shares", {9: "=F8+F10"}),
             (56, "Pro Forma EPS", {9: "=I53/I54"}), (57, "Acquirer standalone EPS", {9: "=F9"}),
             (58, "Accretion / Dilution per share", {9: "=I56-I57"}), (59, "Accretion / Dilution %", {9: "=I56/I57-1"})]
    h.poner(44, 2, "Pro forma pretax income - unadjusted")
    for f, t, celdas in filas:
        h.poner(f, 2, t, "total" if f in (51, 59) else "")
        for c, formula in celdas.items():
            h.poner(f, c, formula, "total" if f in (51, 59) else "", "pct" if f == 59 else ("usd" if f in (56, 57, 58) else "mn"))
    k.celdas.update(ad_acrecion=("Acreción-dilución", 59, 9), ad_bpa=("Acreción-dilución", 56, 9))
