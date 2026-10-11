# Estructura del informe

El índice de contenidos sale del informe de referencia de Lighthouse/IEAF sobre Treelogic (38 páginas; se ignora la maquetación) y se adapta a empresas cotizadas en EEUU.

Leyenda de la columna «Cómo»:
- **D**: dato directo de una fuente.
- **C**: cálculo propio.
- **P**: proyección o estimación.
- **IA**: texto redactado por un LLM.

Los repos citados se describen en [repositorios-base.md](repositorios-base.md).

| # | Sección (págs. en la referencia) | Contenido | Cómo | Fuente / reutilizar |
|---|---|---|---|---|
| 1 | **Portada / resumen** (1) | Precio, fecha, sector y descripción breve | D | edgartools (`Company`), precio vía yfinance (stock-screener `src/data`) |
| | | Market data: market cap, EV, nº de acciones, máximo/medio/mínimo 12m, volumen medio, rotación, ticker, cierre fiscal | D+C | precios + edgartools (acciones en circulación) |
| | | Estructura accionarial | D | edgartools proxy (DEF 14A, Item 403), `beneficial_ownership` (13D/G) y Form 4 (`ownership`). El 13F (`thirteenf`) es la cartera de una gestora, no los accionistas de un emisor |
| | | Datos financieros básicos (histórico + 3 años estimados): ingresos, EBITDA, BN, BPA, FCF, pay-out, DPA, DFN, DN/EBITDA, ROE, ROCE | D+C+P | edgartools `xbrl`/`financials` + edgar_analytics `metrics`/`forecasting` |
| | | Ratios y múltiplos: PER, P/BV, rentabilidad por dividendo, EV/Ventas, EV/EBITDA, EV/EBIT, FCF yield | C | edgar_analytics + precio |
| | | Comportamiento relativo en bolsa (base 100; -1m/-3m/-12m/YTD/-3a/-5a, absoluto y vs índice, vs sector) | C | financial-research-analyst-agent `performance_tracker.track_performance` (SPY, QQQ, `SECTOR_ETFS`); falta el mapeo SIC → ETF |
| | | Titulares de la tesis (4-5 bloques) | IA | Patrón `key_risk`/`key_catalyst` de financial-research-analyst-agent `llm_insight_engine` (`report_generator` ignora los datos) |
| 2 | **Conclusiones** (3-7) | A) Situación actual (histórico 3-4 años); B) Hacia dónde va (proyecciones); C) Fortalezas estructurales y riesgos clave; mensaje final | IA sobre datos C/P | Prompts propios; de financial-research-analyst-agent solo el patrón `*_direct` + `*_with_narrative` (su orquestador pasa texto en vez de datos) |
| 3 | **La compañía en 8 gráficos** (8) | Gráficos clave: mercado, mix, márgenes, FCF, deuda, valoración | C | financial-research-analyst-agent `frontend/components/plotly_charts.py` (`report_export` usa reportlab y no genera gráficos) |
| 4 | **Descripción del negocio** (9-16) | Historia, líneas de actividad, desglose de ingresos por segmento y su evolución, plantilla, estructura de costes, inversión en I+D/intangibles, concentración de clientes, productos, posicionamiento competitivo | D+IA | edgartools: Item 1, segmentos XBRL (`view='detailed'`) y concentración de clientes (`MajorCustomersAxis`); costes de personal `LaborAndRelatedExpense` vía `EntityFacts.time_series`. Sin RAG |
| 5 | **Industria y mercado** (17-21) | Tamaño y crecimiento del mercado (CAGR), tendencias, regulación y financiación sectorial | IA + D externos | 10-K Item 1/1A; edgartools `search_filings` (EFTS). No usar `news_fetcher` (inventa noticias por defecto) ni `macro_data` (serie `NAPM` retirada de FRED). El tamaño y el CAGR del mercado no tienen fuente en ningún repo |
| 6 | **Análisis financiero** (22-26) | Ingresos por línea y mix histórico vs estimado; EBITDA reportado vs recurrente (conciliación); costes de personal; bridge EBITDA → FCF; evolución del FCF; DFN; ROCE vs WACC; partidas no recurrentes/subvenciones | C+P | edgartools `XBRLS.from_filings` y `ttm/` + edgar_analytics `metrics`, `multi_period_analysis`; definiciones propias de EBIT/EBITDA/DFN (ver [plan.md](plan.md), capa 2) |
| 7 | **Valoración** (27) | DCF (FCFF, WACC: Rf, ERP, beta, Ke, Kd, g); múltiplos vs comparables (PER, EV/EBITDA, EV/Ventas, crecimiento); sensibilidad | C+P | DCF propio (patrón de financial-research-analyst-agent `dcf_model`); comparables con edgartools `get_companies_by_industry`. `monte_carlo` simula el precio, no la valoración: no se usa aquí |
| 8 | **Análisis de riesgos** (28-29) | Qué puede salir mal: riesgos ordenados por impacto | IA | 10-K Item 1A (Risk Factors) vía edgartools + LLM |
| 9 | **Gobierno corporativo** (30-31) | Estructura accionarial, consejo, alta dirección, comisión de auditoría, KPIs de gobierno (independencia, retribución…) | D+IA | edgartools `proxy` (retribución y honorarios de auditoría estructurados; consejo, independencia y comisiones solo como texto para la IA), Form 4 (`ownership`), auditor (`company_reports/auditor`) |
| A1 | **Anexo 1. Proyecciones financieras** (32) | Balance, cuenta de resultados y flujos de caja: histórico 4-5 años + 3 estimados, con TACC | D+P | edgartools `XBRLS.from_filings` o `Company.income_statement(periods=5)` (`get_financials()` solo da 3 años); proyección propia |
| A2 | **Anexo 2. Analítica del FCF** (33-34) | FCF recurrente y de los accionistas; variación acumulada del FCF | C | edgar_analytics + cálculo propio |
| A3 | **Anexo 3. Cálculo del EV** (34) | Market cap + DFN + minoritarios + ajustes | C | edgartools + precio |
| A4 | **Anexo 4. Comportamiento histórico** (35) | Serie larga (unos 10 años) de magnitudes y ratios | D+C | edgartools XBRL (company facts) |
| A5 | **Anexo 5. Principales comparables** (35) | Tabla de peers: market cap, PER, crecimiento del BPA, EV/EBITDA, margen, EV/Ventas, crecimiento de ingresos | D+C | edgartools `get_companies_by_industry`; edgar_analytics `analyze(peers=...)`; patrón `peer_comparison` |
| L | **Información legal** (36-38) | Aviso legal / disclaimer | Plantilla fija | — |

## Huecos que no cubren los repos base

- **Estimaciones (años «e»):** solo hay ARIMA para ingresos (edgar_analytics). Falta un modelo de proyección de los tres estados financieros completos.
- **EBITDA recurrente y ajustes:** requieren reglas propias sobre partidas XBRL. Ayuda parcial: edgartools `edgar/earnings.py` extrae el Adjusted EBITDA y la `eps_reconciliation` publicados (EX-99.1); 101 emisores no tienen línea canónica de D&A y necesitan *fallback*.
- **Datos de mercado sectoriales (tamaño, CAGR):** no salen de la SEC; requieren fuentes externas o un LLM con búsqueda.
- **Composición final del documento** (plantilla con secciones, tablas y gráficos): hay que construirla, partiendo de equity-research-agent `combine_reports` (WeasyPrint) y del patrón Jinja2 con herencia de edgartools `ownership/html_render.py`.
- **Consejo e independencia estructurados** (§9) y **accionistas institucionales de un emisor** desde la SEC: no existen en ningún repo.

Inventario completo y rutas exactas: [inventario/README.md](inventario/README.md).
