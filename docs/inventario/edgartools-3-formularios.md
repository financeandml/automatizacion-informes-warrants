# edgartools-3-formularios

- **Repo / alcance / licencia:** `edgartools-main` (paquete `edgar/`, edgartools 5.x, `requires-python >=3.10`, clasificadores hasta 3.14). Alcance: `edgar/documents`, `offerings`, `funds`, `bdc`, `proxy`, `ownership`, `beneficial_ownership`, `thirteenf` y `reference`. Licencia **MIT** (© 2022-present Dwight Gunning, `LICENSE.txt`).
- **Cobertura:** 213 archivos (179 `.py`, 24 `.md`, 2 `.html`, 5 `.csv`, 1 `.json`, 1 `.parquet`, 1 `.pq`; unas 89.400 líneas).
  - **Leídos completos (26):** los 16 *shims* de `offerings/` raíz; `documents/__init__.py` y `agents.py`; `offerings/__init__.py`, `exempt/__init__.py`, `crowdfunding/__init__.py` y `crowdfunding/formc/__init__.py`; `ownership/__init__.py`; `reference/data/__init__.py` y `common.py`; `ownership/templates/base.html`.
  - **Solo firmas (178):**
    - 154 `.py`: docstring del módulo y todas las clases, métodos, funciones y constantes públicas, extraídas con un volcado AST estático que no ejecuta código.
    - 23 `.md`: encabezados e introducción.
    - `ownership_form.html`: sus etiquetas Jinja2.
    - Leí además en detalle las partes relevantes: `Document.get_sec_section`, `chunks` y `prepare_for_llm`; `TEN_K_FRIENDLY_ITEMS`; `ProxyStatement.sections`, `beneficial_ownership` y `to_context`; `ProspectusSectionsMixin.section`; `html_render.py` (Jinja2); `ProxyStatement.md` (disponibilidad de XBRL); `get_ticker_icon_url`.
  - **Por muestreo (9):** los 8 archivos de datos de `reference/data` (esquema, número de filas y 2-3 filas leídas con pyarrow/head) y `documents/.docs/AppleTable.md`, un fixture con el HTML de una tabla de Apple.
  - **Suma:** 26 + 178 + 9 = 213.

## Qué contiene

| Ruta (`edgar/…`) | Qué hace | API/elementos clave (nombres exactos) |
|---|---|---|
| **documents/** `__init__.py` | Fachada del parser HTML v2 de filings | `parse_html(html, config)`, `HTMLParser`, `Document`, `ParserConfig`, `DocumentSearch`, `MarkdownRenderer`, `TextRenderer`, `CrossReferenceIndex` |
| documents/agents.py | Detecta el agente de presentación (Workiva, DFIN, Toppan…) en los primeros 3.000 caracteres | `detect_filing_agent`, `WORKIVA`, `DONNELLEY`… |
| documents/config.py | Configuración y perfiles del parser | `ParserConfig` (`form`, `chunk_size`, `fast_table_rendering`, `for_performance/for_accuracy/for_ai`), `DetectionThresholds` |
| documents/document.py | Modelo de documento parseado | `Document.sections/tables/xbrl_facts/text()/get_sec_section("Item 1A")/get_available_sec_sections/get_sec_section_info/to_markdown/to_dataframe/chunks/search/prepare_for_llm`, `Sections.get_item(item, part)`, `Section.text/markdown/tables/search`, `DocumentMetadata`, `DocumentChunk`, `LLMDocument` |
| documents/form_schema.py | Esquemas declarativos de secciones por formulario | `get_form_schema`, `FormSchema`, `TEN_K_FRIENDLY_ITEMS` (`business`→1, `risk_factors`→1A, `mda`→7, `market_risk`→7A, `security_ownership`→12…), `TEN_K_SCHEMA`, `TEN_Q_SCHEMA`, `DEF14A_SCHEMA`, `S1_SCHEMA` |
| documents/cross_reference_index.py | Índices de referencias cruzadas de 10-K (formato GE) | `CrossReferenceIndex.get_item/extract_item_content`, `PageRange`, `IndexEntry`, `parse_cross_reference_index` |
| documents/section_size_bands.py | Control del tamaño de cada Item: avisa si una sección es anómala o está incorporada por referencia | `band_for`, `evaluate_size`, `is_undersize`, `is_cross_reference`, `SIZE_BANDS` |
| documents/extractors/hybrid_section_detector.py | Detección de secciones con varias estrategias, *fallback* y confianza | `HybridSectionDetector.detect_sections` |
| documents/extractors/toc_section_extractor.py | Texto de secciones a partir de las anclas del índice (TOC) | `SECSectionExtractor.get_section_text/get_available_sections/get_section_info`, `SectionBoundary` |
| documents/extractors/{toc,heading,index}_section_detector.py, pattern_section_extractor.py | Estrategias de detección: TOC, títulos, índice cruzado y regex Item/Part | `TOCSectionDetector`, `HeadingSectionDetector`, `IndexSectionDetector`, `SectionExtractor` |
| documents/extractors/chunk_extractor.py | Troceo estructural anclado a títulos y por presupuesto de tokens | `StructuralChunker(min_chars,max_chars)`, `ChunkExtractor(chunk_size,overlap)`, `Chunk(text,kind,heading,section)`, `chunk_html(html, form)` |
| documents/extractors/text_extractor.py | Texto limpio configurable | `TextExtractor.extract/render_table` |
| documents/search.py | Búsqueda por texto, regex, semántica o ranking | `DocumentSearch.search/ranked_search(query, algorithm, top_k, in_section)/find_tables/find_headings`, `SearchMode`, `SearchResult` |
| documents/ranking/{ranking,semantic,preprocessing,cache}.py | BM25 (`rank_bm25`) más *boost* estructural (sin embeddings) y caché del índice | `BM25Engine`, `HybridEngine`, `SemanticEngine`, `RankedResult.snippet`, `compute_semantic_scores`, `tokenize`, `normalize_financial_term`, `SearchIndexCache.compute_document_hash` |
| documents/table_nodes.py | Tablas del documento | `TableNode.to_dataframe/to_csv/find_row_by_first_cell/find_totals/is_financial_table/summarize_for_llm`, `Cell.numeric_value`, `Row.is_total_row` |
| documents/utils/{table_matrix,currency_merger}.py, table_utils.py | Normaliza tablas con colspan/rowspan y columnas «$» separadas | `TableMatrix`, `ColumnAnalyzer`, `CurrencyColumnMerger`, `process_table_matrix` |
| documents/renderers/{markdown,text,fast_table}.py | Convierte el documento a Markdown o texto y las tablas a texto | `MarkdownRenderer(include_toc, table_format).render/render_node`, `TextRenderer`, `FastTableRenderer`, `TableStyle.pipe_table`, `render_table_fast` |
| documents/strategies/document_builder.py, header_detection.py, style_parser.py, table_processing.py | Pasa el HTML (lxml) a un árbol de nodos y detecta títulos y tablas | `DocumentBuilder.build`, `HeaderDetectionStrategy`, `StyleParser`, `TableProcessor` |
| documents/strategies/{xbrl_extraction,ixbrl_transforms}.py | Hechos iXBRL y transformaciones (fechas, números en palabras, escala) | `XBRLExtractor.extract_fact`, `apply_transform`, `apply_scale`, `TRANSFORMS` |
| documents/parser.py, processors/{pre,post}processor.py | Parser principal, con limpieza previa y posterior | `HTMLParser.parse/parse_file/parse_url/create_for_ai`, `HTMLPreprocessor`, `DocumentPostprocessor` |
| documents/nodes.py, types.py, cache_mixin.py, exceptions.py | Nodos, tipos y excepciones | `Node.find/xpath/walk`, `HeadingNode`, `SectionNode`, `NodeType`, `SemanticType`, `TableType`, `XBRLFact`, `ParsingError`, `DocumentTooLargeError` |
| documents/utils/{toc_analyzer (3.006 L), toc_filter, anchor_cache, anchor_targets, section_slicer, html_utils, cache, tree_traversal}.py | Análisis del TOC, filtrado de navegación, corte por anclas, utilidades lxml y cachés | `TOCAnalyzer`, `analyze_toc_for_sections`, `filter_toc_links`, `extract_section_html`, `html_to_text`, `LRUCache`, `TimeBasedCache`, `cached` |
| documents/migration.py | Compatibilidad con el parser antiguo | `LegacyHTMLDocument`, `LegacySECHTMLParser`, `MigrationGuide` |
| documents/ (6 `__init__` de subpaquetes) | Re-exportaciones | — |
| documents/README.md | Guía del parser v2: quick start, configuración, búsqueda, tablas, render, migración y tests | — |
| documents/docs/*.md (7), html-parsing-prd.md, implementation-plan.md, parsing-analysis.md | Notas internas de la reescritura (estado a 2025-10, PRD, plan por fases). Desfasadas: hablan de `edgar.html` | — |
| **offerings/** `__init__.py` + 16 *shims* raíz (`_424b_*`, `_fee_table`, `_s1_*`, `_s3_cover`, `campaign`, `drs`, `formc`, `formd`, `registration_s1/s3/s4`) | Fachada; los *shims* re-exportan módulos movidos (`globals().update`) | `Prospectus424B`, `OfferingType`, `RegistrationS1/S3/S4`, `DraftRegistrationStatement`, `FormC`, `FormD`, `Campaign` = `Offering` |
| offerings/prospectus/document.py, deal.py, lifecycle.py | Folletos 424B*: oferta, precio, dilución, colocadores y vida útil del *shelf* | `Prospectus424B.from_filing/.offering_type/.pricing/.offering_terms/.dilution/.capitalization/.underwriting/.selling_stockholders/.deal/.lifecycle`, `Deal.gross_proceeds/net_proceeds/dilution_pct/is_atm/to_dict`, `ShelfLifecycle.takedowns/shelf_capacity/status` |
| offerings/prospectus/models.py | Modelos Pydantic | `OfferingTerms` (`warrants_offered`, `pre_funded_warrants_offered`), `DilutionData`, `CapitalizationData`, `UnderwritingInfo`, `RegistrationFeeTable`, `PROSPECTUS_FORMS` |
| offerings/prospectus/_424b_{classifier,cover,xbrl}.py, `_424b_tables/` (5), `_fee_table/` (3), parsing.py | Clasifica el tipo de oferta, extrae la portada y las tablas, y lee la tabla de tasas (Ex-107) | `classify_offering_type`, `extract_cover_page_fields`, `classify_table`, `extract_dilution_data`, `extract_capitalization_data`, `extract_registration_fee_table` |
| offerings/prospectus/registration_s{1,3,4}.py, `_s1_classifier`, `_s1_cover`, `_s3_cover`, `_s4_cover`, drs.py, _sections.py, _render.py, `__init__` | S-1, S-3, S-4/F-4 y DRS; secciones; render | `RegistrationS1.from_filing`, `S1CoverPage.is_large_accelerated_filer/is_smaller_reporting_company`, `S3OfferingType`, `ProspectusSectionsMixin.section(name)`, `to_context` |
| offerings/crowdfunding/ (7: `__init__`, campaign, _campaign_render, `formc/{__init__,core,models,helpers,_render}`) | Regulation CF (Form C) y ciclo de vida de la campaña | `FormC.from_filing`, `Offering.timeline/status`, `AnnualReportDisclosure`, `group_offerings_by_file_number` |
| offerings/exempt/formd.py, `__init__`, effect.py | Form D (Reg D) y aviso EFFECT | `FormD.from_xml/to_context`, `Effect.effective_date/get_source_filing` |
| offerings/docs/FormC.md | Guía de Form C | — |
| **funds/** core.py, `__init__`, data.py, reference.py | Jerarquía compañía → serie → clase de fondos | `Fund`, `find_fund`, `FundCompany`, `FundSeries`, `FundClass`, `resolve_fund_identifier`, `FundReferenceData.get_class_by_ticker` |
| funds/reports.py, models/derivatives.py, models/`__init__` | Cartera mensual N-PORT y derivados | `FundReport.investment_data/derivatives_data/to_context`, `get_fund_portfolio_from_filing`, `SwapDerivative`, `OptionDerivative` |
| funds/ncen.py, ncsr.py, nmfp3.py, prospectus497k.py, _497k_tables.py, twentyfourf.py | N-CEN, N-CSR, N-MFP, 497K y 24F-2NT | `FundCensus`, `FundShareholderReport`, `MoneyMarketFund`, `Prospectus497K.fees/performance`, `FundFeeNotice` |
| funds/series_resolution.py, ticker_resolution.py, thirteenf.py, examples.py | Ticker → serie, CUSIP/ISIN → ticker, puente a 13F y ejemplos | `TickerSeriesResolver`, `TickerResolutionService.resolve_ticker`, `get_thirteenf_portfolio` |
| funds/README.md, fund_domain_model.md | Guía y modelo de dominio de fondos | — |
| **bdc/** (`__init__`, reference, search, datasets, investments [3.156 L], nonaccrual, industry, README) | Business Development Companies: lista oficial, *datasets* DERA, cartera y préstamos dudosos (*non-accrual*) | `get_bdc_list`, `find_bdc`, `fetch_bdc_dataset`, `PortfolioInvestments.from_xbrl/by_industry/non_accrual_rate`, `extract_nonaccrual`, `normalize_sector` |
| **proxy/** core.py | DEF 14A: retribución (XBRL ECD) y tablas HTML | `ProxyStatement.from_filing/has_xbrl/peo_name/peo_total_comp/executive_compensation/pay_vs_performance/summary_compensation_table/director_compensation_table/beneficial_ownership/audit_fees/ceo_pay_ratio/voting_proposals/named_executives/insider_trading_policy_adopted/sections/section(key)/to_context` |
| proxy/html_extractor.py | Extrae datos del HTML del proxy (regex y lxml) | `extract_summary_compensation`, `extract_beneficial_ownership`, `extract_director_compensation`, `extract_audit_fees`, `extract_ceo_pay_ratio`, `extract_voting_proposals`, `AuditFees`, `BeneficialOwner` |
| proxy/models.py, season.py, contest.py, contests.py, `__init__` | Modelos, temporada de juntas y *proxy contests* | `ExecutiveCompensation`, `PayVsPerformance`, `NamedExecutive`, `ProxySeason.for_company`, `ProxyContest`, `proxy_contests(year, quarter)`, `classify_proxy_tier` |
| proxy/docs/ProxyStatement.md, Models.md | Guía de la clase y de sus modelos (incluye cuándo hay XBRL) | — |
| **ownership/** forms.py, summary.py, summary_records.py | Forms 3/4/5 de *insiders* | `Form4`, `Ownership.to_dataframe/get_ownership_summary/market_trades/common_stock_purchases/common_stock_sales/to_context/to_html`, `TransactionSummary.net_change/net_value/primary_activity/has_10b5_1_plan`, `TransactionActivity` |
| ownership/tables.py, table_containers.py, models.py, owners.py, core.py | Tablas, entidades y utilidades | `NonDerivativeTable`, `DerivativeTable`, `TransactionCode.description`, `Owner.position`, `detect_10b5_1_plan`, `translate_transaction_types` |
| ownership/form144.py | Form 144 (aviso de venta) | `Form144.to_analyst_summary/anomaly_flags/is_10b5_1_plan/cooling_off_compliant` |
| ownership/html_render.py + templates/base.html + ownership_form.html | Render HTML con **Jinja2** en el formato de la SEC | `ownership_to_html`, `Environment(loader=FileSystemLoader(template_dir))`, `{% extends "base.html" %}`, `{% block content %}` |
| ownership/text_render.py, ownershipforms.py (*shim*), `__init__` | Contexto para LLM; re-exportaciones | `ownership_to_context(ownership, detail)` |
| ownership/docs/{Form3,Form4,Form5,OwnershipSummary,TransactionSummary}.md | Guías por clase | — |
| **beneficial_ownership/** schedule13.py, models.py, amendments.py, rendering.py, `__init__` | Schedule 13D/13G (más del 5 %) | `Schedule13D/Schedule13G.from_filing/total_shares/total_percent/is_passive_investor/to_context`, `ReportingPerson.percent_of_class`, `Schedule13DItems.item4_purpose_of_transaction`, `compare_to_previous`, `OwnershipComparison.is_accumulating` |
| **thirteenf/** models.py, rendering.py, units.py, manager_lookup.py, demo_comparison.py, `__init__` | 13F-HR (vista desde la gestora) | `ThirteenF.holdings/infotable/total_value/compare_holdings/holding_history/previous_holding_report/to_context`, `HoldingsComparison`, `sparkline`, `resolve_value_unit`, `Ambiguous13FValueUnitWarning`, `lookup_portfolio_managers` |
| thirteenf/parsers/ (6) | Parseo de *infotables* XML y TXT (anteriores a 2013) | `parse_infotable_xml`, `parse_primary_document_xml`, `parse_infotable_txt` |
| **reference/** tickers.py | Mapas ticker ↔ CIK ↔ CUSIP y bolsa | `get_company_tickers`, `find_cik`, `find_ticker`, `get_company_ticker_name_exchange`, `get_companies_by_exchange`, `get_ticker_from_cusip`, `cusip_ticker_mapping`, `get_ticker_icon_url`, `get_icon_from_ticker`, `popular_us_stocks`, `Exchange` |
| reference/company_subsets.py | Selección de universos de empresas por bolsa, SIC o estado | `CompanySubset().from_exchange().from_industry(sic_range=…).sample()`, `get_companies_by_industry(sic, sic_range)`, `get_stratified_sample`, `get_software_companies`, `MarketCapTier` (enum sin datos) |
| reference/company_dataset.py | Construye un dataset de empresas a partir de las *submissions* masivas (Parquet o DuckDB) | `build_company_dataset_parquet`, `build_company_dataset_duckdb`, `get_company_dataset`, `COMPANY_SCHEMA` |
| reference/_codes.py, forms.py, `__init__`, data/common.py, data/`__init__` | Códigos de estado y país, descripción de formularios y lectura de datos empaquetados | `get_place_name`, `is_us_company`, `is_foreign_company`, `describe_form`, `read_parquet_from_package`, `read_csv_from_package` |
| reference/data/README_PORTFOLIO_MANAGERS.md | Guía para mantener a mano el JSON de gestores | — |
| reference/data/ (8 datos, muestreados) | `company_tickers.parquet` (10.365 filas: cik, ticker, exchange, name); `ct.pq` (68.830: Cusip, Ticker); `popular_us_stocks.csv` (85: Ticker, Company, Cik); `secforms.csv` (311: Form, Description); `exhibits.csv` (35, con regex por exhibit); `iso3166.csv` (333); `place_codes.csv` (309); `portfolio_managers.json` (40 gestoras y 75 gestores, v2025.01.09) | — |
| documents/.docs/AppleTable.md | Fixture con el HTML de una tabla financiera de Apple | — |

## Reutilizable para el proyecto

Todo se consume como **dependencia pip `edgartools`**, salvo cuando se indica otra cosa.

| Necesidad | Ruta exacta y símbolo | Cómo reutilizarlo | Notas |
|---|---|---|---|
| Capa 1 · texto del 10-K por Item (§4 Negocio = Item 1, §8 Riesgos = Item 1A, §6 MD&A = Item 7) | `documents/document.py` → `Document.get_sec_section("Item 1A")`, `Sections.get_item("1A")`; `documents/form_schema.py` → `TEN_K_FRIENDLY_ITEMS` | pip | `TenK.risk_factors` (fuera de este alcance) se apoya en este motor. Antes de mandar el texto al LLM, usar `get_sec_section_info` y `section_size_bands.evaluate_size`/`is_cross_reference` para detectar secciones vacías o incorporadas por referencia |
| Capa 4 · troceo para el LLM o RAG | `documents/extractors/chunk_extractor.py` → `ChunkExtractor`, `StructuralChunker`, `chunk_html(html, form="10-K")` | pip | Trozos anclados a títulos con su `section`. Sustituye a `Document.prepare_for_llm`, que está **roto**: importa `edgar.documents.ai.llm_optimizer`, que no existe |
| Capa 4 · verificar la cita literal del 10-K de cada viñeta (principio 3, trazabilidad) | `documents/search.py` → `DocumentSearch.ranked_search(query, top_k, in_section="Item 1A")`, `SearchResult.snippet` | pip | BM25 local (`rank_bm25`) sin embeddings: comprueba que la cita existe en la sección |
| Capa 4 / UI editor · precargar el bloque editable en Markdown (B2) | `documents/renderers/markdown.py` → `MarkdownRenderer.render_node`; `Section.markdown()` | pip | Markdown nativo en Streamlit |
| Capa 4 · contexto compacto para el LLM | Método `to_context(detail='minimal'\|'standard'\|'full')` (27 clases: `ProxyStatement`, `Schedule13G`, `Form4` vía `ownership_to_context`, `ThirteenF`, `Deal`…) | pip; el patrón, como idea | Presupuestos de unos 100, 300 y 500 tokens. Patrón a copiar en nuestros objetos de la capa 2 |
| §1 Estructura accionarial | `proxy/core.py` → `ProxyStatement.beneficial_ownership` (DataFrame `holder_name`, `holder_type` [5pct_holder/director_officer/group], `shares`, `percent_of_class`); `beneficial_ownership/schedule13.py` → `Schedule13G/13D.total_percent`, `ReportingPerson` | pip | La tabla de la Item 403 se extrae del HTML: puede venir vacía. Los 13D/G aportan las altas recientes por encima del 5 % |
| §1 / §9 Actividad de *insiders* | `ownership/forms.py` → `Form4.to_dataframe()`, `get_ownership_summary()`; `ownership/summary.py` → `TransactionSummary.net_change/net_value/primary_activity/has_10b5_1_plan` | pip | Por filing: el agregado por emisor hay que construirlo iterando los Form 4 |
| §9 Gobierno: alta dirección y retribución | `ProxyStatement.executive_compensation` y `pay_vs_performance` (5 años, XBRL ECD), `summary_compensation_table`, `named_executives`, `ceo_pay_ratio`, `director_compensation_table` | pip | El XBRL solo existe en *accelerated filers*: las SRC y EGC quedan exentas, así que hay que comprobar `has_xbrl` |
| §9 Comisión de auditoría y KPIs de gobierno | `ProxyStatement.audit_fees` (`AuditFees`: `auditor_name`, honorarios de auditoría, relacionados, fiscales y otros, actuales y anteriores), `insider_trading_policy_adopted`, `voting_proposals` | pip | Independencia y composición del consejo: no hay datos estructurados. Hay que pasarle al LLM `proxy.section('corporate_governance').text()` |
| §1 Comportamiento institucional (opcional) | `thirteenf/models.py` → `ThirteenF.compare_holdings()`, `holding_history()` | pip | Vista de la gestora, no del emisor: sirve para seguir a un fondo concreto, no para listar los holders de AAPL |
| §8 Riesgos de dilución, emisiones y warrants | `offerings/prospectus/document.py` → `Prospectus424B.deal` (`Deal.dilution_pct`, `is_atm`, `gross_proceeds`), `OfferingTerms.warrants_offered`; `RegistrationS3.is_auto_shelf`; `ShelfLifecycle.shelf_capacity` | pip | Viñeta «emisiones recientes y capacidad de *shelf*» (dato D, no IA) |
| §A5 Comparables y E5 (selección automática por SIC) | `reference/company_subsets.py` → `get_companies_by_industry(sic=…)`, `CompanySubset().from_exchange(["NYSE","Nasdaq"]).from_industry(sic_range=…)` | pip | `MarketCapTier` no tiene datos: hay que filtrar por market cap con nuestro precio. Se puede reforzar con edgar_analytics `analyze(peers=…)` |
| Capa 1 · resolver ticker → CIK y bolsa (portada §1) | `reference/tickers.py` → `find_cik`, `get_company_ticker_name_exchange`, `get_ticker_from_cusip` | pip | Datos empaquetados en `company_tickers.parquet` y `ct.pq`, que funcionan sin red |
| E4 · universo de empresas cotizadas de EEUU | `reference/tickers.py` → `get_companies_by_exchange`; `reference/_codes.py` → `is_us_company`, `is_foreign_company`; `bdc/reference.py` → `is_bdc_cik` | pip | Permite excluir BDC, fondos y extranjeros (20-F) del universo |
| Portada · icono de la empresa | `reference/tickers.py` → `get_ticker_icon_url` | Solo idea | Usa el repo externo `nvstly/icons`, de licencia no verificada: no usarlo en el PDF sin revisarla |
| Plantilla/PDF · Jinja2 con herencia | `ownership/html_render.py` → `Environment(FileSystemLoader)`; `ownership/templates/base.html` (`{% block content %}`) + `ownership_form.html` (`{% extends %}`) | Copiar el patrón con atribución MIT | Mismo esquema que nuestra plantilla única HTML → WeasyPrint. El CSS de la SEC no sirve |
| Capa 3 · tablas HTML del 10-K que no están en XBRL (p. ej., desglose de plantilla) | `documents/table_nodes.py` → `TableNode.to_dataframe()`, `find_row_by_first_cell`, `is_financial_table`; `Document.tables` | pip | Solo como respaldo: la fuente principal es XBRL |
| Versiones / *snapshot* | `documents/ranking/cache.py` → `SearchIndexCache.compute_document_hash` | Solo idea | Hash del contenido de entrada para identificar el *snapshot* |
| Docs/onboarding | `ownership/__init__.py` (docstring «qué paquete tiene tu formulario»), `proxy/docs/ProxyStatement.md` (Common Actions → Properties → Workflows → Errors → Best Practices) | Solo idea | Plantilla para documentar nuestros módulos |

Cobertura de `docs/estructura-informe.md`:

| Sección | Qué cubre este alcance |
|---|---|
| §1 Portada | Ticker, CIK y bolsa; estructura accionarial (proxy, 13D/G e *insiders*) |
| §4 Descripción del negocio | Item 1 |
| §5 Industria y mercado | Solo el texto de los Items 1 y 1A |
| §6 Análisis financiero | Texto del Item 7, para la IA |
| §8 Análisis de riesgos | Item 1A y dilución por emisiones |
| §9 Gobierno corporativo | Retribución, auditor y honorarios, pay-vs-performance, ratio de retribución del CEO, *insiders* y texto de gobierno |
| A5 Principales comparables | Universo por SIC |

No cubre §2, §3, §7, A1-A4 ni L.

## Patrones de organización y onboarding

- **Una carpeta por régimen o formulario, con fachada `__init__` y `__all__`.** La docstring de `ownership/__init__.py` explica a qué ley corresponde cada paquete (Sección 16, 13(d)/(g) y 13(f)). Es trasladable a nuestras carpetas `ingesta/`, `calculo/`, etc.
- **Objetos tipados homogéneos** en todos los formularios:
  - `Clase.from_filing(filing)` como constructor.
  - Propiedades simples y `@cached_property` para lo costoso.
  - `to_dataframe()` para análisis y `to_context(detail)` para el LLM.
  - `__rich__` para la consola.
  - Es un contrato fácil de aprender y conviene adoptarlo en nuestros módulos.
- **Modelos Pydantic y dataclasses** separados de la extracción (`models.py`, frente a `_cover.py` y `_tables/`) y del render (`_render.py`, `rendering.py`, `html_render.py`, `text_render.py`). Separación de responsabilidades trasladable.
- **Shims de compatibilidad** (`offerings/*.py`, `ownership/ownershipforms.py`) para mover módulos sin romper imports. Útil cuando reorganicemos.
- **Docstrings con referencias al tracker** (`edgartools-fhno`, `edgartools-9hwf`, `edgartools-bpab`): cada heurística enlaza a su decisión o incidencia. Buena trazabilidad para personas nuevas y agentes de IA.
- **Documentación por clase** en `docs/*.md` (Quick Start, Common Actions, Properties, Error Handling, Best Practices) y un README por subpaquete (`documents`, `funds`, `bdc`).
- **Configuración por perfiles** (`ParserConfig.for_ai()`, `for_performance()`). Trasladable a nuestra configuración.
- **Puntos débiles para onboarding:**
  - Documentos de desarrollo obsoletos en `documents/docs/` y `implementation-plan.md` (hablan de `edgar.html` y de un estado a 2025-10).
  - `README_PORTFOLIO_MANAGERS.md` apunta a una ruta absoluta del equipo del autor (`/Users/dwight/...`) y a una carpeta equivocada.
  - Módulos de más de 3.000 líneas (`utils/toc_analyzer.py`, `bdc/investments.py`).
- **No hay** CLAUDE.md, `.claude/`, skills ni CI dentro del alcance: están en la raíz del repo, que es otra parte del inventario. Los tests están en `tests/{documents,proxy,ownership,thirteenf,offerings,funds,bdc,reference,beneficial_ownership}`, también fuera de este alcance.

## Lo que NO contiene

Lo he verificado con `grep -ril` sobre las 9 carpetas.

- **UI:** no hay Streamlit.
- **PDF y gráficos:** no hay WeasyPrint, Plotly, kaleido ni matplotlib. El render es Rich (consola), HTML SEC o Markdown.
- **Persistencia y versiones:** no hay SQLAlchemy ni SQLite (`sqlite3`). DuckDB solo aparece para el dataset de empresas.
- **Cliente LLM:** no hay `anthropic`, `openai` ni `langchain`, ni embeddings, ni Chroma/FAISS. El ranking «semántico» es estructural.
- **Datos de mercado:** no hay precios (yfinance), ni market cap real (`MarketCapTier` no tiene datos), ni volumen ni short interest.
- **Valoración:** no hay DCF, WACC ni múltiplos.
- **Gobierno:** no hay datos estructurados de composición del consejo, independencia ni comisiones. Solo el texto de la sección `corporate_governance` y las tablas de retribución.
- **Holders institucionales por emisor:** el 13F es por gestora.
- **Agregado de Form 4 por emisor:** dentro del alcance solo se trata cada filing por separado.

## Riesgos

- **Licencia:** MIT. Para copiar el patrón Jinja2 hay que conservar el aviso. Los iconos de `nvstly/icons` (repositorio externo) tienen licencia no verificada. `portfolio_managers.json` es una base curada a mano y desactualizada (enero de 2025).
- **Dependencias:**
  - `lxml>=6.1`, `pyarrow>=23.0.1`, `rank_bm25`, `rich`, `jinja2` y `pydantic`, más `duckdb` como opcional.
  - `httpx` está limitado a `<0.29` porque está inactivo; el autor planea migrar a httpx2.
  - Hay wheels para Python 3.13 en Windows. El paquete declara compatibilidad de 3.10 a 3.14.
- **Fragilidad:**
  - La extracción de proxy, 424B y secciones es heurística (regex y TOC con confianza) y puede devolver `None` o un DataFrame vacío.
  - `proxy.sections` puede salir vacío en proxies sin TOC (`edgartools-bpab`).
  - Los valores del 13F son ambiguos (miles o dólares) antes de 2023 (`Ambiguous13FValueUnitWarning`).
  - `Document.prepare_for_llm` falla por un import inexistente.
  - **Mitigación:** tests de contrato con AAPL y fijar la versión, `edgartools>=5,<6`.
- **Rendimiento:** el parseo completo de un 10-K grande y el BM25 se calculan en memoria. Las cachés en disco (`get_search_cache_directory`, `get_anchor_cache_directory`) van a la carpeta de caché de edgartools. Hay que mantenerla **fuera de OneDrive**, igual que SQLite (C6).
- **Calidad:** código muy tipado y documentado, con IDs de decisión en las docstrings. Pero los módulos son enormes y la documentación interna está obsoleta.
