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
5. **Reutilizar antes que construir:** todo se busca primero en `repositorios-github/` ([repositorios-base.md](repositorios-base.md)).

### Capa 1 — Ingesta de datos estructurados

| Necesidad | Reutilizar | Hay que construir |
|---|---|---|
| 10-K/10-Q, balance, P&L y cash flow (XBRL) | edgartools `Company`, `get_financials`, cosido multiperiodo en `xbrl/stitching` | — |
| TTM y ajuste por *splits* | edgartools `ttm/` | — |
| Precio, acciones y market cap | edgar_analytics `market_data` (`get_share_price`, `get_market_cap`, vía yfinance) | Fallback a Alpha Vantage (proveedor en financial-research-analyst-agent `src/data`) |
| Texto del 10-K (Items 1, 1A, 7) | edgartools `TenK.business`, `.risk_factors`, `.management_discussion` | — |
| Perfil de vencimientos de deuda | edgartools: los 6 conceptos `LongTermDebtMaturitiesRepaymentsOfPrincipal…` (12 meses → más de 5 años) están estandarizados en `xbrl/standardization/gaap_mappings.json` | — |
| Caché y *snapshot* de los datos usados | edgartools ya cachea HTTP | Guardar el *snapshot* de entrada de cada informe, necesario para las versiones |

### Capa 2 — Motor de cálculo determinista

| Métrica | Dónde está |
|---|---|
| EV (market cap + deuda CP/LP + minoritarios + preferentes − caja e inversiones CP) | edgar_analytics `market_data.compute_valuation_ratios` |
| EV/EBITDA, PER (P/E), P/BV, earnings yield | edgar_analytics `market_data` (docs/METRICS_REFERENCE.md › Valuation) |
| P/FCF | edgar_analytics `PerShareMetrics.fcf_per_share` → precio / FCF por acción; `fcf_yield` en stock-screener `src/data/quality.py` |
| Dividend yield, pay-out | financial-research-analyst-agent `tools/dividend_analyzer.py`; stock-screener `src/data/fetcher.py` (vía yfinance) |
| FCF conversion | edgar_analytics `Earnings Quality` (OCF/BN); FCF/BN y FCF/EBITDA con sus campos `free_cash_flow`, `net_income`, `ebitda_standard` |
| ROIC (NOPAT / capital invertido), asset turnover | edgar_analytics `scores.CapitalEfficiency` |
| Margen operativo, bruto y neto, ROE, ROA, deuda neta, DN/EBITDA, cobertura de intereses, D/E | edgar_analytics `metrics` |
| Ciclo de circulante, DuPont, Piotroski, Altman, Beneish, BPA, valor contable por acción | edgar_analytics `scores` |
| CAGR, crecimiento, 3-5 años fiscales, TTM | edgar_analytics `multi_period_analysis`; edgartools `ttm/`; financial-research-analyst-agent `financial_metrics.calc_cagr` |
| DCF (WACC, escenarios, sensibilidad), comparables | financial-research-analyst-agent `dcf_model`, `peer_comparison` (adaptar para que lean datos SEC) |

Decisión: la capa 2 **no requiere métricas nuevas**. Se usa **edgar_analytics como dependencia** (`pip`) y un módulo propio y fino solo **orquesta**: reúne las métricas, los años y el precio en un único resultado tabular trazable. Los tests se validan contra cifras conocidas de una empresa de referencia (AAPL).

### Capa 3 — Motor visual y estructural

| Necesidad | Reutilizar | Construir |
|---|---|---|
| Gráficos (ingresos vs EBITDA, desglose de FCF, vencimientos de deuda) | Plotly; `frontend/components/plotly_charts.py` de financial-research-analyst-agent como base | Estilo corporativo único; exportación vectorial SVG con `kaleido` |
| Tablas HTML corporativas | pandas `Styler` + Jinja2 (ya es dependencia de edgartools) | Plantillas de tabla |
| Ensamblado del informe | Plantilla proporcionada por el usuario (pendiente) | **Una única plantilla HTML (Jinja2) → PDF** |
| PDF | **equity-research-agent `stock_analysis_agent/tools.py`: Markdown → HTML → WeasyPrint `HTML(...).write_pdf(..., stylesheets=[CSS])`** (descartado reportlab, que usan financial-research-analyst-agent y automated-market-report, porque obliga a maquetar dos veces) | Aplicar el patrón a la plantilla Jinja2. WeasyPrint necesita GTK en Windows (documentarlo en el README) |

### Capa 4 — IA cualitativa y panel del analista

| Necesidad | Reutilizar | Construir |
|---|---|---|
| Configuración del LLM | **financial-research-analyst-agent `src/config.py` (`LLMSettings`) + `src/agents/base.py`**: proveedor elegible por `.env` (`LLM_PROVIDER` = ollama, openai, anthropic, groq, lmstudio, vllm), `LLM_MODEL`, `LLM_TEMPERATURE` = 0.1, `LLM_MAX_TOKENS` = 4096 | Reducirlo a lo que usa este proyecto |
| Resumen de MD&A (catalizadores) y riesgos (Item 1A) | Texto de edgartools; patrón de agentes de financial-research-analyst-agent; edgartools `ai/skills` (skills de EDGAR para Claude) | Prompts acotados con salida estructurada (viñetas + cita textual del 10-K para cada punto, verificable) |
| RAG, si el texto excede el contexto | financial-research-analyst-agent `src/rag`; mtcb para elegir el chunking | Solo si hace falta: con modelos de contexto largo, el Item 7 completo cabe |
| Backend API | financial-research-analyst-agent `src/api` (FastAPI) como patrón | Endpoints propios: crear informe, estado, editar bloques, exportar |
| UI | **Streamlit en localhost**; financial-research-analyst-agent `frontend` (Streamlit: `components/plotly_charts.py`, `utils/theme.py`) como base | Dashboard + editor híbrido + vista previa |

## Flujo al introducir un ticker

1. El analista escribe `AAPL` en el dashboard.
2. Estado «Extrayendo datos de la SEC…» → capa 1: último 10-K/10-Q, estados financieros y precio. Se guarda el *snapshot*.
3. Estado «Calculando métricas…» → capa 2.
4. Estado «Generando gráficos y tablas…» → capa 3.
5. Estado «Resumiendo el 10-K…» → capa 4 (IA): riesgos y catalizadores.
6. Estado «Listo para revisión» → editor híbrido.

## Editor híbrido (human-in-the-loop)

> El diseño detallado de la plantilla, el editor y el sistema de versiones lo proporcionará el usuario; esta sección es provisional.

- **Izquierda, bloque fijo:** tablas, múltiplos y gráficos generados por código. Son de solo lectura y cada cifra muestra su fuente (concepto XBRL, filing y fecha).
- **Derecha, bloque editable:** Markdown precargado con el resumen de la IA. El analista escribe la tesis y ajusta sus **estimaciones** (crecimiento, márgenes, WACC…). Al cambiar una estimación se recalculan la valoración y la parte de proyecciones, y las cifras históricas no cambian.
- **Vista previa:** el PDF se recompila desde la misma plantilla HTML.

## Versiones y almacenamiento

- Unidad de versión: **(ticker, periodo fiscal del último filing, nº de revisión)**, por ejemplo `AAPL · Q2 FY2026 · v1`.
- Cada versión guarda: *snapshot* de datos de entrada, métricas calculadas, textos de IA, textos y estimaciones del analista, PDF final y estado (`borrador` → `aprobado`).
- Una versión aprobada es **inmutable**. Al salir un 10-Q/10-K nuevo se crea un borrador que hereda la tesis anterior para que el analista la actualice.
- Historial por empresa con comparación entre versiones (tesis y estimaciones), para auditar la evolución.
- Almacenamiento: SQLAlchemy con SQLite en local y PostgreSQL en producción (patrón `models/persistence` de financial-research-analyst-agent). Los PDFs y *snapshots*, en disco o en almacenamiento de objetos.

## Estructura del código

```
src/informes_warrants/
  ingesta/        # capa 1
  calculo/        # capa 2
  visual/         # capa 3 (gráficos, tablas)
  plantillas/     # HTML/Jinja2 del informe
  ia/             # capa 4 (prompts y extracción del 10-K)
  almacenamiento/ # modelos, versiones
  ui/             # Streamlit (localhost)
```

La lógica (capas 1-4) no depende de la UI, así que la interfaz se puede cambiar sin tocar el núcleo.

## Fases

| Fase | Entregable | Hito verificable |
|---|---|---|
| 0. Base | Estructura, configuración, tests, CI (GitHub Actions) | ✅ en parte (estructura y config) |
| 1. Ingesta | Estados financieros de 5 años + precio + texto del 10-K + *snapshot* | `informes-warrants datos AAPL` |
| 2. Cálculo | Todas las métricas de la capa 2, con tests | Las cifras de AAPL cuadran con el 10-K |
| 3. Visual | Gráficos, tablas, plantilla HTML y PDF | **Primer informe borrador PDF completo por CLI (MVP)** |
| 4. IA | Resumen de riesgos y MD&A con citas | Bloques cualitativos en el borrador |
| 5. Versiones | Persistencia, estados, historial | Dos versiones de AAPL comparables |
| 6. UI | Streamlit: dashboard con estados, editor híbrido, vista previa | Flujo completo en localhost |
| 7. Contenido completo | Resto del índice: DCF, comparables, gobierno (proxy), proyecciones, anexos | Informe equivalente a la referencia |
| 8. SaaS | Usuarios, autenticación, multiempresa, despliegue, avisos legales | Acceso externo |

## Decisiones tomadas

| Tema | Decisión | Origen |
|---|---|---|
| UI | Streamlit en localhost | Usuario |
| PDF | Plantilla HTML → WeasyPrint | equity-research-agent |
| LLM | `LLMSettings` multiproveedor configurable por `.env` | financial-research-analyst-agent |
| Plantilla, editor y versiones | Pendiente: los aporta el usuario | Usuario |
