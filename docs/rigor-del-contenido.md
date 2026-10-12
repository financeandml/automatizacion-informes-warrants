# Rigor del contenido: carencias, soluciones y plan

Análisis del borrador de AAPL FY2025 (commit 11905b3) frente a un estándar institucional. Para cada carencia: qué falla (con cifras reales), qué hay ya en los repositorios base ([inventario](inventario/README.md)), qué se ha **verificado con datos reales de la SEC** el 2026-10-12 y cómo se resuelve de forma **determinista**. Después, el diseño de los apartados «parciales» del índice del usuario y el orden de trabajo.

**Alcance acordado con el usuario (2026-10-12).**
- Lo que el índice tiene **hecho** se mantiene; los cambios sobre ello van **al final**.
- Lo **parcial** es prioridad alta y se cierra con la solución completa.
- Lo **ejecutable**, lo **externo** (fuentes no SEC) y lo del **analista** se aparcan por ahora.

Cobertura en los repos: **Total** (se usa tal cual), **Parcial** (hay piezas; hay que construir el resto), **Ninguna**.

## Estado de las carencias (2026-10-12)

Implementado y verificado contra la SEC (97 tests, 23 contra la SEC real; ejemplo en [AAPL_FY2025_borrador.pdf](ejemplos/AAPL_FY2025_borrador.pdf), 10 páginas). Se probó de punta a punta con AAPL, MSFT, JNJ, XOM, TSLA, RIVN y KO; los bancos y demás perfiles sectoriales paran con un mensaje claro (su PDF está pendiente).

| # | Carencia | Estado | Dónde está |
|---|---|---|---|
| 1 | Valoración | ✅ Escenarios pesimista/base/optimista editables (25/50/25), 5 + 5 años, flujo terminal normalizado, DCF inverso (crecimiento y rentabilidad implícitos), segunda sensibilidad, Rf de FRED, comparables con aviso «Revisar» | `calculo/dcf.py`, `calculo/valoracion_relativa.py`, `ingesta/comparables.py`, `informe/estimaciones.py` |
| 1 | Remuneración en acciones (SBC) | ✅ Coste: el FCFF parte del EBIT (que ya la resta) y no la suma; P/FCF y FCF yield sobre el FCF tras SBC | `calculo/metricas.py`, `calculo/dcf.py` |
| 2 | Datos desfasados | ✅ LTM (cuatro últimos trimestres) en el normalizador; múltiplos, DCF y proyección sobre el LTM; periodos estimados de doce meses («jun-27e») | `calculo/normalizador.py` `FuenteLTM` |
| 3 | Estimaciones hasta el BPA | ✅ Proyección línea a línea (resultado financiero, impuestos, minoritarios, acciones, BPA, DPA, FCF por acción) coherente con el DCF. El contraste con el consenso queda aparcado (fuente externa) | `calculo/proyeccion.py` |
| 4 | Segmentos y geografía | ⏳ Tarea pendiente con plan cerrado (abajo) | — |
| 5 | Texto analítico | ✅ Puente del margen operativo por partidas (pb), apalancamiento operativo y uso del capital, redactados por reglas; la contribución por segmento llegará con la carencia 4 | `calculo/analitica.py`, `plantillas/secciones/financiero.md.j2` |
| 6 | Gobierno | ✅ Auditor (dei), retribución del CEO y de los directivos, retribución efectiva, *pay ratio* y rentabilidad para el accionista frente a sus comparables (proxy). El consejo sigue siendo tarea del analista | `ingesta/gobierno.py`, `plantillas/secciones/gobierno.md.j2` |
| 7 | Riesgos cuantitativos | ✅ Altman Z, Beneish M y Piotroski F (golden con el 10-K FY2023 de AAPL); comparación del Item 1A con el año anterior (calibrada: AAPL 2025 vs 2024 = 1 nuevo, 2 eliminados, 5 modificados, 21 iguales) | `calculo/puntuaciones.py`, `ingesta/riesgos.py` `comparar_riesgos` |
| 8 | Ratios sin contexto | ✅ Notas por reglas (ROE, ROIC, caja neta, tipo fiscal, PER) y anexo B de metodología y fuentes | `calculo/notas.py`, `calculo/definiciones.py` |

**Reutilización (regla 1).** FinRobot (Apache-2.0, nuevo en el inventario): DCF inverso, flujo terminal normalizado y reglas de la mediana de comparables. edgar_analytics (MIT): fórmulas y umbrales de Altman, Beneish y Piotroski. financial-research-analyst-agent: convergencia lineal y escenarios (idea). edgartools: TTM, proxy, auditor y lista de tickers. Propio, porque no existía: proyección hasta el BPA, analítica de márgenes, notas y comparación del Item 1A.

**Hallazgos de la prueba con varias empresas, ya corregidos en el normalizador.**
- **Partidas que no se declaran como total**, calculadas con conceptos declarados y señaladas como aviso en el semáforo:
  - El pasivo de KO.
  - El patrimonio de JNJ y RIVN.
  - El EBIT de JNJ y XOM, como BAI + intereses.
- **Partidas declaradas por componentes**: la D&A y los gastos generales de MSFT y GOOGL.
- **Acciones básicas como diluidas** cuando la empresa no declara dilución (XOM).
- **Patrimonio temporal** en la identidad del balance (TSLA).
- **Empresas recientes**: los años previos a la salida a bolsa no son errores (RIVN).
- **Acciones en circulación desfasadas** (BRK-B, dato de 2011): se usa el respaldo.
- **Beneficio antes de impuestos**: se quitó `…BeforeIncomeTaxesDomestic`, que es solo el beneficio en EEUU.

## Resumen (análisis inicial)

| # | Carencia | Solución en los repos | Cobertura | Verificado con datos reales |
|---|---|---|---|---|
| 1 | Valoración poco creíble | FRAA `dcf_model.py` (escenarios, convergencia, sensibilidad), FRAA `peer_comparison.py` (agregados), FRED DGS10 | Parcial | Sí: Rf real 5,24 %; el 79,7 % del EV es valor terminal; el DCF inverso no tiene solución a 3 años |
| 2 | Datos desfasados (FY en vez de LTM) | ET `Company.get_ttm`, `edgar/ttm/` | Total (cálculo) | Sí: ingresos LTM 466.823 M = 416.161 + 364.357 − 313.695 |
| 3 | Estimaciones solo hasta EBITDA | EA `forecasting.py` (solo idea) | Ninguna | — (construcción propia) |
| 4 | Sin segmentos ni geografía | ET `FactQuery.by_dimension`, `xbrl/dimensions.py` | Parcial (extracción sí; validación no) | Sí: AAPL, MSFT y JNJ (dos trampas detectadas) |
| 5 | Texto descriptivo, no analítico | EA `scores.py` (`WorkingCapitalCycle`, `DuPontDecomposition`), EA `ALERTS_CONFIG`, FRAA `compute_historical_context` | Parcial | — (fórmulas sobre partidas ya verificadas) |
| 6 | Gobierno vacío | ET `ProxyStatement`, `extract_auditor_info`, `Form4`, `TenK.subsidiaries` | Total (datos) | Sí: auditor, retribución, *pay ratio*, accionistas > 5 %, filiales, Form 4 |
| 7 | Riesgos solo cualitativos | EA `scores.py` (Altman, Beneish, Piotroski); ET `_render_filing_comparison` (idea) | Parcial | Sí: comparación de riesgos AAPL 2025 vs 2024; alarmas 8-K 4.01/4.02 reales |
| 8 | Ratios sin contexto ni metodología | EA `docs/METRICS_REFERENCE.md` (idea), FRAA `compute_historical_context` (idea) | Parcial | — |

---

## 1. Valoración poco creíble

**Qué falla (AAPL, motor actual):**
- **Peso del valor terminal.** Proyecta 3 años y el valor terminal es el **79,7 % del EV** (1.111.737 de 1.395.263 M USD). Casi todo el valor depende de un solo supuesto (g).
- **Tasa libre de riesgo.** Es un 4,5 % fijo. El bono a 10 años está en el **5,24 %** (FRED DGS10, 2026-10-08). Con la tasa real, el valor baja de 92,59 a **84,79 USD**.
- **DCF inverso.** Con este esquema no tiene solución: ni un 60 % de crecimiento anual durante 3 años iguala el precio (336,64 USD). Que el mercado pague 43,9x PER implica crecimiento alto durante **muchos** años o un coste de capital mucho menor; un horizonte de 3 años no puede representarlo.
- **Remuneración en acciones.** No se descuenta: son 12.863 M USD (3,1 % de las ventas y **13,0 % del FCF**). Es un coste económico real (dilución).
- **Escenarios, comparables y sensibilidad.** No hay escenarios ni contraste con comparables. La sensibilidad solo cruza WACC y g.

**Qué hay en los repos:**
- **FRAA `src/tools/dcf_model.py`** (MIT, parcial):
  - `run_dcf_analysis` tiene escenarios *bull/base/bear* y un crecimiento que **converge linealmente a g** en 10 años.
  - `sensitivity_analysis` da una matriz 5×5.
  - Errores ya documentados: no resta la deuda neta, usa crecimientos de Yahoo, mete `inf` en la matriz y emite su propia recomendación. Se reutilizan las ideas, no el código.
- **FRAA `src/tools/peer_comparison.py`:** `compare_peers` (`peer_aggregates`: mediana, media, mínimo, máximo; `percentile_rankings`; `relative_valuation`). Se reutiliza la agregación, con métricas calculadas desde la SEC y no desde Yahoo.
- **FRAA `src/tools/macro_data.py` `get_treasury_yields`:** necesita clave de FRED. **Verificado:** el CSV público `fredgraph.csv?id=DGS10` no la necesita, y `^TNX` de yfinance sirve de respaldo.
- **Sin cobertura en ningún repo:** el DCF inverso, la remuneración en acciones como coste y el gráfico de rangos de valoración (*football field*).

**Solución determinista** (en `calculo/dcf.py` y `calculo/valoracion_relativa.py`):
1. **Tasa libre de riesgo de mercado:** DGS10 de FRED, con su fecha en la trazabilidad; `^TNX` como respaldo. El analista puede fijarla.
2. **Horizonte de 5 + 5 años:** 5 años explícitos que edita el analista, y 5 de convergencia lineal de crecimiento y margen hacia g y el margen terminal (patrón de FRAA). El valor terminal deja de pesar el 80 %.
3. **Remuneración en acciones como coste operativo:** FCFF = EBIT·(1−t) + D&A − capex − ΔNWC − SBC, con su línea visible en la tabla.
4. **Tres escenarios** con probabilidades (por defecto 25/50/25):
   - Base: medias históricas.
   - Pesimista y optimista: ±1 desviación típica histórica del crecimiento y del margen.
   - El precio objetivo del DCF es la media ponderada; el analista edita los tres.
5. **DCF inverso en dos variantes:**
   - El crecimiento a 5 años que iguala el precio.
   - La **rentabilidad implícita** (TIR) que obtiene quien compra hoy con el escenario base.
   - Se resuelve por bisección y lleva tests contra valores calculados a mano.
6. **Comparables:**
   - Múltiplos LTM (EV/EBITDA, PER, EV/Ventas, P/FCF) de cada comparable, calculados con **el mismo normalizador** (companyfacts de cada uno) y su precio.
   - Mediana y percentiles.
   - Valor implícito por múltiplo.
   - Precio objetivo final = `peso_dcf` · DCF + (1 − `peso_dcf`) · múltiplos.
7. **Gráfico de rangos de valoración:** rango de cada método (escenarios del DCF, cuartiles de cada múltiplo, máximo y mínimo de 52 semanas) frente a la cotización.
8. **Segunda tabla de sensibilidad:** crecimiento × margen EBITDA.

**Limitaciones y decisiones:**
- **La selección de comparables por código SIC es tosca.** AAPL tiene SIC 3571 («ordenadores»): saldrían Dell, HP y Super Micro, no Microsoft o Alphabet. El SaaS propondrá la lista y el analista la edita.
- **La propuesta automática necesita el universo SIC.** `edgar.reference.get_companies_by_industry` devuelve vacío si no se ha descargado el *bulk* de *submissions* de la SEC (más de 1 GB, una vez, fuera de OneDrive). La alternativa es consultar empresa a empresa y cachearlo. **Decisión del usuario.**

## 2. Datos desfasados

**Qué falla:** el informe es del 2026-10-11 y usa el FY2025, cerrado el 2025-09-27, aunque ya hay tres 10-Q del FY2026 (el último, 0000320193-26-000020, del 2026-07-31). Los ingresos LTM son **466.823 M USD**, un 12 % más que los 416.161 M USD del FY2025. Los múltiplos y la valoración usan un año viejo.

**Qué hay en los repos:**
- **ET `Company.get_ttm(concept)` y `edgar/ttm/calculator.py` `TTMCalculator`:** devuelven `has_gaps`, `is_stale` y los trimestres usados.
- **ET `ttm/splits.py`:** ajusta los *splits*.
- **Cobertura total del cálculo.** El `compute_ttm` de edgar_analytics es incorrecto y no se usa.

**Verificado:**
- `get_ttm` da 466.823 M USD (Q4 FY25 a Q3 FY26), y el cálculo independiente con companyfacts (FY2025 + 9 meses del FY2026 − 9 meses del FY2025 = 416.161 + 364.357 − 313.695) da **exactamente lo mismo**. Beneficio neto LTM: 128.930 M USD; resultado operativo: 154.859 M USD; flujo operativo: 146.724 M USD.
- **Trampa:** `get_ttm("Revenues")` devuelve un dato de **2018** (`is_stale=True`), porque Apple dejó de usar ese concepto.

**Solución:**
- El LTM sale de **nuestro normalizador** (regla 9): `FuenteEntityFacts` se amplía a periodos trimestrales y, para cada partida, prueba sus conceptos por orden de prioridad con `TTMCalculator`, descartando los resultados con `is_stale` o `has_gaps`.
- Las partidas de balance se toman del último 10-Q.
- Los múltiplos y el punto de partida del DCF pasan a LTM.
- Se añade una tabla de los últimos 8 trimestres.
- Test *golden* con la identidad FY + YTD − YTD anterior.
- **Por la regla del usuario,** las columnas LTM en las tablas ya hechas (apartados 7-9) se añaden al final; la valoración (apartado 10, parcial) usa el LTM desde el principio.

## 3. Estimaciones solo hasta EBITDA

**Qué falla:** el beneficio neto y el BPA estimados salen «—». Sin BPA estimado no hay PER adelantado ni PEG, y el analista no puede contrastar su tesis.

**Repos:** **ninguno.** La proyección de los tres estados es la necesidad sin resolver n.º 1 del inventario; edgar_analytics solo trae un ARIMA de ingresos a un paso.

**Solución** (en `calculo/proyeccion.py`, sobre las estimaciones del analista):

| Partida | Cálculo |
|---|---|
| Ventas, EBITDA, D&A, EBIT | Ya existen |
| Gastos financieros | Coste de la deuda × deuda media |
| BAI | EBIT − gastos financieros |
| Impuestos | BAI × tasa fiscal |
| Beneficio neto | BAI − impuestos − minoritarios |
| Acciones | Variación media histórica de las acciones diluidas (recompras); editable |
| BPA y DPA | BN / acciones; DPA = BPA × pay-out histórico |
| FCF por acción | FCF / acciones |

**Coherencia comprobada por test:** el BPA del primer año estimado, con los supuestos históricos, debe quedar a menos de un 5 % del último real.

## 4. Sin segmentos ni geografía

**Qué falla:** no hay desglose del negocio, lo más básico para analizar una empresa.

**Qué hay en los repos:**
- **ET `FactQuery.by_dimension(eje)`** extrae los hechos con dimensiones.
- **ET `xbrl/dimensions.py` `is_breakdown_dimension`.**
- **Parcial:** la extracción existe, pero no hay validación ni gestión de jerarquías.

**Verificado** (con `by_dimension`; el `to_dataframe()` normal no trae las columnas de los ejes):

| Empresa | Producto (`ProductOrServiceAxis`) | Segmentos (`StatementBusinessSegmentsAxis`) | Geografía (`StatementGeographicalAxis`) |
|---|---|---|---|
| AAPL FY2025 | iPhone 209.586 · Mac 33.708 · iPad 28.023 · Wearables 35.686 · Servicios 109.158 (y **«Products» 307.003, que es la suma de los cuatro primeros**) | Américas, Europa, China… cruzados con un segundo eje (`ConsolidationItemsAxis`) | EE. UU. 151.790 · China 64.377 · Resto 199.994 |
| MSFT FY2026 | 12 líneas | 3 segmentos, también con resultado operativo por segmento | EE. UU. / resto |
| JNJ FY2025 | Solo con varios ejes cruzados | Innovative Medicine 60.401 · MedTech 33.792 | 53.752 / 40.441, **etiquetado «U.S. Plans»** (etiqueta errónea reutilizada de pensiones) |

**Solución** (normalizador de segmentos en `calculo/normalizador.py`, regla 9):
1. **Ejes por prioridad:** segmentos declarados (aceptando el segundo eje solo si es el de segmentos operativos), producto y geografía.
2. **Validación:** un desglose solo se acepta si sus miembros suman el total consolidado (±1 %). Si no cuadra, se marca para el analista; nunca se muestra uno que no cuadre.
3. **Jerarquías:** si un miembro es igual a la suma de otros (el «Products» de AAPL), se descarta como subtotal.
4. **Nombres:** se toman del identificador del miembro (`country:US` → «EE. UU.»), con la etiqueta solo como respaldo. Así se evita el «U.S. Plans» de JNJ.
5. **Cinco años:** se cosen dos 10-K, porque cada uno trae tres años.
6. **Resultado:** peso, crecimiento y contribución al crecimiento de cada segmento, y un gráfico de barras apiladas (no hay ninguno en los repos).
7. **Clientes:** concentración con `ConcentrationRiskByBenchmarkAxis` y `MajorCustomersAxis` cuando se declaren. Muchas empresas no los cifran sobre ingresos (en AAPL no aparecen).

## 5. Texto descriptivo, no analítico

**Qué falla:** «los ingresos pasaron de X a Y» describe; no explica.

**Repos:**
- **EA `scores.py`** (MIT): `WorkingCapitalCycle` (días de cobro, de existencias y de pago) y `DuPontDecomposition`.
- **EA `config.py` `ALERTS_CONFIG`:** umbrales de alerta (idea).
- **FRAA `llm_insight_engine.compute_historical_context`:** percentil frente a la propia historia (idea).
- **Ninguno** hace el desglose del crecimiento ni el puente de márgenes.

**Solución** (cálculo en `calculo/analitica.py`; redacción por plantilla con frases elegidas por reglas, sin IA):
- **Origen del crecimiento:** cuántos puntos aporta cada segmento (Δ segmento / ingresos del año anterior). Por ejemplo, «Servicios aportó +X pp de los Y pp de crecimiento».
- **Puente de márgenes:** variación del margen bruto, de I+D sobre ventas y de gastos generales sobre ventas, en puntos básicos, que explica el cambio del margen operativo.
- **Apalancamiento operativo:** Δ % EBIT / Δ % ventas.
- **Asignación del capital:** dividendos + recompras sobre FCF, reducción neta de acciones y capex sobre D&A.
- **Circulante:** días de cobro, existencias y pago (si existen las partidas; hay que añadir clientes, existencias y proveedores al normalizador).
- **Reglas de redacción:**
  - El verbo y el adjetivo dependen de umbrales fijos: «mejoró» si > +50 pb, «estable» entre ±50 pb.
  - Siempre se nombra el principal contribuidor.
  - Cada frase lleva su cifra.

## 6. Gobierno vacío

**Repos:** **ET, cobertura total de los datos.**

**Verificado en AAPL:**
- **`extract_auditor_info`:** Ernst & Young LLP, San José, PCAOB 42, certifica el control interno.
- **`ProxyStatement`** (DEF 14A del 2026-01-08, con XBRL):
  - Retribución del CEO y media de los consejeros ejecutivos durante 5 años.
  - Retribución frente a resultados: rentabilidad para el accionista frente a la de sus comparables.
  - *Pay ratio*: **533×** (74,3 M USD frente a 139.483 USD).
  - Accionistas > 5 %: Vanguard 9,63 % y BlackRock 7,10 %. Los nombres llegan con espacios de no separación y hay que limpiarlos.
- **`TenK.subsidiaries`:** 19 filiales del Exhibit 21.
- **`Form4.get_ownership_summary()`:** operaciones de los directivos. Por ejemplo, John Ternus (CEO) y Timothy D. Cook (Executive Chair) en octubre de 2026.
- **Limitaciones:**
  - `audit_fees` sale vacío en AAPL.
  - `named_executives` trae los nombres sin cargo completo.
  - La composición del consejo y su independencia **no están estructuradas** (necesidad sin resolver n.º 13): se quedan para el analista.

**Solución:** gobierno automático (auditor, retribución, *pay ratio*, accionistas, filiales), más los cambios de equipo directivo del 8-K Item 5.02. **Por la regla del usuario,** los apartados 4 y 5 del índice son «ejecutables» y se aparcan. Ahora solo entran los insiders (18) y el auditor y sus cambios (21).

## 7. Riesgos solo cualitativos

**Repos:**
- **EA `scores.py`** (MIT, parcial):
  - `AltmanZScore` (Z, Z'' y Z' según el sector), `BeneishMScore` (8 índices; manipulación probable si M > −1,78), `PiotroskiScore` (9 pruebas) y `compute_all_scores(is_financial=...)`, que los suprime en entidades financieras.
  - Funciones puras, pero sobre DataFrames por etiqueta, incompatibles con nuestro normalizador.
- **ET `_render_filing_comparison`:** prompt de riesgos nuevos y eliminados (solo idea).
- **Ninguno** compara los factores de riesgo por código ni los clasifica.

**Verificado:**
- **Comparación de títulos del Item 1A** (AAPL 2025, 27 títulos, frente a 2024, 28 títulos): 3 nuevos, 2 eliminados y 3 modificados.
  - **Trampa:** «net sales and gross margins are subject to volatility» (nuevo) reformula «quarterly net sales … fluctuate» (eliminado).
  - Por eso se muestran como «nuevo o reformulado», emparejados con el más parecido del año anterior.
- **Alarmas del 8-K, deterministas y reales:**
  - Item 4.02 (los estados anteriores dejan de ser fiables) el 2006-08-04: el caso de las *stock options* antedatadas.
  - Item 4.01 (cambio de auditor, de KPMG a EY) el 2009-02-27.
  - Dos 10-K/A (2010 y 1998).

**Solución:**
- **`calculo/puntuaciones.py`:** Altman, Beneish, Piotroski y acumulaciones de Sloan reimplementados sobre las partidas normalizadas, con atribución a edgar_analytics (MIT).
  - Hay que añadir al normalizador clientes, existencias, inmovilizado y reservas.
  - Se valida contra edgar_analytics en un test (dependencia solo de desarrollo).
  - No se aplican a bancos, aseguradoras ni REIT.
- **Comparación del Item 1A:** similitud de texto entre títulos (`difflib`, umbral calibrado con tests); el resultado son nuevos o reformulados, eliminados y modificados.
- **Clasificación:** regulatorio, financiero, competitivo, operativo y de ejecución, macro y legal, por reglas de palabras clave sobre el título. Sin IA y comprobable en tests.

## 8. Ratios sin contexto ni metodología

**Qué falla:** un ROE del 151,9 % o un ROIC del 95 % son correctos, pero sin nota parecen errores.

**Repos:** EA `docs/METRICS_REFERENCE.md` (estructura de referencia, idea) y FRAA `compute_historical_context` (idea). **Parcial.**

**Solución:**
- **Notas por reglas:**
  - Patrimonio < 10 % del activo o negativo → «ROE no comparable: patrimonio reducido por recompras».
  - DFN < 0 → «caja neta».
  - Capital invertido ≤ 0 → ROIC «no significativo».
- **Contexto histórico:** posición de cada múltiplo frente a su propia media de 5 años.
- **Anexo de metodología** generado desde las definiciones de `calculo/metricas.py`, para que no haya dos versiones que se desincronicen.

---

## Apartados «parciales» del índice: diseño

| Apartado | Diseño (solo SEC y cálculo propio) | Depende de |
|---|---|---|
| **2 Resumen ejecutivo** | 3-5 «hechos clave» elegidos por reglas de la analítica: mayor cambio del año, valoración frente a su historia, alarmas y riesgos nuevos. Más la recomendación y la tesis del analista | 1, 4, 5, 7 |
| **3 Qué hace la empresa** | Cita del Item 1 (ya existe), segmentos y geografía validados, contribución al crecimiento, concentración de clientes | 4 |
| **6 Pipeline y catalizadores** | **(a)** El bloque de catalizadores del MD&A, ya construido en `ia/bloques.catalizadores` (la IA solo elige índices; la cita se verifica), se conecta al informe. **(b)** Calendario determinista desde la SEC: próximos resultados estimados por el plazo histórico entre cierre y 10-Q (marcado «estimado»), junta anual (DEF 14A), vencimientos de deuda (**verificado**: 12.393 / 10.078 / 9.300 / 5.235 / 4.972 / 49.303 M USD en AAPL). **(c)** Hechos relevantes de 12 meses por tipo de 8-K: 1.01 contratos, 2.01 adquisiciones, 5.02 cambios en la dirección (p. ej., el nuevo CEO de AAPL) | — |
| **10 Métricas de valoración** | Toda la carencia 1, más el PEG con el crecimiento histórico del BPA y el PER adelantado con el BPA estimado (carencia 3). El consenso (Yahoo) queda fuera por ser externo | 1, 2, 3 |
| **14 Análisis competitivo** | Párrafo literal «Competition» del Item 1 (**verificado** en AAPL); tabla de comparables con el mismo normalizador; cuota sobre ventas **entre comparables cotizados**; evidencia de ventaja competitiva: diferencia ROIC − WACC durante 5 años y estabilidad del margen bruto frente a la mediana de los comparables. El juicio es del analista | 1 (comparables) |
| **18 Insiders y accionistas** | Form 4 de 12 meses: compras y ventas netas en mercado (códigos P/S), separadas de concesiones y ejercicios (A/M/F), por persona y cargo, señalando los planes 10b5-1. Accionistas > 5 % del proxy, con los 13D/13G posteriores. El 13F por emisor queda aparcado (ejecutable) | — |
| **20 Riesgos** | Carencia 7: top 5 actual, más clasificación, nuevos y eliminados, puntuaciones cuantitativas y alertas de apalancamiento y cobertura | 7 |
| **21 Historial de resultados** | Alarmas SEC deterministas: 8-K 4.02 (reformulación) y 4.01 (auditor), 10-K/A, NT 10-K / NT 10-Q (presentación tardía), debilidad material (Item 9A), salvedad de empresa en funcionamiento («substantial doubt»). Reacción bursátil en los días siguientes a cada 8-K 2.02 (resultados; 94 en AAPL). Las sorpresas frente al consenso quedan fuera (externo) | 2 |
| **26 Fuentes** | Anexo automático con cada documento usado (número de registro y fecha: 10-K, 10-Q, DEF 14A, Form 4, 8-K), la descarga de companyfacts, la cotización y DGS10 con fecha, y la metodología (carencia 8) | 8 |

## Orden de trabajo propuesto

Cada paso termina con tests *golden* frente a la SEC, documentación, commit y un PDF intermedio para revisión.

| Paso | Contenido | Cubre |
|---|---|---|
| **4.1 Base de datos** | LTM y trimestres en el normalizador; Rf de mercado; normalizador de segmentos con validación; partidas nuevas (clientes, existencias, inmovilizado, reservas) | Carencias 2 y 4 (cálculo) |
| **4.2 Valoración** | 5 + 5 años, remuneración en acciones como coste, escenarios, DCF inverso, comparables, gráfico de rangos y segunda sensibilidad; proyección hasta el BPA | Carencias 1 y 3, apartado 10 |
| **4.3 Negocio y analítica** | Segmentos en el informe, origen del crecimiento, puente de márgenes, asignación del capital, resumen ejecutivo por reglas | Carencia 5, apartados 2 y 3 |
| **4.4 Riesgos e historial** | Puntuaciones, comparación del Item 1A, clasificación, alarmas SEC, reacción a resultados | Carencia 7, apartados 20 y 21 |
| **4.5 Catalizadores e insiders** | MD&A conectado, calendario, hechos relevantes del 8-K, Form 4, accionistas > 5 % | Apartados 6 y 18 |
| **4.6 Competencia** | Comparables, cuotas y evidencia de ventaja competitiva | Apartado 14 |
| **4.7 Fuentes y metodología** | Anexo automático y notas de contexto de los ratios | Carencia 8, apartado 26 |
| **Al final** | Cambios en lo ya hecho: columnas LTM en los apartados 7-9, BPA estimado en la portada, DuPont en el 11 | Regla del usuario |

## Tarea pendiente: segmentos y geografía (plan)

Verificado con AAPL, MSFT y JNJ (carencia 4). Pasos, cada uno con test *golden*:

1. **Lectura completa de FinRobot `engine/compute/coordinators/segment_extractor.py`** (Apache-2.0), por si resuelve ya la jerarquía o la validación.
2. **`calculo/normalizador.py` `segmentos(xbrl, eje)`.** Con `by_dimension` de edgartools y por orden de prioridad: segmentos declarados (aceptando el segundo eje solo si es `ConsolidationItemsAxis` = segmentos operativos), producto/servicio y geografía.
3. **Validación determinista:**
   - Los miembros deben sumar el total consolidado (±1 %).
   - Se descartan los subtotales (miembro = suma de otros: «Products» en AAPL).
   - Los nombres salen del identificador del miembro (`country:US` → «EE. UU.»), no de la etiqueta («U.S. Plans» en JNJ).
   - Si no cuadra, el bloque pasa al analista; nunca se muestra un desglose que no cuadre.
4. **Cinco años:** se cosen dos 10-K (cada uno trae tres años); el LTM por segmento sale de los 10-Q si lo declaran.
5. **`calculo/analitica.py` `contribucion_segmentos`:** peso, crecimiento y puntos de crecimiento que aporta cada segmento; frase por reglas («Servicios aportó +X pp de los Y pp»).
6. **Informe:** tabla y gráfico de barras apiladas en la sección 02 (negocio) y frase en el comentario financiero; concentración de clientes si se declara.

## Decisiones del usuario

1. **Universo de comparables:** ✅ resuelto sin descargar el *bulk*. La SEC da los CIK por SIC (`browse-edgar`, Atom), la lista oficial de tickers las cotizadas y la API *frames* el tamaño. La lista se marca «Revisar» y el analista la cambia con `--comparables`.
2. **Remuneración en acciones:** ✅ como coste en el flujo de caja (decisión del usuario, 2026-10-12).
3. **Escenarios:** ✅ 25/50/25 editables; dispersión acotada (crecimiento ±2-5 pp, margen ±1-3 pp).
