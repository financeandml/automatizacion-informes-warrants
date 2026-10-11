# Plan de desarrollo

SaaS que, a partir de un ticker de EEUU, genera un informe borrador con datos oficiales de la SEC. El analista lo revisa, completa la tesis y lo versiona cada trimestre.

Contenido del informe: [estructura-informe.md](estructura-informe.md). Código reutilizable: [repositorios-base.md](repositorios-base.md).

## Arquitectura en 4 capas

```
ticker ─► [1 Ingesta] ─► [2 Cálculo] ─► [3 Visual] ─► informe borrador ─► [4 IA + analista] ─► versión aprobada
            SEC + precio   pandas/numpy   gráficos/tablas   HTML/PDF          10-K texto + editor     archivo
```

## Principios del plan maestro

1. **Determinismo:** las capas 1-3 no usan IA. La IA solo trabaja en la capa 4 y siempre la revisa un humano.
2. **Una sola plantilla HTML** para la vista previa y para el PDF: lo que ve el analista es exactamente lo que se descarga.
3. **Trazabilidad:** cada cifra del bloque fijo enlaza a su fuente (concepto XBRL, filing y fecha). Cada viñeta de la IA lleva la cita literal del 10-K.
4. **Versiones inmutables:** una versión aprobada no se modifica y guarda el *snapshot* de los datos con los que se generó.
5. **Reutilizar antes que construir:** antes de cualquier tarea se consulta el inventario completo de `repositorios-github/` ([inventario/README.md](inventario/README.md)) y se razona qué se reutiliza.

### Capa 1 — Ingesta de datos estructurados

Detalle y rutas exactas: [inventario/README.md](inventario/README.md).

| Necesidad | Reutilizar | Hay que construir |
|---|---|---|
| Estados financieros de 5 años + 3 estimados (XBRL) | edgartools `XBRLS.from_filings(...)` (cosido multiperiodo) o `Company.income_statement(periods=5)`; `RenderedStatement.to_dict()` para tablas. `get_financials()` solo da 3 años de P&L y 2 de balance | — |
| TTM y ajuste por *splits* | edgartools `ttm/` (`TTMCalculator`, `detect_splits`). **No** usar `compute_ttm` de edgar_analytics (no suma 12 meses consecutivos) | — |
| Precio actual, acciones y market cap | edgar_analytics `market_data` (`get_share_price`, `get_market_cap`, yfinance) | — |
| Histórico de precios (máx./medio/mín. 12m, volumen, base 100, beta) | financial-research-analyst-agent `src/data/provider.py` (`MarketDataProvider.get_history`, `MultiProvider` con respaldo `AlphaVantageProvider`) | — |
| Texto del 10-K (Items 1, 1A, 7) | edgartools `TenK.business`, `.risk_factors`, `.management_discussion` (en 6.x: `report.get('Item 7')`) | — |
| Perfil de vencimientos de deuda | edgartools: leer el concepto **bruto** `xbrl.facts.query().by_concept('LongTermDebtMaturitiesRepaymentsOfPrincipal', exact=False)`; la estandarización de `gaap_mappings.json` los agrega en `ShortTermDebt`/`LongTermDebt` y pierde el perfil | — |
| Trazabilidad de cada cifra | `FinancialFact` (EntityFacts) y `source_filing_index` (XBRLS) | Añadir `filing.accession_no` y `filing_date` a cada hecho (los facts de un `XBRL` no los traen) |
| Caché y *snapshot* | edgartools cachea HTTP (las *submissions* y *companyfacts* caducan a los 30 s) | *Snapshot* propio por informe (JSON de facts, `RenderedStatement.to_dict()`, `.txt` SGML); sin pickle (`Filing.save/load`) ni el `CacheLayer` de edgar_analytics. Cachés fuera de OneDrive (`EDGAR_LOCAL_DATA_DIR`) |
| Datos de referencia y sectores | edgartools `reference/` (tickers, `get_companies_by_industry`), `classify_business_category`, `Company.is_financial_institution()`, `sic_to_fama_french` | — |

### Capa 2 — Motor de cálculo determinista

| Métrica | Dónde está | Estado |
|---|---|---|
| Margen bruto, operativo y neto, ROE, ROA, deuda neta, DN/EBITDA, cobertura de intereses, D/E | edgar_analytics `metrics` | Reutilizar |
| ROIC (NOPAT / capital invertido), asset turnover, DuPont, Piotroski, Altman, Beneish, BPA, FCF por acción, ciclo de circulante | edgar_analytics `scores` | Reutilizar |
| CAGR | edgar_analytics `compute_cagr` (`financial_metrics.calc_cagr` de financial-research-analyst-agent está anidada y no se puede importar) | Reutilizar |
| PER, P/BV, EV/EBITDA, earnings yield | edgar_analytics `market_data.compute_valuation_ratios` | Contraste: no devuelve el EV y su base no coincide con su `Net Debt` |
| EV y su desglose (Anexo 3), EV/Ventas, EV/EBIT, FCF yield, P/FCF, rentabilidad por dividendo, pay-out, DPA, FCF conversion, ROCE | Piezas: stock-screener `src/data/storage.py` (`StockDatabase._calculate_fcf_yield`), financial-research-analyst-agent `src/tools/dividend_analyzer.py` (alimentado con DPA de XBRL, no con Yahoo) | **Construir** en `calculo/` |
| Definiciones de EBIT y EBITDA | edgar_analytics usa `EBITDA (standard)` = BN + intereses + impuestos + D&A (incluye no operativos) | **Construir**: EBIT = resultado operativo; EBITDA = EBIT + D&A, con *fallback* para los 101 emisores sin línea de D&A estandarizada |
| EBITDA ajustado publicado por la empresa | edgartools `edgar/earnings.py` (Adjusted EBITDA y `eps_reconciliation` del EX-99.1) | Reutilizar como contraste del EBITDA recurrente |
| DCF (WACC, sensibilidad) | financial-research-analyst-agent `dcf_model.py` solo como patrón: no resta la deuda neta, usa crecimientos de Yahoo, mete `inf` y emite recomendación | **Construir** como función pura sobre las estimaciones del analista (FCFF desde EBIT·(1−t)) |
| Comparables | edgartools `get_companies_by_industry(sic=..., sic_range=...)`; financial-research-analyst-agent `peer_comparison` como patrón | Filtro por tamaño con nuestro market cap |
| Comportamiento relativo (1m…5a, YTD vs SPY/QQQ/ETF sectorial) | financial-research-analyst-agent `performance_tracker.track_performance` (`SECTOR_ETFS`) | Mapeo SIC → ETF sectorial |
| Semáforo de calidad de datos antes de aprobar | stock-screener `src/data/quality.py` (`DataQualityChecker`) + edgartools `xbrl/validation.py` (`validate_balance_sheet`) | — |

Decisión (corregida tras el inventario completo): edgar_analytics se usa **como dependencia** para lo que calcula bien, pero la capa 2 necesita un **módulo propio de definiciones** (EBIT, EBITDA, DFN única, EV) y las métricas marcadas «Construir». Los tests se validan con los valores *golden* de AAPL del fixture de edgartools `tests/fixtures/xbrl/aapl/10k_2023` (`AAPL_METRICS`).

### Capa 3 — Motor visual y estructural

| Necesidad | Reutilizar | Construir |
|---|---|---|
| Gráficos | financial-research-analyst-agent `frontend/components/plotly_charts.py` + `utils/theme.get_plotly_layout` (adaptado a `#2B0B02`) | Cascada (*bridge* EBITDA → FCF), barras apiladas (mix), vencimientos de deuda, base 100; exportación SVG con `kaleido` (no existe en ningún repo con licencia) |
| Tablas HTML corporativas | edgartools `RenderedStatement.to_dict()` (sangría, totales, unidades); pandas `Styler` + Jinja2 | Formato español completo: piezas en edgartools `xbrl/core.format_value` (paréntesis) y `display/formatting.moneyfmt(sep='.', dp=',')` |
| Plantilla HTML | Patrón Jinja2 con herencia de edgartools `ownership/html_render.py` | Plantilla A4 con cabecera y pie, numeración (`@top-*`, `counter(page)`) y columna de ladillos: no existe en ningún repo |
| PDF | equity-research-agent `stock_analysis_agent/tools.py` `combine_reports` (WeasyPrint `HTML(...).write_pdf(..., stylesheets=[CSS])`). Ojo: genera el PDF desde `html_content` (sin `<head>` ni charset) en lugar de `html_full` | Aplicarlo a la plantilla Jinja2. WeasyPrint necesita GTK en Windows (documentarlo en el README) |

### Capa 4 — IA cualitativa y panel del analista

| Necesidad | Reutilizar | Construir |
|---|---|---|
| Configuración del LLM | financial-research-analyst-agent `src/config.py`: copiar **solo** `LLMSettings` (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_TEMPERATURE` = 0.1, `LLM_MAX_TOKENS` = 4096); el resto de sub-settings usa `Field(env=...)`, que Pydantic v2 ignora | Reducirlo a lo que usa este proyecto |
| Resumen de MD&A (catalizadores) y riesgos (Item 1A) | Texto de edgartools; patrón `key_risk`/`key_catalyst` de financial-research-analyst-agent `llm_insight_engine`. Las `edgar/ai/skills` son skills para agentes de desarrollo, no prompts del producto | Prompts propios: viñeta + cita literal del 10-K |
| Verificar que cada cita existe en el 10-K | mtcb `ExactMatchValidator`/`FuzzyMatchValidator` (Apache-2.0); edgartools `DocumentSearch.ranked_search` (BM25) | — |
| RAG, si el texto excede el contexto | edgartools `ChunkExtractor` + BM25; mtcb solo para elegir el *chunking*. No usar financial-research-analyst-agent `src/rag` (trunca a 200.000 caracteres y su filtro falla en silencio) | Solo si hace falta |
| Backend API | financial-research-analyst-agent `src/api` solo como patrón (19 rutas no se registran y varias devuelven datos fijos) | Endpoints propios si se necesitan |
| UI | **Streamlit en localhost**; financial-research-analyst-agent `frontend/` (`components/plotly_charts.py`, `utils/theme.py`, `frontend/.streamlit/config.toml`) como base | Dashboard + editor híbrido + vista previa (no existe en ningún repo) |

## Flujo al introducir un ticker

1. El analista escribe `AAPL` en el dashboard.
2. Estado «Extrayendo datos de la SEC…» → capa 1: último 10-K/10-Q, estados financieros y precio. Se guarda el *snapshot*.
3. Estado «Calculando métricas…» → capa 2.
4. Estado «Generando gráficos y tablas…» → capa 3.
5. Estado «Resumiendo el 10-K…» → capa 4 (IA): riesgos y catalizadores.
6. Estado «Listo para revisión» → editor híbrido.

## Editor híbrido y versiones

Definidos en detalle en [editor-y-versiones.md](editor-y-versiones.md). En resumen:

- **Bloques:** 18 AUTO (código), 4 PLANTILLA (texto con datos), 2 IA (riesgos y catalizadores, con cita literal) y 7 ANALISTA (marcados con `[[ANALISTA: …]]`; bloquean la emisión).
- **Izquierda, bloque fijo:** solo lectura, con la fuente de cada cifra. El analista solo puede ajustar los comparables y marcar partidas no recurrentes, siempre con motivo.
- **Derecha, bloque editable:** Markdown con las plantillas ya rellenas, las estimaciones (recalculan proyección y DCF) y la recomendación, que el SaaS propone y el analista confirma.
- **Vista previa en tiempo real:** HTML en cada cambio y PDF recompilado en segundo plano.
- **Emisión:** apartado «Confirmar emisión del informe»; la versión pasa a `emitida` y queda inmutable.
- **Versiones:** se detectan automáticamente con cada 10-Q/10-K (sin enmiendas) y el analista las confirma. Se nombran por año fiscal (`AAPL · FY2026 Q3 · v1`), heredan solo lo que aportó el analista y se guardan en SQLite fuera de OneDrive.

## Estructura del código

```
src/informes_warrants/
  ingesta/        # capa 1 (hecho: títulos de riesgo del 10-K/20-F, conversión a USD)
  calculo/        # capa 2 (hecho: normalizador SEC, métricas, DCF, semáforo de calidad, métricas sectoriales)
  visual/         # capa 3 (hecho: gráficos SVG de marca, HTML → PDF)
  plantillas/     # bloques Markdown, informe HTML/CSS, marca, fuentes (OFL) y texto legal
  informe/        # bloques, plantillas, estimaciones, ajustes, cobertura, perfiles, construir (datos) y render (HTML/PDF)
  ia/             # capa 4 (hecho: LLM, selección con cita literal, bloques de IA)
  almacenamiento/ # versiones: estados, herencia, comparación, SQLite, detección (hecho)
  ui/             # Streamlit (localhost) (pendiente)
```

La lógica (capas 1-4) no depende de la UI, así que la interfaz se puede cambiar sin tocar el núcleo.

## Fases

| Fase | Entregable | Hito verificable |
|---|---|---|
| 0. Base | Estructura, configuración, tests, CI (GitHub Actions en Ubuntu **y Windows**: los repos base solo usan Ubuntu), `edgartools>=5.61.1,<6` (la 6.0 cambia la API) | ✅ Hecho: Python 3.13, dependencias fijadas, ruff, CI en Ubuntu y Windows, CONTRIBUTING |
| 1. Ingesta | ✅ 5 ejercicios normalizados (companyfacts) contrastados con el XBRL del 10-K, cotización, histórico, comportamiento vs SPY/ETF, riesgos y texto del 10-K. Falta el *snapshot* por versión | `informes-warrants informe AAPL` |
| 2. Cálculo | ✅ Normalizador SEC, métricas propias, DCF, beta y semáforo, con tests *golden* del 10-K FY2023 de AAPL | Las cifras de AAPL cuadran al dólar con el 10-K |
| 3. Visual | ✅ Gráficos SVG, tablas, plantilla HTML A4 y PDF de 8 páginas ([ejemplo](ejemplos/AAPL_FY2025_borrador.pdf)) | **Primer informe borrador PDF completo por CLI (MVP)** ✅ |
| 4. IA | ✅ Proveedor, selección con cita literal y los 2 bloques de IA ([ia.md](ia.md)); falta conectar al borrador | `informes-warrants riesgos AAPL` |
| 5. Versiones | ✅ Estados, herencia, comparación, SQLite inmutable y detección; falta el snapshot y el PDF por versión (dependen de las fases 1-3) | `informes-warrants versiones detectar AAPL` |
| 6. Rigor del contenido | Las 8 carencias y los apartados «parciales» del índice, pasos 4.1-4.7 de [rigor-del-contenido.md](rigor-del-contenido.md): LTM, segmentos, valoración (5 + 5 años, escenarios, DCF inverso, comparables), analítica, riesgos cuantitativos, catalizadores, insiders, fuentes | PDF intermedio revisado en cada paso |
| 7. UI | Streamlit: dashboard con estados, editor híbrido, vista previa (sobre los bloques ya cerrados en la fase 6) | Flujo completo en localhost |
| 8. SaaS | Usuarios, autenticación, multiempresa, despliegue, avisos legales | Acceso externo |

## Decisiones tomadas

| Tema | Decisión | Origen |
|---|---|---|
| UI | Streamlit en localhost | Usuario |
| PDF | Plantilla HTML → WeasyPrint (GTK con MSYS2 en Windows) | equity-research-agent |
| LLM | llama4 en OpenRouter (si hay key) > `gpt-oss-120b` en Groq (activo) > Ollama `llama3.2:3b` local; mismo código para todos los proveedores | [ia.md](ia.md) |
| Uso de la IA | Mínimo: 2 bloques, solo elige y resume fragmentos literales | Usuario |
| Editor | Markdown, vista previa en tiempo real, emisión con confirmación del analista | Usuario |
| Recomendación | Sí: el SaaS la propone por potencial y el analista la confirma; se muestra siempre el precio objetivo calculado y el analista puede fijar el suyo | Usuario |
| Contenido | Enfoque determinista. Primero los apartados «parciales» del índice; lo «hecho» se mantiene y sus cambios van al final; lo «ejecutable», lo «externo» y lo del analista se aparcan | Usuario (2026-10-12) |
| Versiones | Detección automática + confirmación; año fiscal; SQLite fuera de OneDrive | Usuario |
| Alcance | Todas las empresas de EEUU: plantilla general + perfiles sectoriales validados (banca, seguros, REIT, BDC/fondos cerrados) y emisores extranjeros en USD; el resto, «plantilla pendiente de validar» | Usuario + [editor-y-versiones.md](editor-y-versiones.md#alcance) |
