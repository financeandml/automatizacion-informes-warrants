# edgartools-5-docs

- **Repo / alcance / licencia:** `edgartools-main` (dgunning/edgartools, `requires-python >=3.10`, rama 5.x con la 6.0 en desarrollo). Alcance: `docs/` (todo), `examples/`, `notebooks/`. Licencia **MIT** (`LICENSE.txt`, © 2022-present Dwight Gunning). Docs publicadas con mkdocs-material (`mkdocs.yml` está en la raíz del repo, fuera de este alcance).
- **Cobertura:** **378** archivos (docs 308, examples 13, notebooks 57).
  - Texto (221): 135 `.md`, 26 `.py`, 57 `.ipynb`, 1 `.css`, 1 `.js`, 1 `.txt`.
  - Binarios (157): 46 png, 49 svg, 41 webp, 8 jpg, 6 gif, 6 mp4, 1 pdf.
  - **Leídos completos: 66**:
    - 32 docs `.md` (todos los de financieros/XBRL/10-K/proxy/config/errores/tests/IA que se citan abajo);
    - 5 archivos de `docs/` (`requirements.txt`, `doctest.py`, `quickstart.py`, `stylesheets/extra.css`, `javascripts/nav-enhance.js`);
    - 6 de `docs/examples/`;
    - 8 de `examples/`;
    - 15 notebooks (todas las celdas de código y los títulos markdown; las salidas solo por muestreo).
  - **Solo firmas: 155**. Se leyeron cabeceras (`#`), firmas `def`/clases, tablas de propiedades y llamadas a la API:
    - las guías de formularios poco relevantes (fondos, BDC, Form C/D, S-1/S-3, 424B, 497K, N-PORT, N-PX, N-MFP, N-CEN, 24F-2NT, 10-D, MA-I, DRS, EFFECT, 6-K, 40-F, SGML, XmlFiling);
    - las referencias `api/xbrl|filing|filings`, `extract-statements` (~70 % del texto), las quick-refs, `archive/*`, `verification-{gap-analysis,roadmap,survey,weaknesses}`, los informes de tipos, `customizing-standardization`, `sec/schedule13/*`;
    - los 11 scripts demo grandes y 42 notebooks (título y APIs usadas).
  - **Por muestreo: 157** binarios. Se listaron por carpeta y tipo, se abrieron `MSFT_financial_complex.png` y `query-aapl-debt.png` y se miraron las cabeceras de los svg.
  - Total: 66 + 155 + 157 = 378.

## Qué contiene

| Ruta | Qué hace | API/elementos clave (nombres exactos) |
|---|---|---|
| `docs/index.md`, `quickstart.md`, `installation.md`, `complete-guide.md`, `quick-guide.md`, `why-edgartools.md`, `about.md`, `examples.md` | Portada, instalación (Py ≥3.10, conflicto con el paquete `edgar`), cheat sheet y mapa de objetos | `set_identity`, `EDGAR_IDENTITY` (con variantes cmd/PowerShell), `Company`, `get_financials`, `get_quarterly_financials`, `get_facts`, `latest`, `shares_outstanding`, `public_float` |
| `docs/xbrl/getting-started/choosing-the-right-api.md` | Árbol de decisión entre las 3 APIs | Company Facts (multianual), `Financials` (un filing, getters), `filing.xbrl()` (segmentos, notas) |
| `docs/common-pitfalls.md` | Errores frecuentes | Los getters pueden devolver `None`; valores en USD reales; `period_offset`; **importar `edgar` en el hilo principal antes de abrir hilos**; claves `tenk['Item 1A']` |
| `docs/upgrade/6.0.md` | Cambios de la 6.0, uno por símbolo | `cash_flow_statement()` único; quitan `cashflow_statement`/`cash_flow`; `edgar.exceptions`; `EDGARTOOLS_STRICT_ERRORS=1`; `get_financials()` sin XBRL lanza `XBRLFilingWithNoXbrlData`; claves canónicas `part_ii_item_7`; `__all__`; se retira `edgar.files` |
| `docs/guides/financial-data.md` | Estados financieros y getters | `get_revenue`, `get_net_income`, `get_operating_income`, `get_total_assets`, `get_free_cash_flow`, `get_capital_expenditures`, `get_financial_metrics()`, `view="summary|standard|detailed"`, `XBRLS.from_filings` |
| `docs/guides/company-facts.md`, `docs/api/entity-facts-reference.md` | API de hechos multianuales (`EntityFacts`) | `company.income_statement(periods, annual, as_dataframe, concise_format)`, `balance_sheet(as_of=)`, `MultiPeriodStatement.iter_with_values/find_item/get_display_value/to_dict/to_flat_list/get_period_comparison/to_llm_context`, `facts.query().by_concept/by_fiscal_year/by_form_type/by_period_length/latest_instant/pivot_by_period`, `time_series`, `get_fact`, `search_concepts`, `available_periods`, `FinancialFact.accession/filing_date/form_type/period_end` |
| `docs/guides/multi-year-financial-data-api.md` | Tutorial FastAPI + Streamlit/Plotly sobre datos multianuales | `_convert_statement_to_dict` (label, concept, values, `get_display_value`), CAGR y crecimiento; patrón de caché con TTL |
| `docs/xbrl/guides/multi-period-analysis.md` | Cosido multiperiodo | `XBRLS.from_filings(filings.filter(amendments=False).head(5))`, `xbrls.statements.income_statement(max_periods=5, view=)`, `df.set_index("standard_concept")`, `get_period_end_dates`, `xbrls.query().trend_analysis` |
| `docs/xbrl/concepts/standardization.md` | **95 conceptos estándar** y 2.900+ mapeos | `Revenue`, `GrossProfit`, `OperatingIncomeLoss`, `NetIncome`, `DepreciationExpense`, `AmortizationOfIntangibles`, `CapitalExpenses`, `CommonDividendsPaid`, `ShortTermDebt`, `LongTermDebt`, `CashAndMarketableSecurities`, `MinorityInterestBalance`, `SharesFullyDilutedAverage`, `OperatingLeaseCommitmentYear1..5`; `get_default_mapper`, `StandardConcept`, `reverse_index.lookup` |
| `docs/xbrl/concepts/dimension-handling.md` | Valores de cara frente a desgloses | Columnas `dimension`, `is_breakdown`, `dimension_label`; ejes `ProductOrServiceAxis`, `StatementBusinessSegmentsAxis`, `StatementGeographicalAxis`, `MajorCustomersAxis` |
| `docs/xbrl/guides/calculation-linkbase.md` | Grafo de cálculo y extensiones del filer | `xbrl.calculation_linkbase()` (`weight`, `menucat`), `statement.extension_arcs(include_values=True)` |
| `docs/api/xbrl.md` (firmas) | Referencia de XBRL | `to_dataframe(include_dimensions, include_unit, presentation)`; columnas `balance`, `weight`, `preferred_sign`, `level`, `abstract`, `parent_concept`; `presentation=True` (signos como en el HTML de la SEC) |
| `docs/guides/extract-statements.md` (firmas) | Jerarquía y segmentos | `MultiFinancials.extract`, `xbrl.notes()`, `xbrl.disclosures()`, `render().to_markdown()`, `facts.search_facts` |
| `docs/guides/stock-splits-eps-normalization.md` | *Splits* y TTM | `edgar.ttm.detect_splits`, `apply_split_adjustments`, `company.get_ttm(concept)`, `get_ttm_revenue`, `get_ttm_net_income` (`TTMMetric.value/as_of_date/periods`) |
| `docs/api/company.md`, `guides/entity-api-guide.md`, `guides/company-classification.md` | Perfil de la empresa y su clasificación | `name`, `tickers`, `sic`, `industry`, `fiscal_year_end`, `get_exchanges()`, `business_address()`, `filer_category`, `is_large_accelerated_filer`, `business_category`, `is_operating_company()`, `is_financial_institution()`, `is_foreign`, `filer_type` |
| `docs/guides/business-overview-data-sources-guide.md`, `guides/company-page-guide.md` | Cómo montar la ficha de una empresa | Clase de ejemplo `CompanyOverview`; `tenk.business`, `risk_factors`, `management_discussion`, `tenk['Item 1C']`, `auditor`, `subsidiaries`; tabla de caché (contenido del 10-K: para siempre) |
| `docs/concepts/data-objects.md`, `docs/data-objects.md` | Catálogo de objetos que devuelve `filing.obj()` | `TenK`, `TenQ`, `EightK`, `Form4`, `ThirteenF`, `Schedule13D/G`, `ProxyStatement`, `Schedule14D9`, `UnsupportedFilingTypeError` |
| `docs/guides/proxystatement-data-object-guide.md` | DEF 14A (XBRL ECD) | `peo_name`, `peo_total_comp`, `peo_actually_paid_comp`, `executive_compensation` (DataFrame de 5 años), `pay_vs_performance`, `total_shareholder_return`, `peer_group_tsr`, `insider_trading_policy_adopted`, `named_executives`. **Consejo y directores no están estructurados** (`filing.search`) |
| `docs/guides/schedule13dg-…`, `thirteenf-…`, `track-form4.md`, `insider-filings.md`, `13f-filings.md`, `company-insiders.md` (firmas) | Accionariado e insiders | `total_shares`, `total_percent`, `reporting_persons`, `holdings`, `compare_holdings()`, `holding_history()`, `get_ownership_summary()` |
| `docs/eightk-filings.md` | 8-K y resultados | `has_earnings`, `earnings.financial_tables/segment_data/eps_reconciliation/guidance`, `get_income_statement()`, `FinancialTable.scaled_dataframe` |
| `docs/advanced-search.md`, `guides/full-text-search.md` | Búsqueda con ranking dentro de un filing y FTS en todo EDGAR | `DocumentSearch(filing.parse()).ranked_search(query, algorithm="bm25|hybrid|semantic", in_section=, boost_sections=, top_k=)`, `search_filings`, `filing.grep` |
| `docs/guides/sec-viewer-guide.md` | Visor R*.htm de la SEC | `filing.viewer`, `financial_statements`, `notes`, `currency_scaling`, `calculation_tree`, `compare_context` |
| `docs/guides/reference-data.md`, `company-subsets.md`, `company-group-testing.md` | Universo de tickers y peers por SIC | `find_cik`, `get_companies_by_industry(sic=, sic_range=, sic_description_contains=)`, `get_companies_by_exchanges`, `get_popular_companies(PopularityTier)` |
| `docs/configuration.md`, `guides/local-storage.md`, `guides/cloud-storage.md`, `guides/ssl_verification.md`, `resources/*` | Configuración, caché y red | `EDGAR_LOCAL_DATA_DIR` (por defecto `~/.edgar`), `EDGAR_USE_LOCAL_DATA`, `EDGAR_RATE_LIMIT_PER_SEC=9`, `EDGAR_HTTP_TIMEOUT=30`, `EDGAR_USE_HTTP2`, `EDGAR_VERIFY_SSL`, `EDGAR_USE_SYSTEM_CERTS`, `use_local_storage`, `configure_http`, `download_edgar_data`, `download_filings`, `diagnose_ssl`, `get_request_stats`; la caché HTTP de `/Archives` es indefinida |
| `docs/guides/error-handling.md` | Jerarquía de errores y significado de `None` | `EdgarError` → `TransportError` (`status_code`), `NotFoundError`, `ParsingError`, `ValidationError`; `report.get(item, default)` |
| `docs/contributing.md`, `testing-guide.md`, `verification-constitution.md`, `verification-guide.md`, `beads-workflow.md` | Gobierno del desarrollo | Hatch (`test-fast/network/slow/regression`, `cov`), *markers*, reglas de *cassettes* VCR, *conventional commits*, formato del CHANGELOG, `docs/upgrade/<major>.md`, 11 principios de verificación, *Definition of Done*, Beads (`bd`) |
| `docs/verification-{gap-analysis,roadmap,survey,weaknesses}.md`, `ty-quality-check-report.md`, `invalid-return-type-*.md` (firmas) | Autoauditoría de calidad | CI con Python 3.10–3.13; 1.346 diagnósticos de `ty`; 719 *asserts* que solo comprueban existencia; agentes `.claude/agents/{test-specialist,bug-hunter,issue-handler,edgartools-architect,docs-writer}.md` |
| `docs/ai/index.md`, `ai/skills.md`, `ai/mcp-setup.md`, `ai/mcp-tools.md`, `ai/mcp-workflows.md`, `ai-integration.md`, `blog/edgartools-mcp-server.md` | IA: servidor MCP (13 herramientas), skills y contexto para LLM | `to_context('minimal|standard|full')`, `to_markdown(detail, optimize_for_llm)`, `tenk.notes.to_markdown(focus='Debt')`, `.docs.search`, `edgar.ai.install_skill()` (instala en `~/.claude/skills/edgartools/`), `package_skill()`, `claude mcp add edgartools -- uvx --from "edgartools[ai]" edgartools-mcp`, `edgar_company/trends/compare/read/notes` |
| `docs/to-context-guidelines.md` | Norma del formato de contexto para LLM | Formato Markdown-KV, *skip-if-None*, bloque `AVAILABLE ACTIONS`, presupuesto de tokens por nivel, `_format_currency` |
| `docs/advanced/customizing-standardization.md` (firmas) | Mapeos propios (doc **anticuado, de la v4**) | `MappingStore`, `ConceptMapper`, `{ticker}_mappings.json`, `add_custom_resolver`; funciones que figuran como «futuras» (`MappingValidator`, `MLConceptMapper`) |
| `docs/guides/*` de fondos y otros formularios (25 archivos, firmas) | Objetos de otros formularios | `Fund`, `FundSeries`, `NPORT`, `NPX`, `Prospectus424B`, `RegistrationS1/S3`, `SixK`, `FortyF`, `Correspondence` (cartas de comentarios), `Form144`, `TenD` |
| `docs/archive/*` (6), quick-refs `StatementType|PeriodType|FormType`, `xbrl-querying.md`, `getting-xbrl.md`, `table-column-width.md`, `concepts/sec-filings.md`, `notebooks.md`, `architecture-diagram.md` (Mermaid) | Material histórico y de referencia | Enums `FormType`, `PeriodType`, `StatementType`; `doc.text(table_max_col_width=)` |
| `docs/sec/schedule13/*` (4 md + 1 pdf) | Especificación XML 13D/G de la SEC | Esquema, códigos y ejemplos |
| `docs/examples/plot_revenue.py` | Gráfico de 5 años (ingresos, margen bruto, beneficio neto, márgenes) con matplotlib | `plot_revenue_simple`, `plot_revenue_complex` (XBRLS); filtra por la etiqueta `"Revenue"`, lo que es frágil |
| `docs/examples/*.py` (resto) y `user_journeys.md`, `snippets.md` | Demos de enums, fondos, Form C y Form 4 a escala | `insider_transactions.py` (`filings.download()`, `summary.to_dataframe(detailed=True)`); `user_journeys.md` contiene código obsoleto (`filing.chunk_text`) |
| `examples/` (13) | Scripts y README | `scripts/advanced/section_detection_demo.py` (`parse_html`, `ParserConfig`, `DetectionThresholds`, `section.confidence`), `ranking_search_examples.py`, `enterprise_config.py` (perfiles por `os.environ`), `scripts/ai/*` (API antigua `company.text(detail, max_tokens)`), `table_width_example.py` (`doc.text(clean, include_tables, max_length)`) |
| `notebooks/` (56) y `docs/Usage.ipynb` | Tutoriales para Colab | Clave: `extract-revenue-earnings` (`get_annual_fact`, `list_supported_concepts`, `discover_concept_tags`), `financial-statements-to-dataframe` (`get_quarterly_statements`, multi-índice Ticker/Period), `revenue-segment-hierarchy`, `10k-business-description` (`tenk.sections['part_i_item_1']`), `8k-earnings-release`, `proxy-statement-def14a`, `sec-industry-sic-code`, `sec-comment-letters`, `Reading-Data-From-XBRL` (`facts_history`) |
| `docs/images/` (156) + `docs/edgartools-demo.mp4` | Capturas de pantalla (webp/png/jpg), gif/mp4 de demo, iconos, *badges* y logo en svg | Ilustración de la documentación; `MSFT_financial_complex.png` es un ejemplo de gráfico de barras + márgenes. Sin valor para el proyecto, más allá de inspiración visual |
| `docs/stylesheets/extra.css`, `javascripts/nav-enhance.js`, `requirements.txt` | Tema de mkdocs-material | `mkdocs>=1.5`, `mkdocs-material>=9` |

## Reutilizable para el proyecto

| Necesidad | Ruta exacta y símbolo | Cómo reutilizar | Notas |
|---|---|---|---|
| Capa 1: estados multianuales (A1, A4 y §6 de estructura-informe) | `docs/xbrl/guides/multi-period-analysis.md` → `XBRLS.from_filings(...).statements.*(max_periods=5)` + `set_index("standard_concept")`; `docs/guides/company-facts.md` → `company.income_statement(periods=10, annual=True, as_dataframe=True)` | pip (`edgartools`) | XBRLS conserva el filing de origen; Facts sirve para la serie larga (A4, unos 10 años) |
| Capa 1: trazabilidad de cada cifra (principio 3 del plan) | `docs/api/entity-facts-reference.md` → `FinancialFact.accession/filing_date/form_type/concept`; columnas `concept`/`standard_concept` de `to_dataframe()` | pip | Guardar en el *snapshot* el concepto, el *accession* y la fecha |
| Capa 1: texto del 10-K (§4, §8 y MD&A) | `notebooks/10k-business-description-python.ipynb` → `tenk.sections.get('part_i_item_1'/'part_i_item_1a'/'part_ii_item_7')`; `tenk.business/risk_factors/management_discussion`; `tenq["Part I, Item 2"]` | pip | Usar las claves canónicas (`upgrade/6.0.md`) |
| Capa 1: portada y *market data* (§1) | `docs/guides/business-overview-data-sources-guide.md` → `CompanyOverview`; `company.shares_outstanding`, `fiscal_year_end`, `sic` | Idea / copiar con atribución MIT | El precio no viene de aquí (ver «Lo que NO contiene») |
| Capa 1: segmentos e ingresos por línea (§4, §6) | `notebooks/revenue-segment-hierarchy-python.ipynb` (`level`, `parent_concept`, `view="detailed"`); `docs/xbrl/concepts/dimension-handling.md` (`MajorCustomersAxis` para concentración de clientes) | Idea + pip | |
| Capa 1: deuda, notas y arrendamientos (§6) | `docs/ai/index.md` → `tenk.notes.to_markdown(focus='Debt')`; conceptos `OperatingLeaseCommitmentYear1..5`, `ShortTermDebt`, `LongTermDebt` | pip | |
| Capa 1: TTM y *splits* | `docs/guides/stock-splits-eps-normalization.md` → `get_ttm`, `detect_splits`, `apply_split_adjustments` | pip | BPA homogéneo para el histórico |
| Capa 1: gobierno corporativo (§9) | `docs/guides/proxystatement-data-object-guide.md` → `executive_compensation`, `pay_vs_performance`, `insider_trading_policy_adopted`; `tenk.auditor` | pip | El consejo y la independencia hay que construirlos (HTML) |
| Capa 1: accionariado (§1, §9) | Guías 13D/G y Form 4 → `total_percent`, `get_ownership_summary()` | pip | |
| Capa 1: guía y ajustes no-GAAP (§6, EBITDA recurrente) | `docs/eightk-filings.md` → `earnings.guidance`, `earnings.eps_reconciliation`, `segment_data` | pip | Solo cuando el *press release* lo publica |
| Capa 1: avisos de nuevo 10-Q/10-K (C1) | `notebooks/monitor-sec-filings-python.ipynb` → `get_current_filings().filter(cik=...)`; `company.get_filings(form=...).latest()` | Idea | |
| Capa 1: filtrar sectores con contabilidad distinta y emisores 20-F (riesgos D) | `docs/guides/company-classification.md` → `business_category`, `is_financial_institution()`, `is_foreign` | pip | Excluir bancos y aseguradoras, o desviarlos a otra plantilla |
| Capa 2: métricas base | `financials.get_financial_metrics()`, `get_free_cash_flow()`; los 95 conceptos de `docs/xbrl/concepts/standardization.md` | pip | Sin EBITDA ni EV; se calculan en capa 2 o con edgar_analytics |
| Capa 2: comparables (A5) | `docs/guides/reference-data.md` → `get_companies_by_industry(sic=)`; `notebooks/financial-statements-to-dataframe.ipynb` → `get_quarterly_statements()` | pip + copiar con atribución MIT | Encaja con la selección automática por SIC (E5) |
| Capa 3: gráficos (§3) | `docs/examples/plot_revenue.py` | Solo idea (portar a Plotly) | El cálculo de márgenes y crecimientos es reutilizable |
| Capa 3/plantilla: signos y negativos entre paréntesis (A8) | `to_dataframe(presentation=True)`, columna `preferred_sign` (`docs/api/xbrl.md`) | pip | |
| Capa 4: contexto para el LLM | `docs/to-context-guidelines.md` (Markdown-KV, *skip-if-None*); `Statement.to_markdown(detail='minimal')`; `doc.text(clean=True, include_tables=True, max_length=)` | Idea + pip | Datos compactos para los prompts |
| Capa 4: citas literales del 10-K (principio 3 y B9) | `docs/advanced-search.md` → `DocumentSearch.ranked_search(..., in_section="Risk Factors")`, `result.snippet/section` | pip | Recuperación BM25 sin base vectorial: alternativa a `src/rag` |
| Capa 4: validar la IA y el parser | `FilingViewer.compare_context(xbrl, statement=...)`; `examples/scripts/advanced/section_detection_demo.py` (`section.confidence`) | pip | |
| UI Streamlit | `docs/common-pitfalls.md` (importar `edgar` en el hilo principal); `docs/guides/error-handling.md` (`TransportError` frente a `NotFoundError`, para los mensajes de estado del dashboard) | Idea | Streamlit ejecuta el script en hilos |
| Versiones y snapshot | `docs/configuration.md` → `EDGAR_LOCAL_DATA_DIR`, `use_local_storage`; caché indefinida de `/Archives` | pip/config | Poner la ruta fuera de OneDrive (C6) |
| CI y tests | `docs/verification-guide.md` (aserción contra *ground truth*: AAPL FY2024 revenue `391035000000`, accession `0000320193-24-000123`); `docs/contributing.md` (VCR); `EDGARTOOLS_STRICT_ERRORS=1 pytest` | Idea | Coincide con el hito de la fase 2 del plan |
| Docs y onboarding | `docs/common-pitfalls.md`, `choosing-the-right-api.md`, `upgrade/6.0.md`, estructura de `mkdocs.yml` | Idea | |
| Gobierno de agentes IA | `docs/ai/skills.md` → `install_skill()`; `docs/verification-roadmap.md` (`CLAUDE.md`, `.claude/agents/*`); `docs/beads-workflow.md` | pip (skill) + idea | La skill de edgartools para Claude Code se instala sin coste |

## Patrones de organización y onboarding

- **La documentación es la especificación** (`verification-constitution.md`): cada ejemplo documentado debe poder ejecutarse como test (`tests/test_documented_examples.py`), y cada funcionalidad se da por terminada con una aserción contra datos reales, un ejemplo documentado, una comprobación de silencio (que no devuelva `None` en vez de fallar) y una entrada en las skills. **Trasladable** tal cual a `docs/` y `tests/` del proyecto.
- **Tests por niveles con *markers*** (`fast`, `network`, `slow`, `regression`, `vcr`) asignados automáticamente por nombre de archivo en `conftest.py`. Las *cassettes* VCR se graban contra la SEC real y no se editan nunca. La cobertura de los grupos se combina en CI. Trasladable: tests de cálculo como `fast` y tests de ingesta con *cassettes*.
- **Una página de páginas «elige esta API»** (`choosing-the-right-api.md`) y otra de **errores frecuentes** (`common-pitfalls.md`). Muy útiles para una persona nueva.
- **Guía de migración por símbolo** (`upgrade/6.0.md`, con su `sed` mecánico) y **reglas del CHANGELOG** (síntoma primero, un dato real de referencia, `(GH #NNN)`).
- **Configuración solo por variables de entorno**, documentadas en una tabla resumen con un ejemplo de `.env` y perfiles por entorno.
- **Mensajes de error con dos preguntas** («¿respondió la SEC?», «¿la entrada estaba mal?»). Aplicable a los estados de la UI.
- **Gobierno de agentes:** `CLAUDE.md` + `.claude/agents/*` + skills instalables + slash commands `/task` y `/triage` sobre Beads. El patrón es trasladable (`CLAUDE.md` del proyecto + agentes de test y docs).
- **Puntos débiles:** documentación muy extensa y con algunos ejemplos inconsistentes. Sirve como advertencia de que hay que verificar la documentación.

## Lo que NO contiene

Verificado con grep sobre los `.md`, `.py` e `.ipynb` del alcance:

- **Precio y datos de mercado:** no hay proveedor de precios. `yfinance` solo aparece como ejemplo externo en `track-form4.md` y no se cubre el comportamiento relativo en bolsa.
- **Valoración:** no hay EV, EV/EBITDA, PER, DCF, WACC, beta ni sensibilidad (0 resultados para «enterprise value», «WACC» o «EV/EBITDA»).
- **Proyecciones (años «e»):** no hay modelo de proyecciones ni de *forecasting*.
- **EBITDA:** no hay concepto estándar de EBITDA en los 95. Solo aparece en la salida `list_supported_concepts()` del notebook `extract-revenue-earnings-python.ipynb`; hay que verificarlo en el código.
- **PDF y plantilla:** no se mencionan WeasyPrint, reportlab ni kaleido. Jinja2 solo aparece como dependencia en las salidas de los notebooks; no hay plantilla HTML de informe.
- **Visualización:** no hay estilo Plotly reutilizable. Plotly solo aparece en un ejemplo de Streamlit trivial dentro de `multi-year-financial-data-api.md`.
- **Persistencia y versiones:** no hay SQLAlchemy ni modelos de persistencia; SQLite solo aparece como *rate limiter* de los tests.
- **UI y editor:** no hay editor de bloques ni UI. Streamlit aparece en un único fragmento de ejemplo.
- **Gobierno corporativo estructurado:** no hay consejo, independencia ni comisión de auditoría estructurados («planned» en la guía de proxy).
- **Mercado e industria (§5):** no hay datos de tamaño ni crecimiento sectorial (CAGR).
- **Disclaimer legal:** no hay ningún texto legal de informe.

## Riesgos

- **Licencia:** MIT. Se puede copiar código de las docs y los notebooks conservando el aviso de copyright.
- **Migración a la 6.0 (en desarrollo):**
  - se eliminan `cashflow_statement()`/`cash_flow()`, `edgar.files`, `chunked_document`, `include_page_breaks`, el `period_length` de `EntityFacts` y los modos de acceso;
  - `get_financials()` sin XBRL pasará a lanzar una excepción;
  - cambian las claves y el contenido de las secciones del 10-K.

  Recomendación: fijar `edgartools>=5.x,<6` (coherente con edgar_analytics), usar solo `cash_flow_statement()` y las claves canónicas, y ejecutar los tests con `EDGARTOOLS_STRICT_ERRORS=1`.
- **Calidad de la documentación (verificar antes de copiar):**
  - `api/company.md` usa `financials.income.loc[...]` y `get_filings(limit=)`, que son obsoletos;
  - `examples/scripts/ai/*` usa `company.text(max_tokens=)`, cuando la API actual es `to_context`;
  - `customizing-standardization.md` es de la v4 y describe funciones que nunca llegaron;
  - `user_journeys.md` usa `filing.chunk_text`;
  - la unidad de `Value` en 13F es contradictoria (miles en `common-pitfalls`, dólares en la guía de 13F);
  - hay cifras de ejemplo dudosas: MSFT con 375 B$ y +53 % en `mcp-tools.md`, y un capex de NVDA de 129 M$ en una salida de notebook;
  - los métodos `calculate_ratios/peer_comparison/detect_anomalies` que cita `company-facts.md` están sin verificar.

  La documentación del propio repo reconoce 1.346 diagnósticos de tipos y 719 *asserts* que solo comprueban existencia. Hay que validar las métricas contra el 10-K (AAPL).
- **Windows y Python 3.13:** la CI documentada cubre Python 3.10–3.13 (3.14 no consta) y no se dice el sistema operativo.
  - El directorio de datos por defecto es `~/.edgar`; conviene fijar `EDGAR_LOCAL_DATA_DIR` fuera de OneDrive.
  - En redes corporativas puede hacer falta `EDGAR_USE_SYSTEM_CERTS`.
  - Al usar hilos (Streamlit), importar `edgar` antes.
- **Dependencias y rendimiento:**
  - el extra `[ai]` es pesado y solo hace falta para el servidor MCP;
  - la SEC limita a unas 9-10 peticiones por segundo; para lotes, `use_local_storage` (la descarga completa ocupa unos 24 GB);
  - `EntityFacts` y `XBRLS` tardan de 1 a 15 s por empresa, así que hay que cachear y guardar el *snapshot*.
- **Datos:** algunas empresas reportan solo con valores dimensionales; con `view="summary"` pueden aparecer NaN. Los estados en 10-K/A pueden estar incompletos (usar `amendments=False`). Las etiquetas varían entre empresas, así que conviene filtrar por `standard_concept`.
