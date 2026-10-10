# Repositorios base

Código de terceros que el proyecto usa como infraestructura. **Antes de implementar algo, comprueba aquí si ya existe.**

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

**Restricciones legales:**
- **AGPL-3.0 (sec-edgar-toolkit):** si se incorpora su código a un SaaS, hay que publicar el código fuente del servicio. Úsalo como referencia, no lo copies.
- **Sin licencia (automated-market-report, financial-ai-agent):** todos los derechos están reservados. Solo se pueden tomar ideas, no código.
- **MIT / Apache-2.0:** se puede reutilizar conservando el aviso de copyright.

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
- `scores`: modelos de scoring (Altman, Piotroski, Beneish).
- `forecasting`: previsión de ingresos con ARIMA/SARIMAX mediante patrón de estrategia.
- `multi_period_analysis`: análisis anual y trimestral.
- `synonyms`: mapeo de conceptos XBRL.
- `market_data`, `company_facts`, `reporting`, `orchestrator` (CSV y salida *rich*), `cache`.

Depende de `edgartools>=5,<6`. **Es candidato directo para la capa de análisis.**

### financial-research-analyst-agent — capa de IA y app
- `src/agents/`: orquestador y agentes de fundamentales, técnico, sentimiento, riesgo, resultados, dividendos, opciones, temático, disrupción, generador de informes y *mixin* de RAG.
- `src/tools/` (40): `dcf_model`, `peer_comparison`, `financial_metrics`, `technical_indicators`, `monte_carlo`, `factor_model`, `insider_activity`, `news_fetcher`, `sentiment_engine`, `report_export`, `scheduled_reports`, `alerts`, `portfolio_optimizer`, `backtesting_engine`, `macro_data`, `short_interest`, etc.
- `src/data/`: proveedores Alpha Vantage y FMP con validación.
- `src/rag/`: ingesta, *embeddings* y recuperación (Chroma/FAISS).
- `src/api/`: API REST con rutas, esquemas y seguridad.
- `src/models/`: persistencia de análisis e informes.
- `frontend/`: Streamlit con 17 páginas (dashboard, análisis, informes, peers…).
- Stack: LangChain/LangGraph. **Configuración LLM adoptada:** `src/config.py` (`LLMSettings`: `LLM_PROVIDER`, `LLM_MODEL`, temperatura 0.1, 4096 tokens) y `src/agents/base.py` (ollama, openai, anthropic, groq, lmstudio, vllm).
- `tools/dividend_analyzer.py`: dividend yield, pay-out. `tools/financial_metrics.py`: ratios de valoración, rentabilidad, liquidez y CAGR.

### equity-research-agent — patrón multiagente
Google ADK con un agente coordinador y subagentes de fundamentales, técnico, flujos de fondos y política. Exporta a PDF/HTML (`tools.py`: Markdown → HTML → **WeasyPrint** con CSS; **patrón PDF adoptado**) y envía por email. LLM vía LiteLLM (Gemini/OpenAI). Está orientado al mercado chino (akshare), así que lo reutilizable es la arquitectura y los prompts.

### stock-screener — screening y automatización
- `src/screening/`: indicadores, fases de Weinstein/Minervini, `quant_engine`, `signal_engine` y procesado por lotes.
- `src/data/`: yfinance/FMP (`fetcher.py` dividend yield; `quality.py` FCF yield), universo de unas 3.800 acciones, fundamentales, calidad de datos y almacenamiento SQLAlchemy/Postgres.
- `src/notifications/`: email, Slack y *scheduler*.
- Ejecución diaria con GitHub Actions.

### mtcb — evaluación RAG
Benchmark de estrategias de chunking (chonkie). El dataset `Ficha` (filings SEC) y `Tacha` (tablas financieras) sirven para elegir el chunking del RAG sobre 10-K.

### sec-edgar-toolkit — solo referencia (AGPL)
Cliente EDGAR en Python y TypeScript con *rate limit*, extracción de items de 10-K/10-Q/8-K, XBRL *as-reported*, 13F y ownership. Solapa con edgartools; consúltalo solo si edgartools no cubre algo.

### automated-market-report — solo ideas (sin licencia)
Informe diario en PDF con reportlab y plotly: índices, FICC, ETFs, *top movers*, calendario económico y noticias.

### financial-ai-agent — solo ideas (sin licencia)
Flujo LangGraph con nodos, estado y memoria SQLite: datos CSV → comparación con competidores (Tavily) → informe con bucle de *feedback* en Streamlit.

## Mapa: pieza del SaaS → qué reutilizar

| Pieza | Reutilizar |
|---|---|
| Datos SEC (filings, XBRL, estados) | edgartools |
| Métricas, ratios, scores, forecast | edgar_analytics |
| Valoración (DCF), peers, Monte Carlo | financial-research-analyst-agent `src/tools` |
| Datos de mercado/precio | stock-screener `src/data`, financial-research-analyst-agent `src/data` |
| Redacción del informe con LLM | financial-research-analyst-agent `src/agents` (patrón: equity-research-agent) |
| RAG sobre 10-K | financial-research-analyst-agent `src/rag` + mtcb para evaluar el chunking |
| Exportar el informe (PDF/HTML) | financial-research-analyst-agent `report_export` (idea: automated-market-report) |
| Programación y notificaciones | stock-screener `notifications`, financial-research-analyst-agent `scheduled_reports` |
| API y frontend | financial-research-analyst-agent `src/api` + `frontend` |
