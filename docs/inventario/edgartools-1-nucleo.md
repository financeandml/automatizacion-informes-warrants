# edgartools-1-nucleo

- **Repo / alcance / licencia:** `edgartools-main` (v5.61.1, `edgar/__about__.py`), de Dwight Gunning. Esta parte cubre `edgar/*.py` (raíz del paquete), `entity/`, `company_reports/`, `files/`, `sgml/`, `storage/`, `search/`, `display/`, `abs/`, `ats/`, `diagnose_ssl/`, `docs/`, `muniadvisors/`, `npx/`, `tender_offers/` y `vendored/`. **Licencia MIT** (`LICENSE.txt`). La excepción es `vendored/uu.py`, que tiene licencia permisiva histórica de CPython (Lance Ellinghouse/CWI). Requiere Python >=3.10 y declara compatibilidad con 3.10-3.14.
- **Cobertura:** 194 archivos (137 `.py`, 32 `.md`, 24 `.json` y 1 `py.typed`).
  - **Leídos completos: 34.** Son 30 `.py`: `__about__`, `storage_management`, `shelfofferings`, `_cli`, `config`, `effect`, `context`, `form144`, `_compat`, `urls`, `_markdown`, `forms`, `company_reports/auditor`, `entity/tools`, `entity/tickers`, `diagnose_ssl/__main__`, `storage/datamule/documents` y 13 `__init__.py`. A ellos se suman 3 `.md` (`XBRL_TABLE_DEDUPLICATION`, `COLOR_SCHEMES`, `training/README`) y `py.typed`, que está vacío.
  - **Solo firmas: 136.** Son 107 `.py` y 29 `.md`. De cada `.py` se sacaron con AST, sin ejecutar nada, el docstring, las constantes, las clases, los métodos y propiedades públicos y los argumentos. Además se leyeron los cuerpos relevantes para el proyecto: `Financials`, `Company`, `EntityFacts`, `TenK`, `CompanyReport`, `settings`, `httpclient` y `Filing.save/load/from_sgml`. De cada `.md` se leyeron los encabezados y el inicio.
  - **Por muestreo: 24 JSON** de `entity/data/` (claves, metadatos y primer nodo).
  - Suma: 34 + 136 + 24 = **194**.

## Qué contiene

### Raíz `edgar/*.py` (36)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `__init__.py` | Fachada pública (129 nombres en `__all__`). `obj()` enruta cada formulario a su clase (10-K→TenK, 8-K→EightK, DEF 14A→ProxyStatement…) | `Company`, `Filing`, `Filings`, `get_filings`, `find`, `obj`, `get_obj_info`, `matches_form`, `compose_context`, `set_identity`, `use_local_storage`, `XBRL`, `Financials`, `MultiFinancials` |
| `__about__.py` | Versión | `__version__='5.61.1'` |
| `_filings.py` | Índices trimestrales de la SEC, contenedor `Filings` y objeto `Filing` | `get_filings(year,quarter,form,…)`, `Filings.filter/latest/to_pandas/save_parquet`, `Filing.xbrl()/obj()/attachments/exhibits/markdown()/text()/sgml()/save()/load()/from_sgml()/to_dict()/search()/grep()/to_context()`, `get_by_accession_number` |
| `financials.py` | Estados financieros de un filing (XBRL) y cosido multiperiodo | `Financials.extract(filing)`, `.balance_sheet/income_statement/cash_flow_statement/statement_of_equity/comprehensive_income(include_dimensions,view)`, `get_revenue/get_net_income/get_operating_income/get_free_cash_flow/get_capital_expenditures/get_shares_outstanding_basic/diluted(period_offset)`, `get_financial_metrics()`, `MultiFinancials.extract(filings)` |
| `earnings.py` | Parser de tablas de notas de resultados (8-K EX-99.1) | `EarningsRelease.from_filing`, `.income_statement/.balance_sheet/.cash_flow_statement/.segment_data/.guidance/.eps_reconciliation`, `get_key_metrics()`, `FinancialTable.to_html/to_json/to_markdown/to_csv/to_facts_dataframe`, `Scale.detect`, `get_earnings_tables` |
| `context.py` | Compone objetos en un único contexto para LLM con presupuesto de tokens | `HasContext` (Protocol `to_context(detail)`), `compose_context(objects,max_tokens,detail)` |
| `settings.py` | Identidad SEC (User-Agent) y directorio de datos | `set_identity`, `get_identity` (si falta `EDGAR_IDENTITY`, llama a `ask_for_identity`, que es interactivo), `get_edgar_data_directory`; `NORMAL/CAUTION/CRAWL` están obsoletos |
| `config.py` | URLs y espejos configurables por entorno | `SEC_BASE_URL`, `SEC_DATA_URL`, `SEC_XBRL_URL`, `VERBOSE_EXCEPTIONS` (`EDGAR_*`) |
| `paths.py` | Rutas centralizadas | `EDGAR_LOCAL_DATA_DIR` (~/.edgar), `EDGAR_CACHE_DIR`, `EDGAR_TEST_DIR`, `CLAUDE_SKILLS_DIR`; `set_data_directory`, `get_claude_skills_directory` |
| `httpclient.py` | Cliente httpx con caché y *throttle* (httpxthrottlecache) | `CACHE_RULES` (Archives: siempre; submissions/companyfacts: 30 s; índices: 30 min), `configure_http(verify_ssl,use_system_certs,proxy,timeout,http2)`, `get_edgar_rate_limit_per_sec` (9/s), caché en `~/.edgar/_tcache` |
| `httprequests.py` | GET/POST con reintentos (stamina), identidad y diagnóstico SSL | `get_with_retry`, `download_json`, `download_text`, `download_file`, `stream_file`, `SSLVerificationError` |
| `exceptions.py` | Jerarquía única de errores | `EdgarError` → `TransportError` (`TooManyRequestsError`, `IdentityError`), `NotFoundError` (`CompanyNotFoundError`, `StatementNotFoundError`, `SectionNotFoundError`…), `ParsingError`, `ValidationError`; `EDGARTOOLS_STRICT_ERRORS` |
| `enums.py` | Enums con autocompletado y validación difusa | `FormType`, `PeriodType`, `StatementType`, `FilerStatus`, `FilerCategory`, `validate_form_type`, `fuzzy_match` |
| `attachments.py` | Adjuntos de un filing, consulta y servidor local | `Attachments.query/exhibits/primary_html_document/download/serve`, `Attachment.text()/markdown()/content`, `FilingHomepage` |
| `core.py` | Utilidades varias (obsoletas en parte) | `DataPager`, `listify`, `run_async_or_sync` (nest_asyncio), `parallel_thread_map`, `cache_except_none` |
| `correspondence.py` | Cartas SEC↔empresa (CORRESP/UPLOAD) en hilos | `Correspondence.from_filing`, `CorrespondenceThread`, `to_context` |
| `current_filings.py` | Feed de filings del día (Atom) | `get_current_filings(form,…)`, `get_all_current_filings`, `iter_current_filings_pages`, `CurrentFilings` |
| `datatools.py` | Utilidades pandas/pyarrow | `table_html_to_dataframe`, `markdown_to_dataframe`, `dataframe_to_text`, `apply_declared_schema`, `convert_to_numeric` |
| `dates.py` | Fechas y trimestres naturales | `extract_dates`, `filing_date_to_year_quarters`, `current_year_and_quarter`, `parse_acceptance_datetime` |
| `filtering.py` | Filtros de tablas de filings | `filter_by_date/form/cik/ticker/exchange/year/quarter` |
| `filesystem.py` | Almacenamiento en la nube (fsspec) | `use_cloud_storage(uri)`, `EdgarPath`, `sync_to_cloud` |
| `headers.py` | Cabeceras de índice (pydantic) | `IndexHeaders.load`, `FilingDirectory` |
| `markdown.py` | HTML de la SEC → Markdown limpio (tablas, ruido, paginación) | `process_content`, `html_to_json`, `create_markdown_table`, `clean_text` |
| `_markdown.py` | Markdown → rich (terminal) | `markdown_to_rich`, `MarkdownContent` |
| `richtools.py` | Render rich y documentación por clase | `Docs` (`.docs` con búsqueda BM25), `df_to_rich_table`, `rich_to_svg/png`, `repr_rich` |
| `xmlfiling.py` | Filings XML genéricos con XSLT | `XmlFiling.from_filing/to_html/to_context` |
| `xmltools.py` | Helpers XML compartidos | `parse_xml`, `child_text`, `optional_decimal` |
| `_party.py` | Modelos de dirección/persona/emisor | `Address`, `Issuer`, `Person`, `Contact` |
| `forms.py` | Catálogo de formularios SEC (scraping de sec.gov/forms) | `list_forms`, `SecForms`, `SecForm` |
| `urls.py` | Constructores de URL | `build_submissions_url`, `build_company_facts_url`, `build_archive_url` |
| `_compat.py` | Alias obsoletos con aviso | `deprecated_alias` |
| `_cli.py` | Script `edgartools mcp` | `main(argv)` (necesita el extra `[ai]`) |
| `effect.py`, `form144.py` | *Shims* obsoletos hacia `offerings/` y `ownership/` (desaparecen en 6.0) | `__getattr__` PEP 562 |
| `shelfofferings.py` | Lista de formularios de colocación (424B…) | `list_takedown_forms` |
| `storage_management.py` | *Shim* hacia `storage/_management` | — |

### `entity/` (28 `.py`, 18 `.md`, 24 `.json`)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `entity/core.py` | Modelo de dominio de emisores | `Company(ticker)`: `get_financials()`, `get_quarterly_financials()`, `income_statement/balance_sheet/cash_flow_statement(periods,period='annual'|'quarterly'|'ttm',as_dataframe,concise_format)`, `get_ttm(concept,as_of)`, `get_ttm_revenue/net_income`, `shares_outstanding`, `public_float`, `fiscal_year_end`, `sic`, `industry`, `business_category`, `is_financial_institution()`, `latest_tenk/latest_tenq`, `proxy_season()`, `get_filings(form,…)`, `to_context`; `Entity.filer_category`, `get_entity`, `get_company` |
| `entity/entity_facts.py` | API de Company Facts (todas las cifras XBRL históricas) | `EntityFacts.to_dataframe(include_metadata,pit_mode)`, `time_series(concept,periods)`, `get_fact`, `get_annual_fact`, `get_concept`, `dei_facts(as_of)`, `query()`, `income_statement/balance_sheet/cash_flow_statement(periods,annual)`, `search_concepts`, `available_periods`, `to_llm_context`; **`calculate_ratios`, `peer_comparison` y `detect_anomalies` son marcadores vacíos («Phase 3»)**; `get_company_facts(cik)` |
| `entity/query.py` | Consultas encadenadas sobre hechos | `FactQuery.by_concept/by_fiscal_year/by_fiscal_period/by_form_type/as_of/latest_periods/high_quality_only/pivot_by_period/to_dataframe` |
| `entity/models.py` | Hecho unificado con trazabilidad | `FinancialFact` (`concept`, `value`, `unit`, `period_start/end`, `fiscal_year/period`, `filing_date`, `form_type`, `accession`, `is_restated`, `dimensions`), `ConceptSearchResults`, `PeriodSummary` |
| `entity/enhanced_statement.py` | Estados multiperiodo jerárquicos | `MultiPeriodStatement.to_dataframe/to_dict/get_period_comparison/to_llm_context`, `EnhancedStatementBuilder`, `detect_fiscal_year_end`, `calculate_fiscal_year_for_label` |
| `entity/statement.py` | DataFrame con formato por concepto | `FinancialStatement.calculate_growth/format_value/to_numeric`, `_repr_html_` (vía `to_html`) |
| `entity/statement_builder.py` | Reconstruye estados con plantillas canónicas | `StatementBuilder.build_statement`, `StructuredStatement` |
| `entity/mappings_loader.py` | Carga los mapeos aprendidos y las extensiones sectoriales | `load_learned_mappings`, `load_virtual_trees`, `get_industry(sic,ticker)`, `load_industry_extension`, `get_concept_statements` |
| `entity/categorization.py` | Clasifica el tipo de negocio | `BusinessCategory`, `classify_business_category(sic,…)`, `classify_reit_subtype`, `SIC_CODES_BANK/INSURANCE/REIT` |
| `entity/unit_handling.py` | Normalización de unidades y escalas | `UnitNormalizer`, `apply_scale_factor`, `is_per_share_label` |
| `entity/filings.py` | Filings de una entidad | `EntityFilings.filter/latest`, `EntityFiling.related_filings/parsed_items` |
| `entity/data.py`, `submissions.py`, `parser.py` | Submissions API → `EntityData`/`CompanyData`; parser de facts | `parse_entity_submissions`, `get_entity_submissions`, `EntityFactsParser.parse_company_facts` |
| `entity/search.py`, `tickers.py`, `tools.py` | Búsqueda por nombre, mapa ticker→CIK y atajos | `find_company`, `CompanySearchIndex`, `get_ticker_to_cik_lookup`, `income_statement(ticker)` |
| `entity/constants.py`, `utils.py`, `dataframe_schema.py`, `terminal_styles.py`, `__init__.py` | Constantes de formularios, CIK, esquemas declarados, colores de terminal y reexportación | `normalize_cik`, `ENTITY_FACTS_CORE`, `SCHEMES` |
| `entity/training/*.py` (5) | Pipeline offline que aprende mapeos concepto→estado | `ConceptLearner`, `run_industry_learning`, `deploy_canonical`, `view.main` |
| `entity/data/process_mappings.py` | Simplifica las estructuras aprendidas | `process_mappings()` |
| `entity/data/*.json` (5, muestreo) | Mapeos aprendidos: `learned_mappings` (106 conceptos), `statement_mappings_v1` (114), `virtual_trees` (5 estados), `concept_linkages` (7.069 conceptos de 331 empresas) e `industry_mappings` (SIC→sector) | datos del pipeline |
| `entity/data/industry_extensions/*.json` (19, muestreo) | Árboles por sector (banca, seguros, REIT, energía, tecnología…) con `sic_ranges` y nº de empresas analizadas | `metadata`, `BalanceSheet`, `IncomeStatement`… |
| `entity/CLAUDE.md` | Guía para asistentes IA: arquitectura, tareas típicas, bugs, *snippets* de reproducción, convenciones y flujo de corrección | — |
| `entity/README.md`, `entity/docs/{Company,EntityFiling,EntityFilings}.md` | Documentación de usuario por clase (la muestra `.docs`) | — |
| `entity/COLOR_SCHEMES.md`, `XBRL_TABLE_DEDUPLICATION.md` | Esquemas de color de terminal; deduplicación de `Statement [Table]` | `EDGAR_FINANCIALS_COLOR_SCHEME` |
| `entity/.docs/**` (12) y `entity/training/{GUIDE,PER_COMPANY_DATABASE_GUIDE}.md` | Diseño interno: especificación del JSON de company facts, duplicados, bug #408 (anual vs trimestral), plan de mejora y aprendizaje | — |

### `company_reports/` (12 `.py`, 1 `.md`)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `ten_k.py` | 10-K por Items | `TenK.business` (Item 1), `.risk_factors` (1A), `.management_discussion` (7), `.directors_officers_and_governance` (10), `.subsidiaries` (EX-21), `['Item 7A']`, `get_item_with_part`, `to_context(detail,focus='debt'|…)` |
| `ten_q.py` | 10-Q por Partes e Items | `TenQ['Part I']`, `get_item_with_part`, `to_context` |
| `_base.py` | Base común de los informes | `CompanyReport.financials`, `.auditor`, `.notes` (`notes['Debt']`), `.get(item,default)`, `.document`, `.period_of_report`, `grep` |
| `auditor.py` | Auditor desde DEI XBRL | `AuditorInfo(name,location,firm_id,icfr_attestation)`, `extract_auditor_info(xbrl)` |
| `current_report.py` | 8-K/6-K | `CurrentReport`/`EightK`: `.items`, `.earnings`, `.has_earnings`, `.press_releases`, `get_exhibit`, `date_of_report` |
| `press_release.py` | Notas de prensa del 8-K | `PressReleases`, `PressRelease.text/to_markdown` |
| `subsidiaries.py` | Parser de EX-21 | `parse_subsidiaries`, `SubsidiaryList.to_dataframe` |
| `twenty_f.py`, `forty_f.py`, `sixk.py` | Emisores extranjeros | `TwentyF.risk_factors/business/operating_review/major_shareholders`, `FortyF.mda_text`, `SixK.financials` |
| `_structures.py`, `__init__.py` | Estructura Parte/Item válida por formulario; reexportación | `FilingStructure`, `is_valid_item_for_filing` |
| `docs/UI-Guide.md` | Guía para pintar un 8-K en una app: modelo de datos por pantalla, *badges*, IA y monitorización | — |

### `sgml/` (10 `.py`, 3 `.md`)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `sgml_common.py` | Envío completo (.txt SGML): cabecera, documentos y descarga | `FilingSGML.from_source/from_filing/attachments/filing_summary/download(path,archive)`, `parse_submission_text` |
| `sgml_parser.py`, `sgml_header.py` | Parsers SGML (formatos moderno y antiguo) y cabecera | `SGMLParser`, `SGMLDocument`, `FilingHeader.parse_from_sgml_text` |
| `filing_summary.py` | FilingSummary.xml e informes R*.htm | `FilingSummary.parse`, `Reports.get_by_category`, `Statements.balance_sheet/income_statement/cash_flow_statement`, `Report.to_dataframe` |
| `concept_extractor.py` | Filas de R*.htm con su concepto XBRL anotado | `extract_concepts_from_report(html,form)`, `ConceptReport.get_by_concept`, `ConceptRow.numeric_values` |
| `metalinks.py` | MetaLinks.json: etiquetas, cálculo y referencias FASB | `MetaLinks.parse/get_calculation_tree/get_auth_refs_for_tag/search` |
| `table_to_dataframe.py` | Tabla de R*.htm → DataFrame | `FinancialTableExtractor`, `extract_statement_dataframe` |
| `text_extraction.py`, `tools.py`, `__init__.py` | Texto del documento principal y utilidades | `primary_document_text`, `html_to_text`, `decode_uu` |
| `*.md` (3) | FilingSummary y estructura de cabeceras SEC | — |

### `files/` (11 `.py`, 3 `.md`): parsers HTML antiguos, **obsoletos**
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `html.py`, `htmltools.py`, `html_documents.py`, `markdown.py`, `page_breaks.py`, `styles.py`, `tables.py`, `text.py`, `docs/filing_document.py` | Parsers anteriores a `edgar.documents` (que queda fuera de este alcance). Emiten `warn_legacy_html_usage` | `Document.parse`, `ChunkedDocument`, `HtmlDocument`, `to_markdown`, `PageBreakDetector`, `FilingDocument.items` |
| `_deprecation.py`, `__init__.py` | Avisos de obsolescencia | `warn_legacy_html_usage` |
| `docs/*.md` (3) | Diseño de extracción de Items y troceado (*chunking*) | — |

### `search/` (5 `.py`, 1 `.md`)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `efts.py` | Búsqueda de texto completo de EDGAR | `search_filings(query,forms,items,cik,ticker,start_date,end_date,limit)`, `EFTSSearch.filter/to_filings/to_context` |
| `textsearch.py` | BM25/regex dentro de un documento | `BM25Search`, `RegexSearch`, `SimilaritySearchIndex` |
| `datasearch.py`, `grep.py`, `__init__.py` | Índice difuso de nombre/ticker; grep exacto | `FastSearch`, `GrepResult.to_context` |
| `.docs/fastsearch-improvements.md` | Análisis de mejoras de FastSearch | — |

### `storage/` (8 `.py`)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `_local.py` | Copia local masiva (offline) de submissions, facts y filings | `use_local_storage(path,allow_network_fallback)`, `download_edgar_data`, `download_filings`, `download_facts` |
| `_management.py` | Análisis y limpieza del almacenamiento | `storage_info`, `analyze_storage`, `cleanup_storage`, `clear_cache` |
| `datamule/*` (4) | Fuente alternativa con tar de datamule (zstd) | `use_datamule_storage`, `load_filing_from_tar`, `TarSGMLDocument` |
| `__init__.py` | Reexportación | — |

### `display/` (4 `.py`)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `formatting.py` | Formato de cifras e identificadores | `moneyfmt(value,places,curr,sep,dp,pos,neg)`, `format_currency_short`, `datefmt`, `cik_text` |
| `styles.py`, `demo.py`, `__init__.py` | Lenguaje visual de terminal (rich) | `PALETTE`, `SYMBOLS`, `styled`, `source_text` |

### Paquetes de formularios ajenos al informe
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `abs/` (4) | 10-D, ABS-EE, CMBS | `TenD`, `CMBSAssetData`, `AutoLeaseAssetData` |
| `ats/` (3) | ATS-N (*dark pools*) | `AlternativeTradingSystem`, modelos pydantic |
| `muniadvisors/` (2) | MA-I, asesores municipales | `MunicipalAdvisorForm` |
| `npx/` (4) | N-PX, votos de fondos en juntas | `NPX`, `ProxyVotes.against_management/management_alignment_rate` |
| `tender_offers/` (3) | Schedule 14D-9 | `Schedule14D9`, `classify_recommendation` |
| `diagnose_ssl/` (5) | Diagnóstico de SSL/proxy (detecta Windows/macOS) | `diagnose_ssl()`, `python -m edgar.diagnose_ssl` |
| `vendored/uu.py` (+`__init__`) | Copia de `uu`, que se eliminó en Python 3.13 | `encode`, `decode` |
| `docs/Filing.md`, `docs/Filings.md` | Documentación de usuario de `Filing`/`Filings` | — |
| `py.typed` | Marcador PEP 561 | — |

## Reutilizable para el proyecto
Todo se reutiliza **como dependencia pip** (`edgartools`, MIT) salvo que se indique otra cosa.

| Necesidad | Ruta exacta y símbolo | Cómo reutilizarlo | Notas (sección de `estructura-informe.md`) |
|---|---|---|---|
| Capa 1: identidad y datos de portada | `entity/core.py` `Company` (`name`, `tickers`, `get_exchanges()`, `sic`, `industry`, `fiscal_year_end`, `shares_outstanding`, `public_float`, `filer_category`) | pip | **§1 Portada**: sector, cierre fiscal, nº de acciones. El precio y el market cap no están |
| Capa 1: estados de 5 años | `Company.income_statement/balance_sheet/cash_flow_statement(periods=5, period='annual', as_dataframe=True)`; `entity/enhanced_statement.py` `MultiPeriodStatement.to_dataframe` | pip | **§1 datos básicos, §6, A1 (histórico)**. Viene de Company Facts: rápido y estandarizado |
| Capa 1: estados del último 10-K/10-Q, con dimensiones | `financials.py` `Financials.extract`, `.income_statement(include_dimensions=True)`, `get_free_cash_flow`, `get_capital_expenditures`, `get_shares_outstanding_diluted`, `get_financial_metrics`; `MultiFinancials.extract(filings)` | pip | **§4 segmentos, §6, A2**. `period_offset` ordena los periodos por recencia (GH #885) |
| Capa 1: TTM | `Company.get_ttm(concept, as_of='2024-Q2')`, `period='ttm'` | pip | §1 y §6 |
| Capa 1: serie larga de 10 años | `entity/entity_facts.py` `EntityFacts.time_series(concept, periods)`, `get_annual_fact` | pip | **A4** |
| Capa 1: texto del 10-K | `company_reports/ten_k.py` `TenK.business`, `.risk_factors`, `.management_discussion`, `get('Item 7A')` | pip | **§4, §5, §8**; entrada de la capa 4 |
| Capa 1: notas y deuda | `company_reports/_base.py` `CompanyReport.notes['Debt']`; `TenK.to_context(focus='debt')` | pip | §6 DFN. Los vencimientos de deuda no están en este alcance (`xbrl/standardization`) |
| Capa 1: gobierno corporativo | `company_reports/auditor.py` `extract_auditor_info` / `CompanyReport.auditor`; `TenK.directors_officers_and_governance`; `Company.proxy_season()`; `TenK.subsidiaries` | pip | **§9** (auditor, ICFR, Item 10, filiales). El proxy completo está en `edgar/proxy`, fuera de este alcance |
| Capa 1: guía y KPIs del trimestre | `earnings.py` `EarningsRelease.from_filing`, `.guidance`, `.segment_data`, `get_key_metrics()`; `CurrentReport.earnings` | pip | §1 tesis, §2 B, §6 |
| Trazabilidad cifra → fuente | `entity/models.py` `FinancialFact` (`concept`, `accession`, `filing_date`, `form_type`); `EntityFacts.to_dataframe(include_metadata=True)`; `sgml/concept_extractor.py` `extract_concepts_from_report` | pip | Principio 3 del plan: cada cifra con su concepto, filing y fecha |
| *Snapshot* y versiones | `entity/query.py` `FactQuery.as_of(date)`; `sgml/sgml_common.py` `FilingSGML`; `_filings.py` `Filing.from_sgml(path)`; `entity_facts.get_company_facts` (JSON) | pip; guardar el .txt SGML y el JSON de facts en la carpeta de *snapshots* | Evitar `Filing.save/load`, que usa `pickle` (inseguro y frágil entre versiones). C1-C4 |
| Versiones: nombre del periodo y aviso de filing nuevo | `enhanced_statement.py` `detect_fiscal_year_end`, `calculate_fiscal_year_for_label`; `FinancialFact.fiscal_year/fiscal_period`; `Company.latest_tenk/latest_tenq` (comparar `accession_no`) | pip | C1 y C2 (`AAPL · FY2026 Q2`) |
| Sectores con contabilidad distinta | `entity/categorization.py` `classify_business_category`, `BusinessCategory`; `Company.is_financial_institution()`, `reit_subtype`; `industry_extensions/*.json` | pip | Riesgo D (bancos, seguros, REIT); E4 |
| Comparables por SIC | `Company.sic` + `mappings_loader.get_industry(sic)`. La lista de empresas está en `edgar.reference.company_subsets.get_companies_by_industry` (otra parte) | pip | A5 y E5: solo sirve para elegir candidatos. **No calcula métricas de peers** |
| Industria y mercado | `search/efts.py` `search_filings(query, forms=['10-K'], …)` | pip | §5: búsqueda de texto completo en todos los filings |
| Capa 4: contexto para el LLM | `context.py` `compose_context(objects, max_tokens)`; `to_context(detail)` en `Company`, `TenK`, `Filing`, `EFTSSearch`… | pip | Presupuesto de tokens con recorte automático |
| Configuración `.env` | `settings.py` `set_identity`; `paths.py` `EDGAR_LOCAL_DATA_DIR`; `httpclient.py` `configure_http`, `EDGAR_RATE_LIMIT_PER_SEC`; `config.py` `EDGAR_*` | pip | Poner `EDGAR_IDENTITY` en `.env` **antes** de la primera llamada (si no, el *prompt* interactivo bloquea Streamlit). Caché **fuera de OneDrive** (C6) |
| Errores y estados de la UI | `exceptions.py` `EdgarError`, `TransportError`, `TooManyRequestsError`, `CompanyNotFoundError`, `StatementNotFoundError`, `ParsingError` | pip | Mensajes de estado del flujo en Streamlit |
| Tablas HTML (capa 3) | `earnings.py` `FinancialTable.to_html(classes=…)`; `entity/statement.py` `FinancialStatement` | Solo idea | Patrón DataFrame→HTML con clases CSS para la plantilla Jinja2 |
| Formato numérico | `display/formatting.py` `moneyfmt(sep='.', dp=',')` | Copiar con atribución MIT, o solo idea | A8: coma decimal sí. No admite negativos entre paréntesis: hay que adaptarlo |
| Docs y onboarding | `richtools.py` `Docs` + `docs/<Clase>.md` junto al código; `entity/CLAUDE.md` | Solo idea | Ver la sección siguiente |
| CI/tests | — | — | No hay en este alcance (`tests/` es otra parte) |

## Patrones de organización y onboarding
- **Docstrings «por qué»**: cada módulo explica la decisión, el bug que corrige (GH #) y su ticket (`bead edgartools-07lk.*`), por ejemplo `exceptions.py`, `effect.py` y `httpclient._host_key`. Una persona nueva entiende el diseño sin preguntar. **Trasladable** como convención en CONTRIBUTING.
- **Fachada única** `edgar/__init__.py` con `__all__` explícito y carga perezosa (`_LAZY_EXPORTS`). Las capas del proyecto pueden exponer así su API pública.
- **Obsolescencia ordenada**: `_compat.deprecated_alias`, *shims* PEP 562 que conservan la identidad del objeto y fecha de retirada («removed in 6.0»). Sirve para refactorizar sin romper nada.
- **Jerarquía de errores** con cuatro ramas que heredan de *builtins* (`ValueError`, `LookupError`), con `context`, `suggestions` y `docs_url`. Es un modelo directo para `informes_warrants.errores`.
- **Configuración solo por entorno** (`EDGAR_*`, documentada en el docstring de `config.py` y `paths.py`), centralizada en `settings.py`, `paths.py` y `config.py`. Encaja con `.env` y `pydantic-settings`.
- **Documentación por clase junto al código** (`entity/docs/Company.md`, `docs/Filing.md`) y accesible con `obj.docs` (`richtools.Docs`). La documentación de diseño interna va separada en `.docs/` (diseño o interna).
- **Guía para agentes por paquete**: `entity/CLAUDE.md` incluye arquitectura, tareas típicas, archivos que revisar, bugs conocidos con su solución, *snippets* de reproducción, convenciones (tipos, errores con contexto), «When Making Changes» y «Emergency Fixes». **Trasladable** como `CLAUDE.md` por capa (`ingesta/CLAUDE.md`…).
- **`to_context(detail='minimal'|'standard'|'full')`** uniforme en todos los objetos: un protocolo (`HasContext`) en lugar de herencia. Es buen patrón para pasar datos de las capas 1-2 a la capa 4.
- **Esquemas declarados de DataFrame** (`entity/dataframe_schema.py`, `datatools.apply_declared_schema`): columnas fijas aunque el resultado esté vacío. Útil para un *snapshot* estable.
- Lo flojo: la documentación interna mezcla planes antiguos («Phase 3» no implementada), hay módulos de 2.000-3.000 líneas (`entity_facts.py`, `enhanced_statement.py`, `_filings.py`) y `files/` está obsoleto pero sigue en el árbol.

## Lo que NO contiene
Verificado con `grep -i` sobre los 194 archivos del alcance.

| Necesidad | Búsqueda | Resultado |
|---|---|---|
| Precio, market cap, volumen, máximos/mínimos 12m, comportamiento relativo | `yfinance`, `share price`, `market_cap` | 0. Solo hay `public_float` (DEI) y `shares_outstanding` |
| EV, EV/EBITDA, PER, DCF, WACC | `enterprise value`, `ev/ebitda`, `wacc`, `discounted cash` | 0 |
| Ratios, comparables, anomalías | `EntityFacts.calculate_ratios/peer_comparison/detect_anomalies` | Existen, pero son **marcadores vacíos** |
| Proyecciones (años «e») | `forecast`, `projection` | 0 (las dos coincidencias son otra cosa) |
| Dividendos y *pay-out* calculados | `dividend` | Solo clasificación de conceptos, sin cálculo |
| Gráficos | `plotly`, `matplotlib`, `kaleido` | 0 |
| Plantilla Jinja2 y PDF | `jinja2`, `weasyprint` | 0 (jinja2 es dependencia de edgartools, pero no se usa en este alcance) |
| UI Streamlit | `streamlit` | 0 |
| Persistencia y versiones | `sqlalchemy`, `sqlite` | 0 (solo la ruta de la base de datos de tests en `paths.py`) |
| Cliente LLM | `import anthropic`, `openai`, `litellm` | 0 (el MCP y las skills están en `edgar/ai`, otra parte) |
| Vencimientos de deuda | `MaturitiesRepayments` | 0 (están en `xbrl/standardization`, otra parte) |
| Negativos entre paréntesis | `moneyfmt` | No los admite |
| CI y tests | — | Fuera de este alcance |
| Tamaño y CAGR del mercado sectorial | — | No existe (no sale de la SEC) |

## Riesgos
- **Licencia:** MIT, compatible con un SaaS si se conserva el aviso. `vendored/uu.py` tiene un aviso propio que también hay que conservar si se copia (no hace falta: se usa vía pip).
- **Dependencias:** pesadas (`pyarrow>=23.0.1`, `lxml>=6.1`, `pandas>=2`, `rich`, `httpx<0.29`, `httpxthrottlecache`, `stamina`, `truststore`, `rank_bm25`, `rapidfuzz`, `nest-asyncio`). El rango `httpx<0.29` puede chocar con los SDK de LLM: fijar versiones y probarlo.
- **Python 3.13 en Windows:** está declarado y `uu` va copiado para 3.13. Las rutas usan `pathlib` y solo `diagnose_ssl` depende de la plataforma. Comprobar que existe *wheel* de `pyarrow>=23` para cp313-win.
- **Bloqueo por identidad:** `get_identity()` llama a `ask_for_identity()` (`input` con `interrupt_main`) si falta `EDGAR_IDENTITY`. En Streamlit o un servidor hay que fijarla siempre en `.env` o con `set_identity` al arrancar.
- **Caché y datos:** se guardan por defecto en `~/.edgar` (`_tcache`, `companyfacts`). Hay que redirigirlos con `EDGAR_LOCAL_DATA_DIR` fuera de OneDrive. Las *submissions* y los *facts* caducan a los 30 s, así que no sirven como *snapshot*: el *snapshot* debe guardarlo el proyecto.
- **`pickle`:** `Filing.save/load` usa pickle. No hay que usarlo para versiones inmutables (riesgo de seguridad y de incompatibilidad entre versiones de edgartools).
- **API inestable:** v5 con muchos avisos «removed in 6.0» (`chunked_document`, `edgar.files.*`, `__getitem__` que pasará a lanzar `SectionNotFoundError`, `XBRLFilingWithNoXbrlData`). Fijar `edgartools>=5.61,<6`, usar `report.get('Item 7')` en lugar de `report['Item 7']` y no importar `edgar.files`.
- **Calidad de datos:** los estados de Company Facts dependen de mapeos aprendidos (`confidence`, cobertura canónica) y pueden omitir partidas o duplicarlas (`.docs/duplicate-fact-handling.md`, bug #408). Hay que validar contra el 10-K (fase 2, AAPL). Bancos, seguros, REIT y 20-F tienen árboles propios y cobertura parcial.
- **Límite de la SEC:** 9 peticiones/s por defecto (`EDGAR_RATE_LIMIT_PER_SEC`). Con muchos usuarios del SaaS hará falta una caché compartida o almacenamiento local (`use_local_storage`).
