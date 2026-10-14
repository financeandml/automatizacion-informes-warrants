# Hoja de ruta: de borrador por CLI a SaaS

Estado a 2026-10-14. Recoge todo lo que falta, también lo apuntado en el «Registro de tareas por terminar» del usuario, incluidas las tareas pendientes de [requisitos-pendientes.md](requisitos-pendientes.md) y [rigor-del-contenido.md](rigor-del-contenido.md). Cada tarea termina con tests, documentación, commit y, si cambia el PDF, un PDF intermedio para revisión.

Las ideas de los informes de referencia (R1-R18) están en [propuestas-referencias.md](propuestas-referencias.md). **No se implementan sin valoración del usuario.** En la tabla figuran como «propuesta R…».

**Empresas de prueba:** IOVA, ORCL y NFLX (más AAPL, que es la referencia de los tests).

## Cerrado al 100 %

- ~~Carencias 1-3 y 5-8 del contenido~~: LTM, escenarios, DCF inverso, proyección hasta el BPA, comparables con aviso, remuneración en acciones como coste, gobierno, puntuaciones, cambios del Item 1A, notas y anexo de metodología.
- ~~Comparables automáticos orientativos~~: aviso antes de emitir, sin bloquear la emisión y sin texto interno en el informe.
- ~~Proyecto ordenado para recién llegados~~: índices de la documentación y de los módulos, README.
- ~~Normalizador con las empresas de prueba~~ (2026-10-12):
  - BAI declarado por componentes (ORCL).
  - Ajuste de acciones y BPA por desdoblamientos (NFLX 10:1 en 2025).
- ~~Bloque R: propuestas aprobadas R2-R4, R6-R14, R16-R18~~ (2026-10-12): plan y reutilización en la tabla de abajo; tests en `tests/test_bloque_r.py` y `tests/test_red.py`.
- ~~Errores de datos encontrados al integrar el bloque R~~ (2026-10-12), corregidos en el normalizador y con test:
  - ORCL: deuda a largo plazo como `LongTermNotesAndLoans` y, en los 10-Q, `NotesPayableCurrent`. Antes faltaban unos 120.000 M USD de deuda y salía con caja neta.
  - ORCL: el BAI de los 10-Q es resultado + impuesto; una suma incompleta ya no impide usar una derivada.
  - IOVA declara las acciones medias en miles desde 2019: se detecta con beneficio neto / BPA del mismo filing (×1.000).
  - XOM: el LTM usa las acciones básicas cuando no declara diluidas.
  - KO y XOM: si la API companyfacts aún no tiene el último 10-Q, se usa el trimestre anterior y no el anual.
  - Aviso nuevo de calidad: intereses / deuda > 20 % indica que falta deuda. Deuda neta / EBITDA = n.s. con EBITDA ≤ 0.
  - ORCL FY2026 tuvo tres primeros ejecutivos: el informe ya no atribuye a «el primer ejecutivo» la retribución de uno solo (2026-10-13).
- ~~Decisiones del usuario F2-F4~~:
  - Parámetros del fondo: los pone el analista.
  - Fuentes externas: solo para opciones y posiciones en corto.
  - Apartado 21: resultados de la empresa.

## Bloque R: propuestas aprobadas (2026-10-12) · cerrado

Orden de desarrollo y por qué: primero los datos que usan los demás, luego la valoración, después las proyecciones y por último las versiones. Cada paso queda integrado en el PDF, probado y documentado antes del siguiente.

| Paso | Propuesta | Plan | Reutiliza |
|---|---|---|---|
| R13 | EV con ajustes | Partidas nuevas en el normalizador: preferentes, pensiones (pasivo neto), arrendamientos financieros (solo si la deuda declarada no los incluye) y patrimonio temporal. EV y valor del patrimonio del DCF y de los comparables con esos ajustes; tabla del puente del EV. Los arrendamientos operativos **no** entran: en US GAAP su coste ya está dentro del EBITDA | FinRobot `multiples.calculate_ev`, `audit/ev_bridge` |
| R18 | Más datos de mercado | Valor contable por acción, capital flotante (dei, con fecha), volumen medio en acciones; cotización de 12 meses sin ajustar por dividendos | edgartools `public_float`, edgar_analytics `book_value_per_share` |
| R2 | Autonomía de caja y dilución | (Caja + inversiones a corto) / consumo de caja de los últimos 12 meses, solo si el FCF es negativo; variación anual de las acciones | — (fórmula sobre datos ya calculados) |
| R3 | Últimos 8 trimestres | Trimestres de ingresos, EBIT, beneficio y BPA (BN / acciones del trimestre) con variación interanual | edgartools `TTMCalculator.quarterize` |
| R11 | Múltiplos históricos | Bandas de PER, EV/EBITDA y P/FCF de 5 años (mediana, P25, P75, P90, actual), con las acciones de cada ejercicio, el dato disponible solo desde la presentación del 10-K (sin sesgo de anticipación) y precios sin ajustar por dividendos; gráfico | FinRobot `primitives/historical_valuation` |
| R14 | Segmentos y suma de partes | Desgloses de negocio, producto y geografía (5 años) validados (suman el total, sin subtotales); resultado operativo por segmento y costes no asignados; suma de partes con múltiplo por segmento (por defecto, mediana EV/EBIT de los comparables del analista; editable) | FinRobot `extract_segment_facts`, `sotp.compute_sotp_breakdown` |
| R8 + R9 | Derivación del precio objetivo y rangos | Síntesis ponderada de los métodos disponibles (pesos editables y renormalizados); tabla método · valor · rango · supuesto · peso; gráfico de rangos (*football field*); rango pesimista-optimista en la portada y desencadenante editable por escenario (por defecto, sus supuestos) | FinRobot `valuation_synthesis`, `valuation_aggregator` |
| R10 | Comparables con crecimiento | Crecimiento anual compuesto de ventas y BPA a 3 años de cada comparable con el normalizador | — (normalizador) |
| R7 | Sistema de recomendación | Definiciones en el anexo B a partir de los umbrales del código | FinRobot `verdict_from_upside` (idea) |
| R12 | Proyección del balance y del flujo de caja | Flujo operativo, capex, FCF tras SBC, dividendos, recompras y variación de caja; balance resumido (caja, activos operativos netos, deuda, patrimonio, DFN) que cuadra por construcción; dos gráficos con el estilo del informe y solo datos del propio informe | — (no existía) |
| R16 | Estimaciones anterior / nueva | Resumen de cada informe (JSON); comparación con el anterior y atribución del cambio del precio objetivo a cada grupo de supuestos (re-valoración de uno en uno) | FinRobot `artifact/semantic_diff` |
| R17 | Historial de recomendación | Desde las versiones emitidas: recomendación, precio objetivo y señal (acertada, en curso, fallida); gráfico | FinRobot `signal.compute_signal` |
| R4 | Pipeline (biotecnología y farmacia) | Campo del analista que solo aparece en esos sectores | — |
| R6 | Autoría | Campos que rellena cada usuario (nombre, correo, teléfono; empresa y contacto) guardados fuera del repositorio; en la portada si están rellenos | — |

## Tareas pendientes fuera de las fases

| # | Tarea | Cuándo |
|---|---|---|
| P1 | R1: hechos clave con etiqueta temática (A2) | Aparcada hasta terminar el SaaS |
| P2 | R5: taxonomía de riesgos para la clasificación del apartado 20 (A7) | Aparcada hasta terminar el SaaS |
| P3 | R15: valoración de empresas sin beneficios | En espera de los documentos del usuario (con B1) |
| P4 | Emisores extranjeros (20-F/40-F) en el PDF (antigua A10). Auditoría del 2026-10-13: faltan las listas IFRS (`ifrs-full`) en el normalizador (reutilizar edgar_analytics `synonyms.py` y `SynonymGroups` de edgartools), sin LTM trimestral (no hay 10-Q), sin Form 4 ni DEF 14A (Item 6 del 20-F); cifras a USD con `ingesta/divisas.py` y textos de `TwentyF` | Aparcada por el usuario |
| P5 | Ajuste de partidas no recurrentes del analista (`informe/bloque_fijo.py`): definido y probado, pero sin conectar al informe ni a la interfaz | Pendiente (revisión del 2026-10-14) |
| P6 | Apartado 1 (ficha): bolsa de cotización, cierre del ejercicio fiscal y empleados (edgartools `Company`) | Pendiente |
| P7 | Apartado 6: fechas de dividendos en el calendario | Pendiente |
| P8 | Apartado 22 (tesis consolidada): plantilla que ate cada asunción del analista a una cifra del modelo | Pendiente |
| P9 | Apartado 25: comparación automática de lo real frente a lo estimado con cada 10-Q nuevo | Pendiente |
| P10 | Apartado 26: fuentes externas (yfinance, FINRA) con su fecha en el anexo de documentos | Pendiente |
| P11 | Apartado 18: tenedores institucionales desde los 13F de la SEC (trazable), en lugar de yfinance | Pendiente |
| P12 | Apartados 15-17: sesgo, movimiento implícito, estructura temporal de la volatilidad y coste de cobertura; foto diaria de la volatilidad implícita para su ranking histórico; volumen de *dark pool* de FINRA (semanal, gratis, con 2-4 semanas de retraso) | Pendiente de decidir |
| P13 | Batería de regresión con 15-20 empresas de sectores distintos (hoy 14: 10 generales y 4 sectoriales) | Pendiente |
| P14 | Restos de la B2: segmentos y trimestres en los perfiles sectoriales, bandas históricas de P/BV y P/TBV, criterios del fondo propios del sector (hoy EV/EBITDA sale «sin dato») y nombres con mayúsculas internas («Jpmorgan») | Pendiente |
| P15 | Apartado 13: citas literales del 10-K cuando la empresa cifra su mercado, como apoyo al analista | Pendiente |
| P16 | Apartado 20: matriz probabilidad × impacto de los riesgos (del analista) | Pendiente |
| P17 | SPAC, ETF y fondos abiertos: hoy «plantilla pendiente de validar»; decidir si entran en el SaaS | Pendiente de decidir |
| P18 | Apartado 5: fecha de alta (Form 3) de directivos con más de 120 formularios de antigüedad (p. ej. Tim Cook) | Pendiente |

Descartados por decisión del usuario (fuentes externas solo para opciones y cortos, F3): consenso de analistas, sorpresas de BPA frente al consenso, ClinicalTrials.gov y el coste de préstamo de las acciones (de pago).

## Fase A: primer uso real (un analista, en su ordenador)

**Estado (2026-10-13): cerrada.** Lo único abierto de la fase está fuera de ella: P2 (antigua A7), P4 (antigua A10) y la decisión F7 (LTM por segmento, provisional).

**Decisiones del usuario para cerrar la fase A (2026-10-13):** orden A14 → A1-bis (F7 provisional) → A15 → A3 → A9 → A6 → A8 → A5 → A4 → A2 → PDF de revisión → A11 → A12 + A13. Todo sin alucinaciones (cifras por código y validadas; si no cuadran, no se muestran).
- A2: 4 hechos por reglas sin etiqueta temática (patrón FRAA `insight_engine`); R1 se valorará después (P1).
- A4: el calendario lo introduce preferentemente el analista; el SaaS prepara un borrador por empresa marcado «Revisar».
- A5: tercer bloque de IA: localizar el apartado «Competition» del Item 1, extraerlo y traducirlo al español salvo los nombres de los competidores.
- A6: lógica de FRAA `insider_activity` (actividad neta, compras agrupadas) sobre los Form 4 de la SEC; participación de *insiders* e institucional de yfinance, etiquetada como fuente externa no auditada (excepción aprobada).
- A11: reutilizar `almacenamiento/` tal cual. A13: la autoría se gestiona solo dentro del SaaS.

Objetivo: que el analista genere, complete, emita (PDF descargable) y versione informes reales de cualquier empresa operativa de EEUU desde una interfaz.

| # | Tarea | Decisiones del usuario y detalle | Estado |
|---|---|---|---|
| ~~A1~~ | ~~Segmentos y geografía~~ | Hecho con R14: los tres desgloses de 5 años, solo los ejercicios que suman el total. LTM por segmento provisional (A1-bis, decisión F7 abierta) | Cerrado |
| ~~A2~~ | ~~Apartado 2: resumen ejecutivo~~ | 4 hechos clave por reglas, uno por tema, sin etiqueta (`calculo/hechos_clave.py`, patrón FRAA `insight_engine`); R1 en P1 | Cerrado (2026-10-13) |
| ~~A3~~ | ~~Apartado 3: qué hace la empresa~~ | Segmentos (A1, con LTM provisional F7) y concentración de clientes declarada (`ConcentrationRiskPercentage1`) | Cerrado (2026-10-13) |
| ~~A4~~ | ~~Apartado 6: catalizadores~~ | Bloque de IA del MD&A conectado; calendario en borrador «Revisar» (resultados y junta + 52 semanas, plazo legal según la categoría de presentador, vencimientos), siempre posterior a la emisión; hechos relevantes del 8-K de 12 meses. El analista lo sustituye con `Estimaciones.calendario` (en la interfaz, A12); aviso antes de emitir mientras sea borrador | Cerrado (2026-10-13) |
| ~~A5~~ | ~~Apartado 14: competencia~~ | Apartado «Competition» extraído por código y traducido por el tercer bloque de IA con verificación (cifras, nombres propios, longitud); cuotas de ingresos, ROIC − WACC y estabilidad del margen frente a los comparables del analista | Cerrado (2026-10-13) |
| ~~A6~~ | ~~Apartado 18: insiders y accionistas~~ | Form 4 de 12 meses (P/S en mercado, plan 10b5-1; retribución y retenciones aparte) con la lógica de FRAA `insider_activity`; >5 % del proxy y 13D/13G; participaciones de yfinance etiquetadas como externas | Cerrado (2026-10-13) |
| ~~A7~~ | ~~Apartado 20: clasificación de riesgos~~ | Sacada de la fase A a P2 (decisión del usuario, 2026-10-13). Hecho: autonomía de caja y dilución (R2) | En P2 |
| ~~A8~~ | ~~Apartado 21: historial de resultados~~ | Publicaciones (8-K 2.02) con su trimestre y la reacción a 5 sesiones según la hora de presentación; alarmas SEC de 5 años; tabla de 8 trimestres (R3) | Cerrado (2026-10-13) |
| ~~A9~~ | ~~Gráficos pendientes~~ | Cascada EBITDA → FCF (cuadra con el flujo operativo declarado) y vencimientos de deuda (solo si cuadran con la deuda declarada) | Cerrado (2026-10-13) |
| ~~A10~~ | ~~Emisores extranjeros en el PDF~~ | Aparcada en P4 (decisión del usuario, 2026-10-13) | En P4 |
| ~~A11~~ | ~~Versiones conectadas al informe~~ | `informe/versionado.py` sobre `almacenamiento/` tal cual: `versiones detectar/preparar/confirmar/emitir`; cada versión guarda textos, estimaciones, resumen (R16), instantánea de la SEC, avisos, calidad y su PDF; lo del analista se hereda y prevalece. La calidad en rojo bloquea la emisión | Cerrado (2026-10-13) |
| ~~A12~~ | ~~Interfaz Streamlit (un analista, en su ordenador)~~ | `informes-warrants interfaz` (`ui/`): empresas y versiones; editor con textos en Markdown, estimaciones, escenarios, calendario y catalizadores, vista previa del informe al lado (sin volver a la SEC al editar); avisos antes de emitir, botón «Confirmar emisión del informe» y descarga del PDF. Estructura de FRAA `frontend` (MIT) | Cerrado (2026-10-13) |
| ~~A13~~ | ~~Autoría~~ | Pantalla «Configuración» de la interfaz (interna; datos fuera del repositorio) sobre `autoria.py` | Cerrado (2026-10-13) |
| ~~A14~~ | ~~Batería de regresión~~ | `informes-warrants regresion` sobre las 10 empresas de prueba (`tests/fixtures/regresion`): compara solo cifras de la SEC; aviso de calidad si la deuda a corto suma papel comercial y préstamos a corto | Cerrado (2026-10-13) |
| ~~A15~~ | ~~Pulido del PDF~~ | Nombres de la SEC legibles (`ingesta/nombres.py`) y leyenda de «n.s.» en la portada | Cerrado (2026-10-13) |

## Fase B: perfeccionar el contenido y la valoración

**Decisiones del usuario (2026-10-14):** se emite aunque queden apartados pendientes (avisos; edición posterior = revisión nueva); borrador de la IA en cada apartado del analista; autoría en la portada; A6 sin *smart money score*; B1 (motor de valoración) retomada con los documentos del usuario y hecha el 2026-10-15.

| # | Tarea | Detalle | Estado |
|---|---|---|---|
| B1 | Motor de valoración | Documentos del usuario recibidos el 2026-10-14 en `Motor de valoración/` (plantillas de rareliquid: DCF simple y avanzado por segmentos, LBO, *accretion/dilution*, comparables y los tres estados; no se publican). Incluye el PEG (apartado 10). Observación de la regresión: con los supuestos por defecto (Rf 5,2 % de FRED, prima 5,5 %, medias históricas) el DCF queda muy por debajo de la cotización en casi todas las empresas (AAPL −62 %, MSFT −44 %, TSLA −98 %); el motor debe revisar estos supuestos por defecto. Ya hechos: derivación ponderada (R8), múltiplos históricos (R11), proyección de flujo y balance (R12) y suma de partes (R14). Faltan DDM, ingreso residual y R15 (P3) | ✅ Hecho (2026-10-15): libro de Excel descargable con las plantillas (general y sectorial), correcciones E1-E31, entradas del analista en la interfaz, cada versión guarda su libro, `informes-warrants modelo` y segunda vía con LibreOffice (14 empresas de prueba sin discrepancias). Detalle y limitaciones en [motor-valoracion.md](motor-valoracion.md) §8. Siguen pendientes DDM, ingreso residual y R15 (P3) |
| ~~B2~~ | ~~Plantillas sectoriales en PDF~~ | `informe/sectorial.py` + `plantillas/informe/informe_sectorial.html.j2`: misma maquetación y apartados 01-06 con las piezas compartidas de la plantilla general (`_inicio`, `_recomendacion`, `_mercado`, `_bolsa_autoria`, `_gestion`, `_competencia`, `_gobierno`, `_riesgos`, `_cambios`, `_sistema_historial`; el HTML general no cambia). `construir`, `render`, la interfaz, las versiones y la regresión eligen solos la plantilla por la cobertura. Cifras del perfil en 5 ejercicios + LTM con trazabilidad; valoración en `calculo/valoracion_sectorial.py`: valor contable justificado de Gordon (banca P/TBV con el ROTE; seguros P/BV con el ROE; BDC P/NAV con el ROE total), descuento de dividendos (REIT y BDC) y comparables del analista (P/TBV, P/BV, P/FFO, P/NAV); sin EBITDA, EV ni DCF. ROE sostenible = media de los ejercicios (no el año pico) o el del analista; cifras de los accionistas ordinarios (sin preferentes); FFO como NAREIT (+ deterioros − ventas); BDC con g = 0 por defecto. Probado con JPM, TRV, O y ARCC (también en la regresión). De paso se corrigió un falso positivo de las alarmas de control interno (TRV: «no material weaknesses»). Pendiente: segmentos y trimestres en estos perfiles y bandas históricas de P/BV | Cerrado (2026-10-14) |
| ~~B3~~ | ~~Apartados 4 y 5~~ | Filiales del Exhibit 21 (`TenK.subsidiaries`); equipo: quien presenta Form 4 (cargo declarado), alta como insider (Form 3) y rentabilidad de la acción desde entonces; cambios de la dirección (8-K 5.02). La trayectoria y la independencia siguen siendo del analista | Cerrado (2026-10-14) |
| ~~B4~~ | ~~Apartados 12 y 23-25~~ | Parámetros del fondo (Configuración, internos) → criterios cumple/no cumple, stop por volatilidad, tamaño por riesgo, VaR/CVaR (FRAA), días de liquidez y prueba histórica del stop con cotizaciones propias (sin vectorbt); checklist cualitativo y criterios de salida del analista; seguimiento con el calendario. Sin parámetros, aviso interno y sin sección | Cerrado (2026-10-14) |
| ~~B5~~ | ~~Apartados 15-17 y 19~~ | Opciones (put/call, volatilidad implícita frente a la realizada, max pain, actividad inusual) y posiciones cortas de yfinance, etiquetadas como externas no auditadas; cálculos de FRAA `options_analyzer` (MIT) sin sus señales. Pendiente de una fuente de pago: *sweeps*, *dark pool* y el ranking histórico de volatilidad implícita | Cerrado (2026-10-14) |
| B6 | Índice A-I como tabla de contenidos y numeración del PDF | Decisión del usuario (2026-10-14): se mantiene el formato y todo lo demás; solo cambia la enumeración | Después de la B1 |
| ~~B7~~ | ~~Cambios sobre lo «hecho»~~ | DuPont en 3 y 5 factores (`analitica.dupont`, fórmulas de edgar_analytics `DuPontDecomposition`, MIT) en la sección 04 (R9, R13 y R18 ya hechos) | Cerrado (2026-10-14) |
| ~~B8~~ | ~~Historial de nuestras recomendaciones en el apartado 21~~ | Descartado: el apartado 21 es de la empresa. El historial de recomendaciones como aviso legal es la propuesta R17 | Descartado |
| ~~B9~~ | ~~Comparación entre versiones en la interfaz~~ | «Empresas y versiones» → «Comparar versiones»: recomendación, datos clave, atribución del cambio del valor DCF (R16), estimaciones y diferencias de textos; reutiliza `almacenamiento/versiones.comparar` y `cambios.comparar` | Cerrado (2026-10-14) |

## Fase C: lanzamiento del SaaS

| # | Tarea | Detalle |
|---|---|---|
| C1 | Sustituir vectorbt | Commons Clause: prohíbe venderlo. Revisión del 2026-10-14: no se llegó a usar (la B4 se hizo con cotizaciones propias); queda comprobarlo y cerrarla |
| C2 | Usuarios y permisos | Autenticación, roles (analista, revisor), varias empresas cubiertas por usuario |
| C3 | Despliegue | Servidor, base de datos gestionada, copias de seguridad, cachés de la SEC y del mercado |
| C4 | Avisos automáticos | Nuevo 10-Q/10-K → versión detectada → aviso al analista |
| C5 | Rendimiento | Caché de companyfacts y de comparables; generación en segundo plano |
| C6 | Migración a edgartools 6 | Fijado en `<6`: la 6.0 cambia la API |
| C7 | Legal y licencias | Revisión legal del aviso (el sistema de recomendación R7 ya está en el anexo B), atribuciones (MIT/Apache) y licencias de datos |
| C8 | Observabilidad | Registro de errores, tiempos y uso del modelo de lenguaje |
| C9 | Facturación y planes | Propuesta nueva (2026-10-14), a valorar: suscripciones y límites por plan |
| C10 | Manual del usuario | Propuesta nueva (2026-10-14), a valorar: guía del analista dentro del SaaS |
