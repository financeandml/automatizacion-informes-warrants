# Motor de valoración (B1): análisis de las plantillas y plan

Estado: **plan pendiente de aprobación** (2026-10-14). Origen: las plantillas de `Motor de valoración/Ejemplos-plantillas/` (rareliquid; no se publican en el repositorio). Regla del usuario: usarlas **siempre**, sin eliminar funciones ni relaciones entre hojas y sin añadir nada que no esté en ellas; el analista introduce las mínimas variables y descarga el modelo completo para verificarlo número a número.

## 1. Qué contienen las plantillas (análisis del 100 %)

Analizadas las 12 hojas de cálculo (cada celda: entradas, fórmulas en notación relativa, vínculos entre hojas, nombres, validaciones y comentarios) y los 4 PDF.

| Plantilla | Hojas | Qué valora y cómo | Datos de entrada en el original |
|---|---|---|---|
| `simple-dcf` | WACC, IS, CFS, *Empty* (ejercicio), *Answer Key* | DCF de 5 años: ventas × (1 + crecimiento), EBIT = margen × ventas, impuestos = % del EBIT, D&A y capex, ΔNWC = media de 3 años sobre ventas; FCF no apalancado; descuento a fin de año; valor terminal por perpetuidad; EV + caja − deuda; precio por acción y potencial | Estimaciones de consenso de FactSet (IS hasta 2027E; D&A y capex tecleados en rojo); caja, deuda, acciones y WACC tecleados |
| `advanced-dcf-part-1` | DCF, WACC, Shares, Segments, IS, CFS, CapEx | Ventas y EBIT por segmento (Norteamérica, Internacional, AWS); impuestos = media de 5 años; D&A, capex y ΔNWC = media de 5 años sobre ventas; DCF consolidado con **convención de mitad de año y periodo parcial** (`YEARFRAC`); acciones totalmente diluidas | Segmentos con consenso de FactSet hasta 2029E |
| `advanced-dcf-part-2` | + Operating Model, Consolidated, un DCF por segmento | **Suma de partes**: DCF de cada segmento, con D&A, capex y ΔNWC asignados por segmento (datos parciales del 10-K, media de 3 años); el consolidado suma los segmentos | Igual que la parte 1 |
| `advanced-dcf-part-3` | + Comps | Valor terminal combinado **80 % perpetuidad + 20 % múltiplo de salida** (EV/EBITDA mediano de los comparables); controles: valor terminal sobre el EV, múltiplo implícito de la perpetuidad y crecimiento implícito del múltiplo; **WACC con beta desapalancada de los comparables y reapalancada** (Hamada); bonos convertibles; tablas de sensibilidad WACC × crecimiento | Comparables y betas de FactSet tecleados |
| `trading-comps` | *Empty*, *Answer Key*, base de datos | Comparables: crecimiento, márgenes, EV/Ventas, EV/EBITDA y PER; media y mediana; precio implícito con el mínimo, la media, la mediana y el máximo de cada múltiplo × la métrica de la empresa (EV − deuda + caja; PER × BPA) | Base de datos de FactSet con estimaciones (33 empresas) |
| `intermediate-lbo` | LBO | LBO de 5 años: fuentes y usos, modelo operativo por % de ventas, flujo de caja apalancado, deuda (revolver, préstamo, bonos) con amortización por barrido de caja, MOIC y TIR | Enunciado del ejercicio |
| `advanced-lbo-part-2` y `part-3` | LBO, Shares | LBO completo (Burger King 2010): interruptores de **circularidad**, **caso** (conservador / dirección) y **PIK**; 5 tramos de deuda con comisiones y plazos; capital circulante, inmovilizado e intangibles; flujo de caja, barrido de caja, revolver con control de disponibilidad, intereses sobre saldos medios, comisiones capitalizadas; balance *pro forma* con control de cuadre; TIR y MOIC. La parte 3 añade la tesorería mínima, el circulante detallado y el balance proyectado | 10-K y PREM14A de la operación |
| `accretion-dilution` | *Empty*, *Answer Key* | Fusiones: contraprestación en acciones, deuda y caja; fuentes y usos; revalorización de activos y su D&A; sinergias; BPA *pro forma* frente al independiente | Hipotéticos |
| `income-statement`, `balance-sheet`, `cash-flow-statement` (+ PDF) | *Exercise*, *Solution* | Ejercicios contables (puesto de limonada): cuenta de resultados, balance con control activo = pasivo + patrimonio, flujo de caja = explotación + inversión + financiación | Didácticos |
| `trading-comps.pdf` | — | Método en 5 pasos (grupo de comparables, datos, comparación, valor implícito, precio implícito) y temas avanzados: acciones diluidas, caja y deuda correctas, operaciones posteriores al último filing, prima frente a múltiplos históricos. **EV = capitalización + preferentes + deuda + minoritarios − caja** | — |

Las funciones que usan son estándar (`IF`, `ISERROR`, `IFERROR`, `AVERAGE`, `MEDIAN`, `MIN`, `MAX`, `SUM`, `SUMPRODUCT`, `VLOOKUP`, `CHOOSE`, `YEARFRAC`), más tablas de datos de Excel (sensibilidades) y cálculo iterativo (circularidad del LBO).

## 2. Errores encontrados en las plantillas

| # | Plantilla y celda | Error | Corrección propuesta |
|---|---|---|---|
| E1 | Todas (DCF, comparables, LBO) | Cifras tecleadas dentro de fórmulas (`=71178+17914` de caja, `=1233*2/deuda`, deuda neta de los comparables, `380.5` de RSU, BPA 3,55, 48,1 de SBC…): no se actualizan ni se pueden trazar | Cada cifra en su celda de datos, enlazada a la SEC con su *accession* |
| E2 | Todas | Nombres definidos rotos (`CASE`, `CIRC` = `#REF!`) y vínculos a libros externos (`[1]LBO`, `[2]DCF`, `[3]Operating Model`); en la parte 1, `wacc` y `tgr` apuntan a **otro libro**: el DCF depende de un archivo que no existe | Nombres internos y sin vínculos externos |
| E3 | DCF simple y avanzado, comparables | Proyecciones de ventas, EBIT, D&A y capex = **consenso de FactSet** (externo, no auditado y prohibido por la decisión F3) | Entradas del analista (ver §4) |
| E4 | DCF avanzado parte 3, segmentos | El valor terminal por **múltiplo de salida** se descuenta con el periodo de mitad de año; el múltiplo se paga al final del año | Descontarlo a fin de año (la perpetuidad sí sigue la convención de mitad de año) |
| E5 | DCF avanzado | El puente del EV solo usa caja y deuda; su propio PDF define EV = capitalización + preferentes + deuda + minoritarios − caja | Puente del PDF (con las partidas que ya trae nuestro normalizador: R13) |
| E6 | WACC parte 3 | Pesos con deuda bruta y reapalancamiento con deuda neta: incoherente | Misma deuda en los dos (bruta, como los pesos) |
| E7 | WACC | Coste de la deuda = intereses del semestre × 2 / deuda al cierre | Intereses LTM / deuda media |
| E8 | Tablas de sensibilidad | El WACC central está tecleado (0,0833151): no sigue al WACC del modelo | Enlazado al WACC del modelo |
| E9 | Comparables | Mínimo, máximo, media y mediana incluyen múltiplos negativos y empresas no comparables (aerolíneas junto a tecnológicas) | Excluir negativos y no significativos (regla ya aprobada del informe) |
| E10 | LBO | TIR = MOIC^(1/5) − 1 con los 5 años tecleados | Años del modelo |
| E11 | LBO avanzado | Proveedores proyectados sobre ventas; la propia plantilla anota que deben ir sobre el coste de ventas | Sobre el coste de ventas |
| E12 | LBO | El interruptor de circularidad usa «OFF» para activar el cálculo circular | Etiqueta coherente (sin cambiar la lógica) y cálculo iterativo activado en el libro |
| E13 | Acreción / dilución | Resta las comisiones de la operación (únicas) del beneficio recurrente *pro forma* | BPA recurrente sin comisiones; las comisiones, en fuentes y usos |
| E14 | DCF simple | Descuento a fin de año sin periodo parcial, incoherente con el DCF avanzado | Convención del DCF avanzado (mitad de año y periodo parcial) |
| E15 | DCF avanzado | Crecimientos con «--» (texto) en filas numéricas | Se mantiene (es su forma de marcar «sin dato»); las medias ya lo ignoran |
| E16 | Ejercicio del flujo de caja | Texto y celdas que no coinciden (100 frente a −200 de valores negociables) | Solo se usan como reglas de control |

## 3. Diseño del motor

**Un único libro por empresa**, «Modelo de valoración», generado por código con las fórmulas vivas (openpyxl, MIT) y la misma estructura, filas, fórmulas y relaciones entre hojas que las plantillas, con la marca de Warrants & Co.:

| Hoja | De qué plantilla sale | Qué cambia |
|---|---|---|
| Portada e índice | Cover | Índice de hojas, interruptores (escenario, circularidad, módulos activos) |
| Entradas | Celdas azules de todas | Solo las entradas del analista (§4), con su valor por defecto y la marca «Revisar» |
| IS, CFS, BS, Segments, CapEx | Hojas de datos de FactSet | Las mismas filas, rellenadas con el normalizador SEC (5 ejercicios + LTM) y su *accession* |
| Operating Model | DCF avanzado (partes 2 y 3) | Igual; las proyecciones de ventas y EBIT, desde Entradas en lugar del consenso |
| DCF de cada segmento y Consolidated | DCF avanzado parte 3 | Igual; tantos DCF como segmentos validados (con uno solo, el DCF consolidado de la parte 1) |
| WACC y Shares | DCF avanzado parte 3 | Igual, con betas y deuda de los comparables calculadas (no tecleadas) y opciones, RSU y convertibles del XBRL |
| Comps | Trading Comps + Comps de la parte 3 | Base de datos con nuestro normalizador; prima frente a múltiplos históricos (sus columnas AH-AP) |
| LBO | LBO avanzado parte 3 | Opcional: TIR de un comprador financiero a la cotización + prima |
| Acreción / dilución | Accretion/Dilution | Opcional, para una operación corporativa |
| Síntesis | Tabla de valor implícito de los comparables y salidas de cada método | Precio objetivo y gráfico de rangos del informe |
| Controles | Checks de las plantillas (balance, revolver, deuda) | + controles de coherencia (§5) |

**Dos cálculos independientes que tienen que cuadrar:**
1. El libro, recalculado con LibreOffice sin interfaz (MPL-2.0, gratuito), que también deja guardados los valores para quien lo abra.
2. El mismo modelo en Python (`calculo/motor/`), que da las cifras del PDF.

Se comparan **todas** las celdas con fórmula (tolerancia 1e-9). Si una sola no cuadra, el semáforo pasa a rojo y no se puede emitir.

**Qué plantilla se usa según la empresa** (cobertura y sector):

| Empresa | Modelo |
|---|---|
| Operativa con 2 o más segmentos validados | DCF por segmentos (suma de partes) + Consolidated + comparables |
| Operativa sin segmentos | DCF consolidado (parte 1) + comparables |
| Sin EBITDA positivo o flujo terminal negativo | Comparables por EV/Ventas (el DCF no da valor: aviso) |
| Banca, seguros, REIT y BDC | Pendiente de la decisión D4 (las plantillas son de flujo de caja libre de la empresa y no sirven para estos sectores) |
| Con deuda y EBITDA estable, si el analista lo activa | + LBO |
| Operación corporativa, si el analista la activa | + Acreción / dilución |

Reutilización (regla 1): ningún repositorio base genera ni recalcula libros de Excel con fórmulas; FRAA `report_export.py` solo vuelca datos con openpyxl. FinRobot (Apache-2.0) tiene operadores deterministas de DCF, WACC, LBO, suma de partes y síntesis (`engine/compute/operators/`): se usan como **segunda comprobación** del motor en Python, no como modelo (el modelo son las plantillas).

## 4. Entradas del analista (las mínimas)

Todo lo demás sale de la SEC y del mercado. Cada entrada trae un valor por defecto marcado «Revisar».

| Entrada | Por defecto | Origen del valor por defecto |
|---|---|---|
| Crecimiento de ventas de cada segmento (5 años) | Tasa de crecimiento anual compuesto de los 3 últimos ejercicios del segmento | Normalizador SEC (las plantillas usaban consenso) |
| Margen EBIT de cada segmento | El último margen, constante (regla de la plantilla) | Plantilla |
| Crecimiento a perpetuidad y reparto perpetuidad / múltiplo | 2,5 % y 80 / 20 | Plantilla |
| Lista de comparables | La del analista (obligatoria para el múltiplo de salida y la beta; sin ella, 100 % perpetuidad y beta propia, con aviso) | Ya existe |
| Prima de riesgo de mercado | Decisión D7 | Plantilla (4,06 %) o informe actual (5,5 %) |
| Escenario | Base | Interruptor `CASE` de la plantilla LBO |
| LBO (si se activa) | Prima del 25 %, deuda por tramos en veces EBITDA, tipos y 5 años | Plantilla |
| Acreción / dilución (si se activa) | Términos de la operación | Analista |

## 5. Controles de coherencia («que los números cuadren»)

Bloquean la emisión si fallan:
- Las dos vías de cálculo dan lo mismo.
- La suma de los segmentos es igual al total consolidado.
- El balance cuadra (activo = pasivo + patrimonio).
- El flujo de caja es igual a la variación de la caja.
- La deuda del LBO cuadra (saldo inicial − amortización = saldo final) y el revolver no se excede.

Avisan sin bloquear:
- WACC mayor que el crecimiento a perpetuidad.
- Valor terminal por debajo del 85 % del EV.
- El múltiplo implícito de la perpetuidad y el crecimiento implícito del múltiplo están en rango frente a los comparables.
- La convención de mitad de año está aplicada.
- No hay cifras tecleadas en fórmulas ni vínculos externos.
- El precio objetivo coincide con la hoja Síntesis.
- Las acciones diluidas son mayores o iguales que las básicas.

## 6. Plan por pasos

Cada paso termina con tests, documentación y commit; los pasos 7 y 9 terminan además con un PDF para revisión.

| Paso | Qué | Verificación |
|---|---|---|
| 0 | LibreOffice sin interfaz y comparador de celdas; *golden tests* con las propias plantillas: recalcular cada original y reproducir sus valores guardados | Los 12 libros recalculados cuadran con sus valores guardados |
| 1 | DCF simple en el motor (libro + Python) | Con los datos de AMZN del original, el mismo precio que su *Answer Key* |
| 2 | DCF avanzado: Operating Model, DCF por segmento, Consolidated, WACC, Shares y sensibilidades | Mismo precio por acción y mismas tablas que la parte 3 con sus datos |
| 3 | Comparables (base de datos, estadísticas, precio implícito, prima histórica) | Mismos valores que el *Answer Key* de Trading Comps |
| 4 | LBO avanzado (circularidad, casos, PIK, deuda, balance *pro forma*) e intermedio | Misma TIR, MOIC y controles que la parte 3 |
| 5 | Acreción / dilución | Mismo resultado que su *Answer Key* |
| 6 | Datos de la SEC en lugar de FactSet: correspondencia fila a fila con el normalizador; correcciones E1-E16 | 14 empresas de la regresión: controles del §5 en verde |
| 7 | Selección del modelo por empresa, entradas del analista y libro final descargable | PDF intermedio de AAPL, IOVA, ORCL, NFLX |
| 8 | Integración: sección de valoración y portada del informe, interfaz (entradas y botón de descarga), versiones (cada versión guarda su libro), CLI `informes-warrants modelo TICKER` y regresión | Tests sin conexión y regresión |
| 9 | Revisión final y documentación; después, la B6 (índice A-I como tabla de contenidos) | PDF final para tu revisión |

## 7. Decisiones del usuario

| # | Decisión | Propuesta |
|---|---|---|
| D1 | Derechos de las plantillas: los libros son de rareliquid y sus datos de FactSet («strictly confidential») | Reproducir su estructura y fórmulas al 100 % en libros propios de Warrants & Co., sin su marca ni sus datos; distribuir los originales exige permiso escrito |
| D2 | Proyecciones: las plantillas usan el consenso de FactSet (prohibido por la decisión F3) | Entradas del analista con los valores por defecto del §4 |
| D3 | Instalar LibreOffice (gratis, MPL-2.0) en tu equipo y en el servidor | Sí: es lo que garantiza que el Excel descargado y el PDF dan las mismas cifras |
| D4 | Banca, seguros, REIT y BDC: las plantillas no sirven (flujo de caja libre de la empresa) | Mantener su valoración de la B2 y añadir la hoja de comparables de la plantilla |
| D5 | Lo que hoy tiene el informe y no está en las plantillas | Equivalente en la plantilla: escenarios → interruptor de caso; DCF inverso → crecimiento y múltiplo implícitos; múltiplos históricos → prima frente a múltiplos históricos; suma de partes → DCF por segmento. Se retiran la convergencia a 10 años y la proyección hasta el BPA, que no están en las plantillas |
| D6 | Corregir los errores E1-E16 aunque cambie alguna fórmula del original | Sí, con cada corrección anotada en la hoja Controles |
| D7 | Prima de riesgo de mercado por defecto | La de la plantilla (4,06 %), editable |
