# Repositorios base

Código de terceros que el proyecto usa como infraestructura. **Resumen.** El análisis completo (100 % de los archivos, rutas y símbolos exactos, discrepancias y huecos) está en [inventario/README.md](inventario/README.md): consúltalo antes de cualquier tarea.

Las copias locales viven en `repositorios-github/` (zips, ignorados por git). Para obtenerlas, descarga cada repo desde su URL.

## Resumen y licencias

| Repo | URL | Licencia | Qué aporta |
|---|---|---|---|
| edgartools | github.com/dgunning/edgartools | MIT | Núcleo de datos SEC: empresas, filings, XBRL, estados financieros |
| edgar_analytics | github.com/zoharbabin/edgar_analytics | MIT | Métricas, scores y forecasting sobre edgartools |
| financial-research-analyst-agent | github.com/gsaini/financial-research-analyst-agent | MIT | Agentes LLM, herramientas de análisis, API, frontend |
| equity-research-agent | github.com/CarlosFinEngg/equity-research-agent | MIT | Patrón multiagente para informes de research |
| stock-screener | github.com/RyanJHamby/stock-screener | MIT | Screening técnico/fundamental, notificaciones |
| mtcb | github.com/chonkie-inc/mtcb | Apache-2.0 | Benchmark de chunking para RAG (incluye dataset de filings SEC) |
| sec-edgar-toolkit | github.com/stefanoamorelli/sec-edgar-toolkit | **AGPL-3.0** | Cliente EDGAR alternativo (Python + TypeScript) |
| automated-market-report | github.com/hgnx/automated-market-report | **Sin licencia** | Informe diario de mercado en PDF |
| financial-ai-agent | (URL original desconocida) | **Sin licencia** | Agente LangGraph + Streamlit de análisis |
| FinRobot | github.com/AI4Finance-Foundation/FinRobot | Apache-2.0 | Motor de valoración determinista (DCF inverso, comparables, SOTP, DDM, LBO) y generador de informes ([ficha](inventario/finrobot.md)) |
| ai-hedge-fund | github.com/virattt/ai-hedge-fund | MIT | Fondo simulado con agentes; estudio de eventos ([ficha](inventario/otros-backtesting.md)) |
| vectorbt | github.com/polakowo/vectorbt | Apache-2.0 **+ Commons Clause** | *Backtesting* vectorizado; no usable en un SaaS ([ficha](inventario/otros-backtesting.md)) |
| Lean | github.com/QuantConnect/Lean | Apache-2.0 | Motor de *trading* algorítmico en C# ([ficha](inventario/otros-backtesting.md)) |

**Restricciones legales:**
- **AGPL-3.0 (sec-edgar-toolkit):** si se incorpora su código a un SaaS, hay que publicar el código fuente del servicio. Úsalo como referencia, no lo copies.
- **Sin licencia (automated-market-report, financial-ai-agent):** todos los derechos están reservados. Solo se pueden tomar ideas, no código.
- **MIT / Apache-2.0:** se puede reutilizar conservando el aviso de copyright.
- **Commons Clause (vectorbt):** prohíbe vender el software o un servicio basado en él: no se usa.

## Detalle por repo

### edgartools (v5.61.1) — dependencia principal
Se instala con `pip install edgartools`. Paquete `edgar/`:
- `Company`, `get_filings`, `Filing`: búsqueda de empresas y presentaciones (filings).
- `company_reports/`: objetos tipados para 10-K, 10-Q, 8-K, 20-F, 40-F, 6-K, notas de prensa, auditor y filiales.
- `xbrl/`: parseo de XBRL (`standardization/gaap_mappings.json` incluye los vencimientos de deuda `LongTermDebtMaturitiesRepaymentsOfPrincipal…`), estados financieros, cosido multiperiodo (`stitching`), dimensiones, notas y estandarización.
- `financials.py`: `Financials.balance_sheet()`, `income_statement()`, `cash_flow_statement()`.
- `ttm/`: cálculo de los últimos 12 meses (TTM) y ajuste por *splits*.
- `standardization/`: sinónimos de conceptos contables.
- `ownership/`, `beneficial_ownership/`, `thirteenf/`: Form 3/4/5, 13D/G y 13F.
- `proxy/`, `offerings/`, `funds/`, `bdc/`, `earnings.py`: proxy, emisiones, fondos y resultados.
- `ai/`: servidor MCP (`edgartools-mcp`, extra `[ai]`), skills para LLM y exportadores a contexto de LLM.
- Docs: `docs/` (mkdocs). Hay guías de XBRL, estados financieros y filings.

### edgar_analytics — métricas y scoring
Uso: `ea.analyze("AAPL", peers=[...])` y la CLI `edgar-analytics`. Módulos:
- `metrics`: más de 40 métricas GAAP/IFRS (márgenes, ROE/ROA, deuda neta, DN/EBITDA, FCF, coberturas, calidad del beneficio = OCF/BN).
- `market_data`: precio y market cap (yfinance), EV, PER, P/BV, EV/EBITDA y earnings yield.
- `scores`: ROIC (`CapitalEfficiency`), BPA/FCF por acción, ciclo de circulante, DuPont.
- Referencia completa de fórmulas: `docs/METRICS_REFERENCE.md`.
- `forecasting`: previsión de ingresos con ARIMA/SARIMAX mediante patrón de estrategia.
- `multi_period_analysis`: análisis anual y trimestral.
- `synonyms`: mapeo de conceptos XBRL.
- `market_data`, `company_facts`, `reporting`, `orchestrator` (CSV y salida *rich*), `cache`.

Depende de `edgartools>=5,<6`. Se usa como dependencia para la capa de análisis, con matices: `market_data` no devuelve el EV, su `EBITDA (standard)` incluye resultados no operativos, `compute_ttm` no suma 12 meses consecutivos, desacumula trimestres por año natural, cachea en el directorio de trabajo y su `CompanyFactsClient` usa un User-Agent genérico.

### financial-research-analyst-agent — capa de IA y app
- `src/agents/`: orquestador y agentes de fundamentales, técnico, sentimiento, riesgo, resultados, dividendos, opciones, temático, disrupción, generador de informes y *mixin* de RAG.
- `src/tools/` (40): `dcf_model`, `peer_comparison`, `financial_metrics`, `technical_indicators`, `monte_carlo`, `factor_model`, `insider_activity`, `news_fetcher`, `sentiment_engine`, `report_export`, `scheduled_reports`, `alerts`, `portfolio_optimizer`, `backtesting_engine`, `macro_data`, `short_interest`, etc.
- `src/data/`: proveedores `YFinanceProvider`, `AlphaVantageProvider`, FMP y `MultiProvider` (con respaldo). `validator.py` existe pero no está conectado.
- `src/rag/`: ingesta, *embeddings* y recuperación (Chroma/FAISS).
- `src/api/`: API REST con rutas, esquemas y seguridad.
- `src/models/`: `persistence.py` (SQLAlchemy) no lo usa ningún módulo; solo patrón.
- `frontend/`: Streamlit con 17 páginas (dashboard, análisis, informes, peers…).
- Stack: LangChain/LangGraph. **Configuración LLM adoptada:** `src/config.py` (`LLMSettings`: `LLM_PROVIDER`, `LLM_MODEL`, temperatura 0.1, 4096 tokens) y `src/agents/base.py` (ollama, openai, anthropic, groq, lmstudio, vllm).
- `tools/dividend_analyzer.py`: dividend yield, pay-out. `tools/financial_metrics.py`: ratios de valoración, rentabilidad, liquidez y CAGR.

### equity-research-agent — patrón multiagente
Google ADK con un agente coordinador y subagentes de fundamentales, técnico, flujos de fondos y política. Exporta a PDF/HTML (`tools.py` `combine_reports`: Markdown → HTML → **WeasyPrint** con CSS; **patrón PDF adoptado**, con el fallo de usar `html_content` en vez de `html_full`). LLM vía LiteLLM (Gemini/OpenAI). `email_report` no está registrada como herramienta, lleva credenciales de ejemplo en el código y devuelve éxito aunque falle.

### stock-screener — screening y automatización
- `src/screening/`: indicadores, fases de Weinstein/Minervini, `quant_engine`, `signal_engine` y procesado por lotes.
- `src/data/`: yfinance/FMP (`fetcher.py` dividend yield; `storage.py` `StockDatabase._calculate_fcf_yield`; `quality.py` `DataQualityChecker`, la pieza más útil), universo de unas 3.800 acciones, fundamentales, calidad de datos y almacenamiento SQLAlchemy/Postgres.
- `src/notifications/`: email, Slack y *scheduler*.
- Ejecución diaria con GitHub Actions.

### mtcb — evaluación RAG
Benchmark de estrategias de chunking (chonkie). Los datasets `Ficha` (filings SEC) y `Tacha` (tablas financieras) están en Hugging Face, no en el repo, con licencia por confirmar. Lo más útil para la capa 4: `ExactMatchValidator`/`FuzzyMatchValidator`, que verifican que una cita existe literalmente en el texto.

### sec-edgar-toolkit — solo referencia (AGPL)
Cliente EDGAR en Python y TypeScript con *rate limit*, extracción de items de 10-K/10-Q/8-K, XBRL *as-reported*, 13F y ownership. Solapa con edgartools; consúltalo solo si edgartools no cubre algo.

### automated-market-report — solo ideas (sin licencia)
Informe diario en PDF con reportlab y plotly: índices, FICC, ETFs, *top movers*, calendario económico y noticias.

### financial-ai-agent — solo ideas (sin licencia)
Flujo LangGraph con nodos y estado: datos CSV → búsqueda de competidores (Tavily) → informe con bucle de *feedback* en Streamlit. Ojo: la memoria es `SqliteSaver(":memory:")` (se pierde en cada ejecución) y la investigación de competidores no llega al LLM, que inventa las cifras.

## Mapa: pieza del SaaS → qué reutilizar

Versión resumida; la matriz completa está en [inventario/README.md](inventario/README.md).

| Pieza | Reutilizar |
|---|---|
| Datos SEC (filings, XBRL, estados, Items del 10-K, referencia de tickers/SIC) | edgartools (`XBRLS`, `ttm/`, `TenK`, `reference/`, `documents/`) |
| Métricas, ratios y scores | edgar_analytics (dependencia) + módulo propio de definiciones y métricas faltantes |
| Valoración (DCF) y comparables | DCF propio (patrón `dcf_model`); comparables con edgartools `get_companies_by_industry` |
| Datos de mercado e histórico de precios | financial-research-analyst-agent `src/data/provider.py` (`MultiProvider`); comportamiento relativo con `performance_tracker` |
| Calidad de datos | stock-screener `DataQualityChecker` + edgartools `validate_balance_sheet` |
| Redacción con LLM | Prompts propios; patrón `llm_insight_engine` de financial-research-analyst-agent |
| Verificación de citas del 10-K | mtcb `ExactMatchValidator`/`FuzzyMatchValidator` + edgartools `DocumentSearch` |
| Plantilla y PDF | equity-research-agent `combine_reports` (WeasyPrint) + patrón Jinja2 de edgartools `ownership/html_render.py` |
| Gráficos y UI Streamlit | financial-research-analyst-agent `frontend/` (`plotly_charts.py`, `theme.py`) |
| Programación y notificaciones | stock-screener `notifications`, financial-research-analyst-agent `scheduled_reports` |
| Organización, tests, CI y gobierno de agentes IA | edgartools (`CLAUDE.md`, `.claude/agents`, `.claude/commands`, `conftest` con carriles fast/network); CI de edgar_analytics |
