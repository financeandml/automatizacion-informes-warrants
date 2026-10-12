# FinRobot (AI4Finance Foundation)

- **Zip:** `FinRobot-master.zip` (añadido el 2026-10-11; 1.235 archivos, 45 MB descomprimido).
- **Licencia:** Apache-2.0, en la raíz y en `finrobot_desktop/`. Se puede copiar conservando el aviso y señalando los cambios.
- **Cobertura de esta ficha** (2026-10-12):
  - Listado del 100 % de los archivos.
  - Lectura completa de los operadores de valoración de `finrobot_desktop/finrobot/engine/compute/operators/` (`dcf.py`, `multiples.py`, `peer_screen.py`, `forward_estimates.py`).
  - Lectura dirigida de `finrobot_equity/core/src/modules/` (`valuation_engine.py`, `sensitivity_analyzer.py`, `financial_data_processor.py`).
  - Muestreo del resto: tests, interfaz de escritorio, skills.

## Estructura

| Carpeta | Archivos | Qué es |
|---|---:|---|
| `finrobot_desktop/finrobot/engine/` | 133 `.py` | **V2.** Motor de cálculo determinista con trazabilidad numérica: `compute/operators/` (DCF, WACC, múltiplos, comparables, DDM, LBO, SOTP, ingreso residual, Monte Carlo, agregador de valoración) y `compute/operators/audit/` (puente del EV, periodo TTM, coherencia narrativa-cifras). También `data/` (proveedores EDGAR, yfinance, FMP, Finnhub) y `pipelines/` (dcf, comps, equity_research, ic_memo) |
| `finrobot_desktop/desktop`, `tests`, `skills`, `scripts` | ~800 | Aplicación Tauri, tests y skills de agentes |
| `finrobot_equity/core/src/` | 33 `.py` | **V1.** Generador web de informes HTML/PDF: `valuation_engine.py` (EV/EBITDA, comparables, DCF, datos de *football field*), `sensitivity_analyzer.py` (crecimiento × margen), `financial_data_processor.py` (BPA proyectado proporcional a ventas y margen: heurístico), agentes de texto por sección |
| `finrobot_autogen/` | 52 `.py` | **V0.** Librería AutoGen educativa (agentes, RAG, *toolkits*) |

## Qué se reutiliza

| Necesidad | Ruta y símbolo | Modo | Notas |
|---|---|---|---|
| DCF inverso: crecimiento implícito | `engine/compute/operators/dcf.py` `solve_for_implied_growth`, `_price_for`, `ReverseSolveReason` | Copiar con atribución (Apache-2.0), adaptado | Bisección en un intervalo; precio monótono en g; devuelve un código cuando no hay solución (`TARGET_ABOVE_RANGE`/`BELOW`) y señala la falta de convergencia |
| DCF inverso: WACC implícito | `dcf.py` `solve_for_implied_wacc` | Copiar con atribución | Precio decreciente en el WACC; acota el intervalo por encima de g |
| Flujo terminal normalizado | `dcf.py` `_terminal_fcf` | Copiar con atribución | En perpetuidad, capex = min(D&A, capex) × (1 + g): no capitaliza el capex de la fase de crecimiento. Rechaza el valor terminal si el flujo es ≤ 0 (BUG-074) |
| Mediana de comparables | `multiples.py` `PEER_PE_NM_CAP` = 75, `PEER_EV_EBITDA_NM_CAP` = 50, `_sanity`, `calculate_peer_statistics` | Copiar las reglas | El comparable sigue en la tabla, pero su múltiplo «no significativo» queda fuera de la mediana. Rechaza NaN e infinitos |
| Filtro de comparables | `peer_screen.py` `_is_non_common_listing` (preferentes, *warrants*, cupón en el nombre), `_same_issuer` (doble clase) | Idea | Nosotros quitamos los duplicados por CIK, que es exacto |
| Sensibilidad crecimiento × margen | `finrobot_equity/.../sensitivity_analyzer.py` `generate_sensitivity_table` | Idea | Segunda tabla de sensibilidad |
| *Football field* | `finrobot_equity/.../valuation_engine.py` `generate_football_field_data`; `valuation_aggregator.py` | Idea | Hecho: gráfico de rangos por método (`visual/graficos.rangos_valoracion`) |
| Segmentos | `engine/compute/coordinators/segment_extractor.py` `extract_segment_facts` | Idea | Hecho a nuestra manera: validación con los dominios declarados (`domains_by_role` de edgartools) y el total consolidado (`calculo/normalizador.segmentos`) |
| Múltiplos históricos | `engine/compute/primitives/historical_valuation.py` `compute_historical_band`, `_quantile` | Copiar con atribución, corregido | Acciones de cada ejercicio y dato disponible desde la presentación del 10-K (`calculo/historico.py`) |
| Síntesis del precio objetivo | `engine/compute/operators/valuation_synthesis.py` `synthesize_valuations` | Patrón | Pesos del analista renormalizados (`calculo/sintesis.py`) |
| Suma de partes | `engine/compute/operators/sotp.py` `value_segment`, `compute_sotp_breakdown` | Patrón | Con costes no asignados (`valoracion_relativa.suma_de_partes`) |
| Cambios entre versiones | `artifact/semantic_diff.py` `build_semantic_delta` | Patrón | Atribución secuencial que cuadra con el total (`dcf.atribucion_secuencial`) |
| Señal de la recomendación | `engine/compute/operators/signal.py` `compute_signal` | Reglas con atribución | Horizonte de 12 meses (`calculo/historial.py`) |
| EV con ajustes | `multiples.py` `calculate_ev`; `audit/ev_bridge` | Idea | Preferentes, pensiones, patrimonio temporal y arrendamientos financieros (`metricas.componentes_ev`) |
| Auditoría del TTM | `engine/compute/operators/audit/ttm_period.py` | Idea | Contraste del periodo LTM |

## Qué no se usa

- **`forward_estimates.py`:** el BPA adelantado sale del consenso de FMP o de Yahoo (externo). Nuestra proyección se construye línea a línea desde las estimaciones del analista.
- **El BPA proyectado de `finrobot_equity`:** lo hace crecer en proporción a ventas × margen, sin intereses, impuestos ni acciones.
