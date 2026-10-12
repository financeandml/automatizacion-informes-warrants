# Propuestas a partir de los informes de referencia (pendientes de valoración)

Ideas de contenido tomadas de dos iniciaciones de cobertura que el usuario dejó en `Plantilla/`:
- **Referencia A:** Nomura sobre Schneider Electric, bienes de equipo, 21 páginas.
- **Referencia B:** Barclays sobre Achillion Pharmaceuticals, biotecnología, 23 páginas.

Ambas son de terceros y no se publican (`Plantilla/*.pdf` está fuera de git). Solo se toman ideas de **contenido**: la maquetación y la identidad del informe no cambian ([maquetación aprobada](ejemplos/AAPL_FY2025_borrador.pdf)).

**Regla del usuario:** nada de esto se implementa sin valoración previa. Estado de cada propuesta: «propuesta».

Columnas:
- **Fuente:** de dónde saldría el dato.
- **Encaje:** apartado del [índice](estructura-informe.md) o tarea de la [hoja de ruta](hoja-de-ruta.md).
- «*Al final*» indica que modifica algo ya hecho, así que, por la regla del usuario, iría al final.

## Encajan en la fase A (primer uso real)

| # | Propuesta | Visto en | Fuente y cálculo | Encaje |
|---|---|---|---|---|
| R1 | **Cuatro hechos clave con etiqueta temática:** Crecimiento · Rentabilidad · Balance y caja · Valoración. Cada uno en una frase con su cifra | A, portada (*Growth, Profitability, Sentiment, Valuation*) | Reglas sobre la analítica ya calculada | Apartado 2 (A2): concreta los 4 hechos clave |
| R2 | **Autonomía de caja y dilución** en empresas con pérdidas: meses de caja al ritmo de consumo actual y crecimiento anual de las acciones | B, riesgos («la caja financia las operaciones hasta principios de 2017») | (Caja + inversiones a corto) / (flujo operativo + capex de los últimos 12 meses, si es negativo); acciones diluidas a 3 años | Apartado 20 y valoración; clave para IOVA |
| R3 | **Tabla de los últimos 8 trimestres:** ingresos, margen operativo y BPA, con variación interanual | B, portada (BPA trimestral y anual) | Trimestres derivados de los 10-Q (normalizador, igual que el LTM) | Apartado 21 (A8); base para la reacción a 5 sesiones |
| R4 | **Pipeline y próximos hitos** (fármaco o producto, indicación, fase, próximo hito y fecha) | B, resumen ejecutivo | Tabla para el analista: la SEC no la estructura y ClinicalTrials.gov es externo (no aprobado) | Apartado 6 (A4); IOVA |
| R5 | **Riesgos para la recomendación y el precio objetivo** (base para la decisión de clasificar, sin ejecutarla): macro frente a específicos de la empresa (crecimiento, rentabilidad, competencia, regulatorio, financiero, ejecución y M&A); en biotecnología, clínico, regulatorio, comercial, precio y financiero. Cada riesgo indicaría qué supuesto del modelo amenaza: crecimiento, margen o WACC | A y B, riesgos | Taxonomía fija; asignación por reglas o por el analista | Apartado 20 (A7): **a decidir** |
| R6 | **Bloque de autoría** en la portada: analistas (nombre, correo, teléfono) y contacto de la empresa | A y B, portada | Configuración del SaaS | A13 |
| R7 | **Sistema de recomendación en el aviso legal**: definición de Comprar, Mantener y Vender (umbrales +15 % / −10 %, horizonte de 12 meses) | B y A, avisos legales | Texto fijo con los umbrales del código | Aviso legal |
| R8 | **Derivación del precio objetivo**: tabla de método · valor · supuesto clave · peso → precio objetivo | A, valoración | Valores ya calculados (DCF por escenarios, múltiplos) | Apartado 10; se amplía con el motor de valoración |
| R9 | **Casos alcista y bajista con su desencadenante**: precio del escenario y una frase de qué tendría que pasar | B, cuadro de la recomendación | Precios de los escenarios (ya calculados) + frase editable del analista | Apartado 10 y portada (*al final*) |
| R10 | **Comparables con crecimiento**: crecimiento anual compuesto de ingresos y BPA a 3 años de cada comparable | B, tabla de comparables | Normalizador sobre cada comparable (SEC) | Apartado 14 (A5) |
| R11 | **Múltiplos frente a su propia historia**: PER y EV/EBITDA de los 5 últimos ejercicios frente a su media | A, valoración («múltiplos medios de 5 años») | Precio al cierre de cada ejercicio (yfinance) y cifras de la SEC | Apartado 10; método candidato para el motor (no depende de los comparables) |

## Encajan en la fase B (contenido completo y motor de valoración)

| # | Propuesta | Visto en | Fuente y cálculo | Encaje |
|---|---|---|---|---|
| R12 | **Página de datos clave**: cuenta de resultados, flujo de caja y balance resumidos con estimaciones; tabla de crecimientos (ventas, EBITDA, EBIT, BPA, DPA); márgenes, rentabilidades y **ROCE / WACC** | A, página 2 | Proyección de los tres estados (hoy solo hasta el BPA) | B1 y B6 |
| R13 | **EV con ajustes institucionales**: déficit de pensiones y arrendamientos | A, página 2 | XBRL (`DefinedBenefitPlanFundedStatusOfPlan`, `OperatingLeaseLiability`) | Múltiplos y DCF (*al final*) |
| R14 | **Suma de partes por segmento** (EV de cada segmento por múltiplo) | A, valoración; B (suma de partes por valor actual neto) | Segmentos (A1) + múltiplos por segmento | B1 |
| R15 | **Valoración de empresas sin beneficios**: valor actual neto de las ventas pico por producto, sin valor terminal, más la caja neta | B, valoración | Supuestos del analista y del motor | B1; hoy IOVA sale «Pendiente» |
| R16 | **Estimaciones anterior / nueva** al revisar una versión | A, portada | Versiones (la comparación ya existe) | A11 y B9 |
| R17 | **Historial de recomendación y precio objetivo** (gráfico de 3 años) | A y B, avisos legales | Versiones emitidas | Aviso legal |
| R18 | **Más datos de mercado**: valor contable por acción, capital flotante (`dei:EntityPublicFloat`) y volumen medio en acciones | B, portada | SEC y yfinance | Portada (*al final*) |

## No se proponen

- **Consenso frente a nuestras estimaciones y sorpresas frente al consenso** (A y B): son fuentes externas, que solo están aprobadas para opciones y posiciones en corto.
- **Encuestas propias y marcos sectoriales** (A): requieren el juicio del analista.

## Qué existe ya en los repositorios base (evaluación del 2026-10-12)

Revisión de los 13 repos:
- **9 repos inventariados:** consulta del [inventario](inventario/README.md), que cuenta como análisis completo.
- **FinRobot:** sus 938 archivos de código, *skills* y documentación.
- **ai-hedge-fund:** sus 135 archivos.
- **vectorbt y Lean:** no aportan nada a R1-R18 (son motores de *backtesting* y *trading*).

Grado de reutilización:
- **Listo para adaptar:** existe código determinista con licencia libre que resuelve casi todo.
- **Parcial:** hay piezas o un patrón; el resto se construye.
- **De cero:** no existe en ningún repo, o solo como texto para un modelo de lenguaje.

| # | Grado | Qué hay y dónde |
|---|---|---|
| R1 | Parcial (idea) | FinRobot Equity `major_takeaways_agent` y `investment_overview_agent` los redactan con IA (descartados: IA mínima). Idea útil: financial-research-analyst-agent `generate_smart_observations` (respaldo por reglas). Las reglas se construyen sobre nuestra analítica |
| R2 | De cero (trivial) | No hay código; solo texto en *skills* de FinRobot. Idea parcial: edgar_analytics, alerta por rachas de FCF trimestral negativo (`SUSTAINED_NEG_FCF_QUARTERS`). Una fórmula sobre el LTM ya calculado |
| R3 | Listo para adaptar | edgartools `TTMCalculator` ya deriva los trimestres (lo usa nuestro LTM) y `calculate_ttm_trend` da el crecimiento interanual; FinRobot `edgar_provider` valida 4 trimestres discretos (idea). La reacción a 5 sesiones toma como idea ai-hedge-fund `event_study` |
| R4 | De cero | Nada estructurado (la SEC no publica el pipeline clínico como datos); FinRobot *skill* `catalyst-calendar` solo describe el flujo. Tabla del analista |
| R5 | Parcial (idea) | FinRobot *skill* `initiating-coverage` («8-12 riesgos en 4 categorías»), FinRobot Equity `enhanced_text_generator` (categorías, con IA), equity-research-agent `POLICY_AGENT_PROMPT` (escala alto/medio/bajo). Ninguno clasifica por código |
| R6 | De cero (trivial) | FinRobot Equity `html_renderer` tiene campos de autor (idea). **Decisión del usuario: los datos de autoría los introduce cada persona en el SaaS** |
| R7 | Parcial | FinRobot `valuation_synthesis.verdict_from_upside` (bandas asimétricas por confianza, idea); el texto se construye con nuestros umbrales |
| R8 | Listo para adaptar | FinRobot `valuation_synthesis.synthesize_valuations` (media ponderada por confianza, determinista) y `valuation_aggregator` (rangos por método, *football field*); FinRobot Equity `generate_football_field_data` (idea). Apache-2.0 |
| R9 | Hecho en su mayor parte (propio) | Los precios de los escenarios ya existen. FinRobot `sotp_scenario` se ancla al consenso (externo: no). Solo falta la frase editable del analista |
| R10 | Parcial | edgar_analytics `analyze(peers=...)` (crecimiento de ingresos; no instalado), financial-research-analyst-agent `compare_peers` (Yahoo: no). Nuestro normalizador ya da 5 años de cada comparable |
| R11 | Listo para adaptar | FinRobot `primitives/historical_valuation.compute_historical_band`: bandas históricas de EV/EBITDA y P/FCF (actual, P25, mediana, P75, P90 y serie temporal), puro y Apache-2.0. Más financial-research-analyst-agent `compute_historical_context` (PER frente a su media de 5 años, idea) |
| R12 | De cero (proyección) / trivial (ROCE / WACC) | La proyección de los tres estados no existe en ningún repo (necesidad sin resolver n.º 1); la *skill* de FinRobot solo la describe. ROCE y WACC ya se calculan |
| R13 | Parcial | FinRobot `multiples.calculate_ev` (preferentes y minoritarios) y `audit/ev_bridge` (avisa de componentes no declarados); edgar_analytics incluye arrendamientos en su deuda neta. Pensiones: nada |
| R14 | Parcial (alto) | FinRobot `sotp.compute_sotp_breakdown` (suelo por segmentos × múltiplo − DFN, puro) y `edgar_provider.extract_segment_facts` (segmentos ASC 280 del 10-K con ingresos y beneficio bruto u operativo). **También sirve de base para A1 (segmentos)**; no valida que sumen el total ni cubre producto y geografía |
| R15 | De cero | No hay valoración de compañías sin beneficios (VAN ajustado por probabilidad) en ningún repo; pendiente de los documentos del usuario (motor de valoración) |
| R16 | Listo para adaptar | FinRobot `artifact/semantic_diff.build_semantic_delta`: diferencias entre versiones con atribución por re-valoración de cada supuesto, sin IA. Más nuestra `almacenamiento/versiones.comparar` |
| R17 | Parcial | FinRobot `signal.compute_signal` y `aggregations/hit_rate_overview` (acierto de las recomendaciones por versión). El gráfico se construye con nuestras versiones emitidas |
| R18 | Listo (SEC) | edgar_analytics `PerShareMetrics.book_value_per_share`, FinRobot `primitives/book_value` (valor contable por acción con varias clases de acciones), edgartools `Company.public_float` |
