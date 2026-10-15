# Motor de valoración (B1): análisis de las plantillas y plan

Estado: **implementado** (decisiones D1-D7 del usuario, 2026-10-14; estado y limitaciones en el §8). Origen: las plantillas de `Motor de valoración/Ejemplos-plantillas/` (rareliquid; no se publican en el repositorio). Regla del usuario: usarlas **siempre**, sin eliminar funciones ni relaciones entre hojas y sin añadir nada que no esté en ellas; el analista introduce las mínimas variables y descarga el modelo completo para verificarlo número a número.

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

Encontrados al reproducir las plantillas con datos reales (corregidos; la lista completa, en la hoja Controles de cada libro):

| # | Dónde | Corrección |
|---|---|---|
| E17 | Capital circulante | La inversión (aumento = pago) sale del balance; la plantilla restaba un cobro |
| E18-E19 | Convertibles | Precio de conversión = 1.000 / ratio; si convierten, su principal sale de la deuda |
| E20 | Periodo parcial | Nulo si la fecha de valoración ya pasó el cierre del ejercicio en curso |
| E21-E26 | LBO | EBIT conservador sin autorreferencia; intangibles sin circularidad; signo de otros activos y pasivos a largo plazo; amortización total con pagos obligatorios y PIK; tipo PIK en todos los años; acciones diluidas con opciones y RSU |
| E27-E29 | LBO, balance *pro forma* | Depreciación del caso elegido; amortización de comisiones de financiación como gasto no monetario; «otros usos» como coste de la operación. Con ellas el balance cuadra (el de la plantilla descuadraba entre −32,7 y −37,8 al año) |
| E30 | LBO, control de la deuda | Con tolerancia relativa: la igualdad exacta sobre valores iterativos dependía del residuo de la iteración |
| E31 | LBO, balance proyectado | Las preferentes que la operación no amortiza siguen en el balance (la plantilla no tenía preferentes; con ORCL descuadraba en 4.954 cada año) |
| — | DCF con valor por acción ≤ 0 (ORCL y RIVN con los supuestos por defecto) | No es una valoración: se muestra en el modelo y en el texto, con aviso y nota para el analista, pero no entra en el precio objetivo |
| — | Historia corta (menos de 5 ejercicios en la SEC) | Las ratios de los años sin datos daban #DIV/0! y el error llegaba al WACC: se marcan «--» (como hace la plantilla) con `IFERROR`, un comentario en la celda y un aviso |

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
1. El mismo libro evaluado en Python (`calculo/motor/excel.py`, validado contra los 7.250 valores guardados de las 12 plantillas), que da las cifras del PDF.
2. El libro recalculado con LibreOffice sin interfaz (MPL-2.0, gratuito; `calculo/motor/recalculo.py`).

Se comparan **todas** las celdas con fórmula (tolerancia relativa y absoluta de 1e-6). Decisión del usuario: el informe se emite igualmente; cada discrepancia sale como aviso con la celda y los dos valores, y la lista completa queda en `<libro>_discrepancias.csv`. Dos detalles técnicos:
- El .xlsx lleva junto a cada fórmula el valor calculado en Python (como hace Excel al guardar): se ve aunque el programa no recalcule y LibreOffice itera el bloque circular del LBO desde él, de modo que confirma que cada fórmula se cumple (desde cero, LibreOffice dejaba celdas del bloque circular sin actualizar). Excel recalcula todo al abrir.
- LibreOffice no calcula las tablas de datos de Excel (sensibilidades): esas celdas y lo que lee de ellas no se contrastan (se avisa) y las calculan Python y Excel.
- Cálculo iterativo: 1.000 iteraciones y cambio máximo 1e-7 (las plantillas: 100 y 0,001, cuyo residuo dejaba incoherente el bloque circular).

Resultado (2026-10-15): las 14 empresas de la regresión construyen su libro sin celdas en error y con 0 discrepancias entre las dos vías (AAPL: 3.652 celdas; los libros sectoriales, 70-94). Controles que avisan con datos reales, todos legítimos: valor terminal > 85 % del EV (IOVA, JNJ) y revolver del LBO excedido (ORCL, TSLA: el LBO no sería financiable).

**Qué plantilla se usa según la empresa** (cobertura y sector):

| Empresa | Modelo |
|---|---|
| Operativa con 2 o más segmentos validados | DCF por segmentos (suma de partes) + Consolidated + comparables |
| Operativa sin segmentos | DCF consolidado (parte 1) + comparables |
| Sin EBITDA positivo o flujo terminal negativo | Comparables por EV/Ventas (el DCF no da valor: aviso) |
| Banca, seguros, REIT y BDC | D4: la valoración de la B2 con fórmulas vivas (valor contable justificado, descuento de dividendos, comparables) y la hoja de comparables de la plantilla (`calculo/motor/sectorial.py`), contrastada con el cálculo del informe |
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
| Lista de comparables | La del analista; sin ella, los **comparables modelo** del SaaS: empresas del mismo sector de Damodaran (NYU Stern) cotizadas en NYSE/Nasdaq, las 6 más parecidas por ingresos (SEC); si la empresa no está clasificada, el código SIC. Entran en el libro (múltiplo de salida, hoja Comps) con aviso «Revisar»; el método «Comparables» del precio objetivo sigue exigiendo la lista del analista (decisión del 2026-10-12) | `ingesta/damodaran.py`, `ingesta/comparables.py` |
| Beta | La de los comparables del analista (plantilla); sin ellos, la **beta modelo**: desapalancada y corregida por la caja del sector de Damodaran, reapalancada con la deuda bruta y el tipo de la empresa (fórmula de la plantilla); sin sector, la propia | Damodaran, Betas.html (cada enero) |
| Prima de riesgo de mercado | La vigente, actualizada cada semana (D7): prima implícita del S&P 500 de Damodaran (NYU), «ERP (T12 m with sustainable payout)»; sin conexión, la última guardada o el 5,5 % | `ingesta/mercado.prima_riesgo`; la propone el SaaS y la confirma o cambia el analista |
| Convención de descuento | Mitad de año (la marca el analista: mitad o fin de año) | Plantilla |
| Escenario | Base | Interruptor `CASE` de la plantilla LBO |
| LBO (si se activa) | Prima del 25 %, deuda por tramos en veces EBITDA, tipos y 5 años | Plantilla |
| Acreción / dilución (si se activa) | Términos de la operación | Analista |

## 5. Controles de coherencia («que los números cuadren»)

Ninguno bloquea la emisión (decisión del usuario, 2026-10-14): todos salen como avisos antes de emitir. Controles de cuadre:
- Las dos vías de cálculo dan lo mismo.
- La suma de los segmentos es igual al total consolidado.
- El balance cuadra (activo = pasivo + patrimonio).
- El flujo de caja es igual a la variación de la caja.
- La deuda del LBO cuadra (saldo inicial − amortización = saldo final) y el revolver no se excede.

Controles de coherencia:
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

**Decisiones del usuario (2026-10-14):** D1 sí. D2: los datos de FactSet se sustituyen por los de la SEC con la referencia de cada documento; FactSet solo como excepción para las proyecciones de consenso si falla la SEC y es estrictamente necesario. D3: instalado. D4: sí. D5: se mantiene lo que ya tenía el informe salvo incompatibilidad, pero prevalece el motor (el DCF por escenarios, los múltiplos históricos y la suma de partes siguen como análisis complementario y en la síntesis con su peso). D6: sí, una a una. D7: la prima vigente, actualizada cada semana; el SaaS propone y el analista confirma o cambia. Además: mitad de año y fin de año, a elección del analista; los dos cálculos se comparan celda a celda y las discrepancias avisan sin bloquear.

## 8. Estado de la implementación

| Pieza | Dónde |
|---|---|
| Evaluador de fórmulas de Excel (circularidad, tablas de datos, 15 cifras significativas) | `calculo/motor/excel.py` · test *golden* con las 12 plantillas en `tests/test_motor.py` |
| Libro de Warrants & Co. (estilo de marca, comentarios con el origen, nombres, validaciones, valores guardados) | `calculo/motor/libro.py` |
| Modelo general (Portada, Entradas, Operating Model, DCF por segmento, Consolidated, WACC, Shares, Comps, LBO, Acreción-dilución, Síntesis, Controles, estados y Trazabilidad) | `calculo/motor/modelo.py` y `lbo.py` |
| Modelo sectorial (D4) | `calculo/motor/sectorial.py` |
| DDM e ingreso residual (P19, decisión del usuario del 2026-10-15) | Hoja «DDM y RI» (`modelo._accionista`) y `calculo/accionista.py` (FinRobot, Apache-2.0), contrastados entre sí |
| Segunda vía (LibreOffice) | `calculo/motor/recalculo.py` |
| Conexión con el informe: el DCF del informe es el del modelo; sección «Modelo de valoración» en el PDF; avisos | `informe/motor.py`, `informe/construir.py`, `informe/sectorial.py`, `plantillas/informe/_motor.html.j2` |
| Interfaz: pestaña «Modelo de valoración» (crecimiento y margen por segmento, % por perpetuidad, convención, LBO, «He revisado») y descarga del .xlsx | `ui/app.py`, `ui/logica.py` |
| Versiones: cada versión guarda su libro junto al PDF y los avisos del contraste | `informe/versionado.py` |
| Línea de comandos: `informes-warrants modelo TICKER` (solo el libro) e `informe` (PDF + libro) | `cli.py` |

**D&A, capex y capital circulante por segmento (2026-10-15).** Fuente: la propia SEC (ASC 280 exige el D&A y el capex de cada segmento si los revisa la dirección; ASU 2023-07 amplía el desglose desde 2024); ninguna fuente gratuita externa los da por segmento (los proveedores los toman de estos mismos 10-K). El normalizador extrae el D&A y el capex de cada segmento de negocio (solo miembros y ejercicios validados por los ingresos); en los ejercicios en que todos los segmentos traen el dato y su suma no supera el consolidado, el modelo usa ese dato (tecleado con su *accession*) y reparte lo corporativo por ventas, de modo que el total sigue siendo el de la SEC; si no, el reparto por ventas de la plantilla, con aviso. El capital circulante no lo publica nadie por segmento: por ventas (regla de la plantilla). Probado con AMZN (D&A de la SEC en los 5 ejercicios; capex en 2 —en los demás, las altas por segmento incluyen arrendamientos y superan el capex consolidado, y se rechazan—).

**Limitaciones conocidas:**
- El resultado por segmento se toma de `OperatingIncomeLoss`; las empresas que miden el segmento con otra magnitud (JNJ: beneficio antes de impuestos) salen con DCF consolidado.
- FactSet, aparcado (decisión del usuario, 2026-10-15): las proyecciones son las entradas del analista. Alternativa oficial: la guía (*guidance*) que la empresa publica en sus 8-K de resultados (Item 2.02, anexo 99.1) y en el MD&A; de momento, la lee el analista.
- Sin lista de comparables del analista, el valor terminal es 100 % por perpetuidad y la beta, la propia (se avisa).
