"""Definiciones del anexo de metodología: la versión legible de las fórmulas de calculo/.

Cada fila resume una fórmula implementada en el módulo indicado (la fórmula exacta y su origen están en
el docstring de ese módulo). tests/test_calculo.py comprueba que cada métrica del informe tiene aquí su
definición, para que el anexo no se desincronice del código.
"""

DEFINICIONES: tuple[tuple[str, str, str], ...] = (
    # (grupo, término, definición)
    ("Datos", "Fuente", "SEC EDGAR: companyfacts (XBRL de todos los 10-K y 10-Q) y XBRL del último 10-K, proxy DEF 14A, "
     "Form 8-K. Cotizaciones e índices: yfinance. Tipo libre de riesgo: FRED (DGS10)."),
    ("Datos", "Normalizador SEC", "Cada partida se lee de una lista exacta de conceptos us-gaap por orden de prioridad, sin "
     "desgloses dimensionales. Nunca se estima un dato que no se declara."),
    ("Datos", "LTM (últimos doce meses)", "Suma de los cuatro últimos trimestres (el cuarto se deriva del anual menos los nueve "
     "meses); balance al cierre del último trimestre; BPA = beneficio neto LTM / acciones diluidas del trimestre."),
    ("Datos", "Control de calidad", "Activo = pasivo + patrimonio (±1 %), beneficio bruto declarado = ingresos − coste, contraste "
     "entre companyfacts y el XBRL del 10-K y partidas obligatorias presentes. Un error bloquea la emisión."),
    ("Datos", "Trimestres", "Trimestres discretos de los 10-Q; el cuarto = anual − nueve meses. BPA declarado del trimestre "
     "(el del cuarto, derivado). Variación frente al mismo trimestre del año anterior."),
    ("Datos", "Segmentos y geografía", "Desgloses del XBRL de los 10-K (segmento, producto o servicio y geografía). Solo se "
     "publica un ejercicio si los miembros declarados por la empresa suman los ingresos consolidados (±1 %); los "
     "subtotales no se cuentan dos veces. LTM por segmento provisional: último ejercicio + acumulado del año − acumulado del "
     "año anterior (10-Q), solo si cuadra con los ingresos LTM."),
    ("Datos", "Concentración de clientes", "Porcentajes que la empresa declara (ConcentrationRiskPercentage1), sobre ingresos o "
     "cuentas a cobrar; sin proveedores ni residuos («otros clientes»)."),
    ("Márgenes", "EBITDA", "Resultado operativo (EBIT) declarado + amortizaciones del estado de flujos."),
    ("Márgenes", "Margen bruto, EBITDA, operativo y neto", "Cada partida sobre los ingresos."),
    ("Caja", "FCF", "Flujo de caja operativo − capex."),
    ("Caja", "FCF tras SBC", "FCF − remuneración en acciones (se trata como coste). Base de P/FCF y de la rentabilidad FCF."),
    ("Caja", "Conversión de FCF", "FCF / beneficio neto."),
    ("Caja", "Del EBITDA al FCF", "EBITDA − impuestos pagados − intereses pagados + remuneración en acciones ± circulante y otros "
     "(diferencia hasta el flujo operativo declarado) − capex = FCF."),
    ("Balance", "Vencimientos de deuda", "Principal declarado por año en el 10-K; solo si suma lo mismo (±2 %) que la deuda "
     "declarada."),
    ("Balance", "Deuda financiera neta (DFN)", "Deuda a corto + deuda a largo − caja − inversiones financieras a corto plazo. "
     "Negativa = caja neta."),
    ("Rentabilidad", "ROE", "Beneficio neto / patrimonio neto atribuible."),
    ("Rentabilidad", "ROIC", "EBIT · (1 − tipo efectivo) / (patrimonio + minoritarios + DFN)."),
    ("Rentabilidad", "ROCE", "EBIT / (activo total − pasivo corriente)."),
    ("Rentabilidad", "DuPont", "ROE = margen neto × rotación de activos × apalancamiento (activo / patrimonio); en 5 factores, "
     "carga fiscal (BN / BAI) × carga financiera (BAI / EBIT) × margen operativo × rotación × apalancamiento."),
    ("Múltiplos", "EV", "Capitalización + deuda + minoritarios − caja − inversiones a corto plazo + acciones preferentes + "
     "pasivo neto por pensiones + patrimonio temporal + arrendamientos financieros (si la deuda no los incluye). Los "
     "arrendamientos operativos no se suman: su coste ya está dentro del EBITDA (US GAAP)."),
    ("Múltiplos", "PER, EV/EBITDA, EV/Ventas, P/FCF", "Sobre las cifras LTM y la cotización de la fecha del informe."),
    ("Múltiplos", "Múltiplos históricos", "Precio semanal sin ajustar por dividendos sobre las cifras del último 10-K ya "
     "presentado en cada fecha (sin sesgo de anticipación) y las acciones de ese ejercicio. Mediana y cuartiles de 5 años; "
     "valor implícito = mediana × cifra LTM."),
    ("Valoración", "DCF", "FCFF = EBIT · (1 − t) + D&A − capex − Δcirculante. El EBIT ya resta la remuneración en acciones, "
     "que no se vuelve a sumar. 5 años explícitos + 5 de convergencia lineal hacia g; valor terminal de Gordon sobre un flujo "
     "normalizado (capex de mantenimiento)."),
    ("Valoración", "Proyección de flujo y balance", "Flujo operativo = beneficio + D&A + remuneración en acciones − "
     "Δcirculante; recompras = FCF tras SBC × % del analista; Δcaja = flujo operativo − capex − dividendos − recompras. "
     "La deuda se mantiene; caja + activos operativos netos = deuda + patrimonio + minoritarios cada año."),
    ("Valoración", "WACC", "Ke = Rf + β · prima de riesgo; Kd después de impuestos; pesos a valor de mercado. β semanal a 5 años "
     "frente al S&P 500."),
    ("Valoración", "Escenarios", "Pesimista y optimista: base ∓ 1 desviación típica histórica del crecimiento y del margen "
     "EBITDA. Valor DCF = media ponderada por probabilidades (25/50/25 por defecto). Editables por el analista."),
    ("Valoración", "DCF inverso", "Crecimiento anual de ventas (años explícitos) y tasa de descuento que igualan el valor del "
     "escenario base a la cotización, por bisección."),
    ("Valoración", "Comparables", "Propuesta por código SIC y tamaño (ingresos), revisable por el analista. Múltiplos LTM con el "
     "mismo normalizador; la mediana excluye valores negativos y no significativos (PER > 75x, EV/EBITDA > 50x)."),
    ("Valoración", "Suma de partes", "Resultado operativo de cada segmento declarado × su múltiplo EV/EBIT (del analista o "
     "mediana de sus comparables); los costes no asignados se valoran al mismo múltiplo."),
    ("Valoración", "Precio objetivo", "Media ponderada de los métodos con valor (DCF de escenarios, comparables, múltiplos "
     "históricos, suma de partes) con los pesos del analista, repartidos entre los que tienen valor; el analista puede "
     "fijar el suyo. Recomendación: comprar ≥ +15 %, vender ≤ −10 %."),
    ("Riesgos", "Altman Z", "Probabilidad de insolvencia: Z (empresas con rotación de activos > 0,5) o Z'' (resto). "
     "Zonas: segura, gris, riesgo."),
    ("Riesgos", "Beneish M", "Ocho índices de calidad del beneficio; M > −1,78 indica manipulación probable."),
    ("Riesgos", "Piotroski F", "Nueve pruebas de rentabilidad, apalancamiento y eficiencia (0-9)."),
    ("Competencia", "Cuota de ingresos", "Ingresos LTM de cada empresa / suma de la empresa y sus comparables del analista."),
    ("Competencia", "Estabilidad del margen", "Desviación típica del margen operativo de los 5 últimos ejercicios (pp)."),
    ("Insiders", "Compras y ventas en mercado", "Form 4 de 12 meses, códigos P y S; la retribución en acciones (A, M) y las "
     "retenciones fiscales (F), aparte. Compras agrupadas: 2 o más insiders comprando en 14 días."),
    ("Historial", "Reacción a los resultados", "Cierre de la 5.ª sesión / cierre previo − 1; la 1.ª sesión es la del día del 8-K "
     "(ítem 2.02) si se presentó antes de las 16:00 de Nueva York, o la siguiente."),
    ("Historial", "Alarmas de la SEC", "8-K 4.01 y 4.02, 10-K/A, 10-Q/A, NT 10-K y NT 10-Q de 5 años y frases del 10-K sobre "
     "control interno no eficaz o dudas sobre la continuidad."),
    ("Resumen", "Hechos clave", "4 observaciones por reglas sobre la analítica, ordenadas por relevancia, como mucho una por "
     "tema (crecimiento, rentabilidad, balance, valoración, riesgos)."),
    ("Calendario", "Fechas estimadas", "Resultados y junta: el mismo evento de hace un año + 52 semanas (8-K 2.02 y 5.07); "
     "plazo legal del 10-Q/10-K según la categoría de presentador. Siempre posteriores a la emisión."),
    ("Opciones (externo)", "Ratio put/call y volatilidad", "Volumen (y posiciones abiertas) de puts / calls; volatilidad "
     "implícita ponderada por volumen frente a la realizada a 30 días (√252 × desviación de los rendimientos diarios). "
     "Max pain: precio con el menor pago total a los compradores. Fuente: yfinance, no auditada."),
    ("Cortos (externo)", "Posiciones cortas", "Acciones en corto declaradas (FINRA vía yfinance), sobre el capital flotante y "
     "días para cubrir al volumen medio. Fuente no auditada."),
    ("Posición", "Criterios del fondo", "Umbrales que fija el analista (potencial, PER, EV/EBITDA, deuda neta / EBITDA, ROIC, "
     "crecimiento) frente a las cifras del informe: cumple, no cumple o sin dato."),
    ("Posición", "Stop y tamaño", "Stop = precio × (1 − k × volatilidad diaria × √h), acotado entre la pérdida mínima y máxima "
     "del analista; acciones = capital × riesgo por posición / (precio − stop), sin superar el peso máximo. VaR y CVaR "
     "diarios al 95 % históricos (1 año); prueba histórica: % de ventanas de h sesiones (5 años) en que se tocó el stop."),
    ("Riesgos", "Autonomía de caja", "Solo si el FCF LTM es negativo: meses = (caja + inversiones a corto plazo) / −FCF × 12."),
    ("Riesgos", "Cambios en los factores de riesgo", "Comparación de los títulos del Item 1A con los del informe anual "
     "anterior por similitud de texto: nuevos, eliminados y modificados."),
)
