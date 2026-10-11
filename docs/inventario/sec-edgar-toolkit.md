# sec-edgar-toolkit

- **Repo / alcance / licencia:** `sec-edgar-toolkit-main`, de Stefano Amorelli. Es un monorepo con dos paquetes paralelos: uno en Python (`python/`, paquete `sec_edgar_toolkit`) y otro en TypeScript (`typescript/`), cuya API es espejo 1:1 de la de Python. La versión es la 0.2.0 en `pyproject.toml` y `package.json`, pero `CITATION.cff` dice 0.1.0 (2025-01-06). Esta ficha cubre todo el repo: raíz, `.github/`, `python/` y `typescript/`.
  - **Licencia AGPL-3.0** (`LICENSE`, © 2025 Stefano Amorelli; el autor ofrece licencia comercial por email). Para este SaaS es **solo referencia de ideas**: no se copia código ni se instala como dependencia, porque integrarlo obligaría a publicar el código del servicio (ver [repositorios-base.md](../repositorios-base.md)).
  - Python: `requires-python >=3.8`, clasificadores 3.8-3.12. La única dependencia obligatoria es `requests>=2.31`; los extras son `pandas`, `lxml`, `full` y `dev`.
- **Cobertura:** 238 archivos (80 `.py`, 74 `.ts`, 4 `.js`, 54 `.txt`, 2 `.xml`, 8 `.yml`, 4 `.md` y 12 de configuración: `LICENSE`, `Dockerfile`, `Makefile`, `pyproject.toml`, `package.json`, etc.).
  - **Leídos completos: 119.**
    - Raíz: 7 (todo menos `LICENSE`).
    - `.github/workflows`: 7.
    - Configuración y README de `python/`: 6.
    - `python/src`: los 59 `.py`.
    - `python/examples`: 7. `python/scripts`: 2.
    - `python/tests`: 10 `.py`.
    - Configuración y README de `typescript/`: 5.
    - `typescript/src`: 16 (los 9 `index.ts`, `types/config.ts`, `exceptions/base.ts`, `utils/cache.ts`, `utils/http-client.ts`, `utils/disk-cache.ts`, `client/edgar-client.ts` y `client/sync-wrapper.ts`).
  - **Solo firmas: 63.** Se leyeron las exportaciones, clases y métodos públicos, más los cuerpos relevantes:
    - `LICENSE`: cabecera y copyright.
    - `python/tests`: 2 (`test_sec_edgar_api.py` y `test_sec_edgar_api_integration.py`; firmas, más los bloques de errores y *rate limit*).
    - `typescript/src`: 44 (con `item-extractor.ts` leído en parte, `ErrorHandler` y `StatementTable`).
    - `typescript/src/__tests__`: 9 (nombres de `describe` e `it`).
    - `typescript/examples` y `typescript/scripts`: 7 (cabeceras).
  - **Por muestreo: 56.**
    - 2 XML sintéticos de Form 4/5: cabecera y banderas de relación.
    - 54 `.txt`, que son 27 en `python/tests/fixtures/forms/` y otros 27 idénticos en `typescript/` (verificado con `diff -rq`). De cada uno se muestreó la cabecera SGML (tipo, empresa, periodo, nº de `<DOCUMENT>`) o el cuerpo de error.
  - Suma: 119 + 63 + 56 = **238**.

## Qué contiene

### Raíz y `.github/` (15)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `README.md` | Presenta el monorepo, con una tabla de paridad Python/TS, *quick start* de las 3 capas de API, Docker y agradecimientos | Aviso «not affiliated with… the SEC». Enlaza un `CONTRIBUTING.md` **que no existe** |
| `LICENSE` | AGPL-3.0 (solo referencia) | `Copyright (C) 2025 Stefano Amorelli` |
| `SECURITY.md` | Política OWASP Tallinn: reporte privado, secretos, cadena de suministro, PR con revisión, commits firmados | Acuse en 7 días hábiles; corrección en 90 días o menos |
| `CITATION.cff` | Metadatos de cita | ORCID, `license: AGPL-3.0` |
| `Dockerfile` | *Multi-stage*: `typescript-base/dev`, `typescript`, `python-base/dev` y `python` (python:3.11-slim), más un `dev` combinado (ubuntu 22.04) | `pnpm install --frozen-lockfile` sin lockfile versionado |
| `docker-compose.yml` | 5 servicios (dev y prod por lenguaje, más el combinado) en la red `sec-edgar-net` | `python-dev` ejecuta `pytest --cov` |
| `.dockerignore`, `.gitignore` | Exclusiones estándar de Python y Node | Ignora los lockfiles (`package-lock.json`, `pnpm-lock.yaml`) |
| `.github/workflows/python-ci.yml` | CI de Python filtrado por `paths: python/**`, matriz 3.8-3.12 en `ubuntu-latest` | `ruff check src/`, `ruff format --check`, `mypy src/`, `pytest --cov` y Codecov (solo en 3.11) |
| `.github/workflows/python-lint-check.yml` | Lint y mypy en los PR (3.11). Duplica en parte el anterior | `ruff check src/ tests/` |
| `.github/workflows/python-release.yml` | Release al crear un tag `v*`: inyecta la versión con `sed`, construye, sube con `twine` y crea la GitHub Release | `PYPI_API_TOKEN`, `softprops/action-gh-release@v1` |
| `.github/workflows/conda-release.yml` | Espera a que el paquete esté en PyPI, genera `meta.yaml` al vuelo y publica en Anaconda | `ANACONDA_TOKEN` |
| `.github/workflows/typescript-ci.yml`, `javascript-ci.yml` | Dos CI casi idénticos para `typescript/**` (pnpm 8, Node 20) | `lint`, `type-check` (solo en javascript-ci), `test`, `build` |
| `.github/workflows/typescript-release.yml` | Publica en npm con *trusted publishing* OIDC | `id-token: write`, sin `NPM_TOKEN` |

### `python/`: configuración y documentación (6)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `pyproject.toml` | Paquete setuptools: `requires-python >=3.8`, dependencia única `requests`, configuración de ruff (target py38, 88 columnas, reglas E/W/F/I/B/C4/UP/ARG/SIM con 13 excepciones), mypy laxo y black | Extras `pandas`, `lxml`, `full`, `dev` (pytest, pytest-cov, responses, ruff, mypy, black, pre-commit) |
| `pytest.ini` | Activa `--cov` y el informe HTML por defecto, `--strict-markers` | Marcadores `integration` y `unit`. Duplica `[tool.pytest.ini_options]` del pyproject |
| `Makefile` | Atajos de desarrollo con `rm -rf`/`find` (POSIX) | `install`, `install-dev`, `test`, `test-unit`, `test-integration`, `lint`, `lint-fix`, `format` (black, mientras que la CI usa `ruff format`), `type-check`, `clean`, `all`, `dev` |
| `.env.example` | Plantilla de entorno | `SEC_EDGAR_TOOLKIT_USER_AGENT="MyCompany/1.0 (contact@example.com)"` |
| `.python-version` | Fija `3.8`, que ya no tiene soporte (EOL) | — |
| `README.md` | Guía de la capa baja `SecEdgarApi`: company, submissions, facts, concept, frames, errores y *rate limit* | *Badges* estáticos («97 % coverage», «41 tests»). No documenta la API de objetos |

### `python/src/sec_edgar_toolkit/` (59)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `__init__.py` | Fachada pública. El docstring explica las 3 capas: objetos → API fluida → JSON crudo | `__version__='0.2.0'`, `Company`, `Filing`, `Filings`, `CompanyFacts`, `Financials`, `XBRLInstance`, `FactQuery`, `TenK`, `TenQ`, `EightK`, `OwnershipForm`, `ThirteenF`, `set_identity`, `find_company`, `search`, `get_filings`, `get_current_filings`, `full_text_search`, `search_filings`, `create_client`, `EdgarClient`, `AsyncEdgarClient`, `SecEdgarApi`, excepciones, parsers, tipos |
| `compat.py` | Ruta de importación estable para la API de objetos | Reexporta `core` |
| `client/__init__.py`, `core/__init__.py`, `core/xbrl/__init__.py`, `endpoints/__init__.py`, `exceptions/__init__.py`, `parsers/__init__.py`, `types/__init__.py`, `utils/__init__.py` (8) | Reexportadores | `parse_filing_index_html`, `CurrentEventParser`, `FinancialFormParser`, `ItemExtractor`, `FormType`, `FilingFilter`, `HttpClient` |
| `client/sec_edgar_api.py` | Cliente de bajo nivel. Valida el User-Agent (o lo toma de `SEC_EDGAR_TOOLKIT_USER_AGENT`) y delega en 4 grupos de endpoints | `SecEdgarApi(user_agent, rate_limit_delay=0.1, max_retries=3, timeout=30, cache_dir, cache_ttl=21600)`: `get_company_tickers`, `get_company_by_ticker/cik`, `search_companies`, `get_company_submissions(cik, submission_type, from_date, to_date)`, `get_company_submissions_page`, `get_filing`, `get_company_facts`, `get_company_concept`, `get_frames`, `full_text_search`, `get_recent_filings` |
| `utils/http.py` | Sesión `requests` con `Retry` (429 y 5xx, *backoff* 1 s), espera mínima entre peticiones, mapeo de códigos HTTP a excepciones y caché en disco opcional | `HttpClient.get` (JSON), `get_raw` (bytes), `_rate_limit`, `_cache_key` |
| `utils/disk_cache.py` | Caché en disco indexada por el SHA-256 de la URL. **Las URL `/Archives/` son inmutables y no caducan; las respuestas de la API usan TTL** | `DiskCache(cache_dir, ttl).get/set/clear`, `<hash>.body` + `<hash>.meta.json` (`{url, timestamp}`) |
| `utils/filters.py` | Filtra la tabla columnar `filings.recent` | `FilingFilter.filter_filings(filings, form_type, from_date, to_date)` |
| `utils/xml_parser.py` | Envoltorio de lxml que recurre a ElementTree si lxml no está | `EnhancedXMLParser(recover, remove_blank_text, huge_tree)`, `HTMLParser`, `parse_xml`, `parse_html`, `xpath`, `to_dict` |
| `utils/optional_deps.py` | Importa pandas o lanza un error que dice cómo instalarlo | `require_pandas()` → «pip install 'sec-edgar-toolkit[pandas]'» |
| `endpoints/company.py` | Mapa ticker↔CIK desde `company_tickers_exchange.json`, con caché en memoria de 24 h | `CompanyEndpoints.get_company_tickers/get_company_by_ticker/get_company_by_cik/search_companies` (busca subcadenas del nombre) |
| `endpoints/filings.py` | Lee `submissions/CIK##########.json`, `Archives/…/index.json`, las páginas de histórico antiguo y el feed Atom `getcurrent` | `FilingsEndpoints.get_company_submissions`, `get_company_submissions_page`, `get_filing`, `get_recent_filings(form_type, limit, owner, start)`, `_parse_atom_feed` |
| `endpoints/fulltext.py` | Búsqueda de texto completo en efts.sec.gov (filings desde 2001) | `FullTextSearchEndpoints.search(query, forms, start_date, end_date, cik, offset)` → `{total, hits[accession_number, document, cik, company_name, form_type, filing_date, period_ending, file_type, score]}` |
| `endpoints/xbrl.py` | Endpoints companyfacts, companyconcept y **frames** (un concepto para todas las empresas en un periodo `CY2023Q4I`) | `XbrlEndpoints.get_company_facts`, `get_company_concept(cik, taxonomy, tag, unit)`, `get_frames(taxonomy, tag, unit, year, quarter, instantaneous)`. Error: sin trimestre ignora `instantaneous` |
| `exceptions/base.py`, `exceptions/http.py` | Jerarquía mínima de excepciones | `SecEdgarApiError` → `RateLimitError`, `AuthenticationError`, `NotFoundError` |
| `core/global_functions.py` | Cliente global (*singleton*) y funciones de módulo | `set_identity(user_agent, cache_dir, cache_ttl)`, `_get_api`, `find_company`, `search`, `get_filings(form, cik, ticker, since, before, limit)`, `get_current_filings(form, page_size, owner)`, `full_text_search`, `search_filings` |
| `core/company.py` | Empresa por ticker o CIK. El perfil se carga al primer acceso desde submissions (`__getattr__`) | `Company(identifier)`: `cik`, `name`, `ticker`, `exchange`, `tickers`, `sic`, `sic_description`, `fiscal_year_end`, `state_of_incorporation`, `get_filings(form, since, before, limit, deep, amendments)`, `get_facts`, `get_company_facts`, `get_financials`, `get_quarterly_financials`, `get_concept` |
| `core/collections.py` | Lista de filings, del más reciente al más antiguo | `Filings.latest(n)`, `filter(form)`, `filter_by_form` |
| `core/filing.py` | Un filing: URLs del archivo, documento principal, texto limpio, adjuntos tipados, `obj()` por formulario, items y XBRL | `Filing(cik, accession_number, form_type, filing_date, …)`: `url`, `attachments`, `exhibits`, `text(format='text'\|'html'\|'raw')`, `obj()`, `extract_items(item_numbers)`, `get_item`, `items`, `xbrl()`; `FilingItem` |
| `core/attachments.py` | Un documento de la carpeta del filing | `Attachment(name, url, size, type, description, sequence)`, `is_press_release` (EX-99*), `is_exhibit`, `to_dict` |
| `core/exhibits.py` | Parser regex de la página índice del filing: tipo de cada documento | `parse_filing_index_html(html)` → `{sequence, description, document, type, size}` |
| `core/facts.py` | Envoltorio de companyfacts | `CompanyFacts.data`, `get_fact(concept)` → DataFrame `fy, fp, value, unit, form, end, start, filed, accn`. Busca en us-gaap → dei → ifrs-full → srt |
| `core/financials.py` | Estados financieros desde companyfacts, filtrados por tipo de formulario, con listas fijas de conceptos GAAP e IFRS | `Financials(facts_data, form_type, accession_number)`, `.extract(filing)`, `income_statement()`, `balance_sheet()`, `cash_flow()`/`cash_flow_statement()`. Listas: `INCOME_STATEMENT_CONCEPTS` (15), `BALANCE_SHEET_CONCEPTS` (18), `CASH_FLOW_CONCEPTS` (9: capex, dividendos, recompras, D&A, SBC), `IFRS_*`, `ANNUAL_FORMS`, `QUARTERLY_FORMS`. **Solo devuelve 4 periodos, ignora `accession_number` y no filtra por duración** |
| `core/periodic_report.py` | Base común de 10-K y 10-Q. Solo expone como atributos las secciones encontradas | `PeriodicReport.SECTION_ITEMS`, `items`, `financials` |
| `core/form_10k.py` | 10-K | `TenK.business` (Item 1), `.risk_factors` (1A), `.mda` (7) |
| `core/form_10q.py` | 10-Q | `TenQ.mda` (Item 2), `.risk_factors` (II-1A) |
| `core/form_8k.py` | 8-K: items presentes, fecha del informe y notas de prensa | `EightK.items`, `date_of_report`, `press_releases`, `has_press_release`, `has_item(EightKItem.RESULTS_OF_OPERATIONS)` |
| `core/ownership.py` | Form 3/4/5 con acceso por atributos (subclase de `dict`) | `OwnershipForm.owner_name/owner_title/is_director/is_officer/is_ten_percent_owner/issuer_name/issuer_cik/transactions/holdings/derivative_holdings/owners/footnotes/to_dataframe()`; `OwnershipTransaction`, `OwnershipHolding`, `OwnershipOwner` |
| `core/thirteenf.py` | 13F de una gestora: localiza la *information table* y la portada | `ThirteenF.from_filing`, `holdings`, `holding_count`, `total_value`, `by_issuer(name)`, `top_holdings(n)`; `Holding13F` |
| `core/xbrl/instance.py` | XBRL de un filing: consultas sobre companyfacts y estados por rol (instance + linkbases o R-files) | `XBRLInstance.facts/us_gaap/dei/reports/as_reported/instance_document`, `query(concept \| "concept=X&unit=USD", taxonomy, unit, period)`, `get_all_statements()`, `get_statement(role, source='auto'\|'instance'\|'rendered')`, `find_statement`, `get_concept_value`, `list_concepts`, `to_dataframe`, `to_dict` |
| `core/xbrl/as_reported.py` | **Estados tal como se reportan**: combina el instance (`_htm.xml`), la presentación (`_pre.xml`) y las etiquetas (`_lab.xml`). Conserva orden, profundidad y etiqueta preferida, y crea filas dimensionales limitadas a los miembros del rol | `AsReportedStatements(archive_base, http_client, file_names)`: `is_available`, `list_roles`, `get_statement(role)` → `{concept, label, base_label, section, values{periodo: valor}, units, has_values, abstract, depth, order, dimensions}` |
| `core/xbrl/instance_document.py` | Parser puro (sin I/O) del instance: contextos, unidades y hechos deduplicados | `InstanceDocument.parse(raw)`, `facts_for`, `concepts`, `unit_of`, `context_of`; `Context.period_key/is_duration/dimensions`; `InstanceFact.numeric_value` |
| `core/xbrl/linkbases.py` | Parsers puros de los linkbases de presentación y etiquetas | `PresentationLinkbase.parse/ordered_concepts/find_role`, `PresentationNode`, `LabelLinkbase.parse/label_for(concept, preferred)`, `STANDARD_LABEL` |
| `core/xbrl/queries.py` | Primitivas de consulta sobre companyfacts | `FactsData.facts_history(concept)`, `FactQuery.by_concept/to_dataframe`, `build_fact_records`, `parse_filter_expression` |
| `core/xbrl/rendered_reports.py` | Lee `FilingSummary.xml` y los `R<n>.htm`, con caché | `RenderedReportReader.list_reports/find_report/read_statement` |
| `core/xbrl/report_html.py` | Parser regex puro de los R-files: periodos, escala («in Millions/Thousands/Billions»), negativos entre paréntesis y secciones por eje | `parse_report_html`, `parse_report_number`, `normalize_period_label` («Sep. 27, 2025» → `2025-09-27`), `_parse_multipliers` |
| `core/xbrl/statements.py` | Alias y conceptos mínimos de cada estado | `STATEMENT_ALIASES`, `STATEMENT_CONCEPTS`, `normalize_statement_type` |
| `edgar.py` | API fluida encadenable, construida sobre la de objetos | `EdgarClient`, `create_client`, `CompanyQueryBuilder.lookup/search/batch_lookup`, `CompanyFilingBuilder.form_types/since/until/recent/fetch`, `CompanyFactsBuilder.concept/taxonomy/in_units/period/fetch`, `Company.financial_summary`, `FilingAnalysis.extract_financials`, `FinancialData.key_ratios` (D/A, D/E), `AsyncEdgarClient` (no es asíncrono real: usa `run_in_executor`). `configure()` no hace nada |
| `parsers/items.py` | Enumeraciones y tablas de items por formulario | `FormType`, `TenKItem` (`BUSINESS`="1", `RISK_FACTORS`="1A", `CYBERSECURITY`="1C", `MANAGEMENT_DISCUSSION_AND_ANALYSIS`="7"…), `TenQItem` ("II-1A"…), `EightKItem`, `TwentyFItem`, `ItemDefinition`, `FORM_10K_ITEMS`, `FORM_10Q_ITEMS`, `FORM_8K_ITEMS`, `FORM_20F_ITEMS` |
| `parsers/item_extractor.py` | Extrae items por regex: quita las etiquetas, detecta el índice y, entre las coincidencias de cada encabezado, elige la que abarca más texto hasta el siguiente «Item N.» | `ItemExtractor.extract_items(content, form_type)`, `extract_specific_items`, `get_item_definitions` |
| `parsers/ownership_forms.py` | Parser XML de los Form 3/4/5 | `OwnershipFormParser.parse_document_info/parse_issuer_info/parse_reporting_owner_info/parse_reporting_owners/parse_non_derivative_transactions/parse_non_derivative_holdings/parse_derivative_transactions/parse_derivative_holdings/parse_footnotes/parse_all`; `Form4Parser`, `Form5Parser`, `OwnershipFormParseError` |
| `parsers/thirteenf.py` | Parser del 13F, independiente del *namespace* | `ThirteenFParser.parse_holdings()`, `parse_cover_page()` |
| `parsers/financial_forms.py` | Parser heurístico por regex («$» + número) sobre el texto del 10-K/10-Q | `FinancialFormParser.parse_all/parse_balance_sheet/parse_income_statement/parse_cash_flow_statement/get_business_segments/get_risk_factors/get_management_discussion/get_xbrl_facts/get_financial_metrics`. **Calidad baja**: la *quick ratio* la calcula como activo corriente × 0,8 / pasivo corriente, y la severidad del riesgo por palabras clave |
| `parsers/current_events.py` | Parser heurístico de los 8-K | `CurrentEventParser.parse_all/get_current_events/get_material_agreements/get_executive_changes/get_acquisitions/get_earnings_results`. `_extract_item_content` usa `[^]` (sintaxis de JS), inválida en el `re` de Python |
| `types/company.py`, `types/filing.py` | TypedDicts de las respuestas JSON de la SEC | `CompanyTicker`, `CompanySubmissions`, `FilingDocument`, `FilingDetail` |
| `types/financial_forms.py`, `types/current_events.py`, `types/institutional_holdings.py`, `types/parsing.py`, `types/analytics.py`, `types/proxy_statements.py` (6) | TypedDicts de los parsers heurísticos. `analytics` y `proxy_statements` son **solo tipos, sin implementación** | `ParsedFinancialForm`, `RiskFactor`, `MDSection`, `ParsedCurrentEvent`, `ParsedInstitutionalHolding`, `Timeline`, `OwnershipTrend`, `ComplianceMetrics`, `ParsedProxyStatement`, `BoardMember`, `CompensationTable` |

### `python/examples/` y `python/scripts/` (9)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `examples/object_api.py` | Recorrido por la API de objetos. Coincide con la API actual | `Company`, `get_filings().latest()`, `obj()`, `get_item(TenKItem.CYBERSECURITY)`, `get_fact`, `xbrl().get_all_statements()` |
| `examples/basic_usage.py` | Capa baja: tickers, submissions, 10-K de los últimos 2 años, facts, concepto `Assets` y frames de `Revenues` 2023 (top 5) | `SecEdgarApi()` leyendo el User-Agent del entorno |
| `examples/api_showcase.py` | API fluida y `AsyncEdgarClient` | `financial_summary`, `key_ratios`, `batch_lookup` |
| `examples/xml_parsing_example.py` | Parsea los XML de ejemplo de Form 4/5 e imprime cada sección | `Form4Parser`, `Form5Parser`; admite una ruta como argumento |
| `examples/current_events_tracker.py`, `item_extraction_demo.py`, `xbrl_financial_analysis.py` (3) | **Ejemplos rotos**: usan `await` sobre métodos síncronos y llaman a `get_facts_by_concept`, que solo existe en TS | — |
| `scripts/live_e2e.py` | *Smoke test* en vivo contra la SEC con `check(name, cond, detail)`. Sale con código 1 si algo falla | Sobre AAPL: CIK, perfil, orden de los filings, `TenK` (riesgos de más de 1000 caracteres), 8-K, Form 4, `get_fact`, `Financials`, estados de segmentos, `query`, `get_current_filings` |
| `scripts/live_features_e2e.py` | Igual, para as-reported, búsqueda de texto completo, exhibits, 13F (Berkshire), Form 4 con varios declarantes, 20-F IFRS (TSMC), enmiendas y caché | **Oráculo AAPL, 10-K FY2025 (cierre 2025-09-27): `NetIncomeLoss` = 112.010.000.000 USD y `EarningsPerShareBasic` = 7,49** |

### `python/tests/` (12 `.py` y 2 `.xml`; los 27 `.txt`, en «Fixtures»)
| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `__init__.py`, `conftest.py`, `fixtures/__init__.py`, `fixtures/company_fixtures.py`, `fixtures/filing_fixtures.py` (5) | Fixtures de pytest con JSON simulado de la SEC (tickers, submissions de Apple, facts, frames) | `api_client`, `mock_company_tickers`, `mock_company_submissions`, `mock_xbrl_facts`, `mock_frame_data`, `mock_filing_data` |
| `test_core_functionality.py` | Prueba la API de objetos con `unittest.mock` | `TestGlobalFunctions`, `TestCompany`, `TestFiling`, `TestXBRLInstance` |
| `test_sec_edgar_api.py` | Prueba la capa baja con HTTP simulado (`responses`): endpoints, *rate limit*, errores 401/404/429/500/timeout y filtros | `TestSecEdgarApi`, `TestTypeDefinitions` |
| `test_sec_edgar_api_integration.py` | Flujos completos con HTTP simulado | `TestSecEdgarApiIntegration` (flujo completo, varias empresas, frames, caché) |
| `test_instance_xbrl.py` | XBRL as-reported con XML en línea y un `LocalHttp.get_raw` falso, sin red. Cubre también 13F, exhibits, búsqueda de texto completo con *stub*, `DiskCache` y 20-F | `TestInstanceDocument`, `TestLinkbases`, `TestAsReported`, `TestThirteenF`, `TestExhibits`, `TestDiskCache`. Incluye una aserción que siempre se cumple (`… is None or True`) |
| `test_ownership_forms.py` | Form 4/5 sobre los XML de ejemplo | `TestOwnershipFormParser`, `TestForm4Parser`, `TestForm5Parser`, `TestIntegration` |
| `test_financial_forms.py` | Comprueba solo claves y tipos del parser heurístico sobre `apple_10k_2023.txt` | `TestFinancialFormParser` |
| `test_recent_filings.py` | Feed Atom de ejemplo en línea | `TestAtomFeedParser`, `TestGetRecentFilings` |
| `fixtures/form4_sample.xml`, `fixtures/form5_sample.xml` | XML **sintéticos** (Tim Cook/AAPL y Satya Nadella/MSFT), esquema X0306, banderas `true`/`false` | — |

En Python no hay tests de `ItemExtractor.extract_items` (solo de las definiciones del 20-F) ni de `CurrentEventParser`.

### Fixtures `.txt` (54)
Hay 27 en `python/tests/fixtures/forms/` y 27 copias idénticas en `typescript/tests/fixtures/forms/`, unos 19,7 MB por copia.

| Carpeta | Nº | Contenido real (cabecera SGML muestreada) |
|---|---|---|
| `10-K/` | 4 | `apple_10k_2023.txt` (9,6 MB): 10-K completo de Apple FY2023 (`0000320193-23-000106`, 96 documentos). `jpmorgan_10k_2024.txt` (90 KB): en realidad es un **SC 13G/A** sobre Federal Realty. `alphabet_…` y `pfizer_…`: error S3 `NoSuchKey` (~340 B) |
| `10-Q/` | 3 | `amazon_10q_2024.txt` (5,5 KB): en realidad es un **Form 4** (Andrew Ng/AMZN). Los otros 2, `NoSuchKey` |
| `13F/` | 5 | `bridgewater_13f_2024.txt` (17,6 KB): en realidad es un **SC 13G/A** (Coupang, presentado por Morgan Stanley). Los otros 4, `NoSuchKey` |
| `4/`, `5/`, `6/` | 3 + 1 + 2 | Todos `NoSuchKey` |
| `8-K/` | 4 | `apple_8k_2024.txt` (9,8 MB): en realidad es el **10-K FY2024 de Apple** (`0000320193-24-000123`, 102 documentos). `exxon_8k_2024.txt` (258 KB): un **8-K de 3M**. `nvidia_8k_2023.txt`: un **Form 4** (NVIDIA). `nvidia_8k_2024`: `NoSuchKey` |
| `DEF14A/` | 5 | Todos `NoSuchKey` |

Resumen: 20 de los 27 son páginas de error. De los 7 reales, 6 no corresponden al formulario que dice su nombre. Los tests de ambos lenguajes solo usan `apple_10k_2023.txt`. Lo único útil son los dos 10-K completos de Apple (FY2023 y FY2024, en SGML), como muestra local para inspeccionar. Son datos públicos de la SEC y se pueden descargar directamente.

### `typescript/` (108)
Esta sección se agrupa por carpeta porque es un espejo 1:1 del paquete Python, asíncrono (todo devuelve `Promise`) y escrito en camelCase.

| Ruta | Qué hace | API/elementos clave |
|---|---|---|
| `package.json`, `tsconfig.json`, `jest.config.js`, `.eslintrc.js`, `README.md` (5) | Paquete npm `sec-edgar-toolkit` 0.2.0 (ES2020, commonjs, `strict`). El README documenta la capa baja y los parsers de ownership | Dependencias `fast-xml-parser ^5.2.5`, `node-fetch ^2.7.0`. Scripts `build`, `test`, `lint`, `format`, `type-check` |
| `src/index.ts`, `src/edgar.ts` | Fachada (3 capas) y API fluida | `createClient`, `CompanyQueryBuilder`, `CompanyFilingBuilder`, `CompanyFactsBuilder`, `FinancialData.getKeyRatios` |
| `src/client/` (3: `index`, `edgar-client`, `sync-wrapper`) | Cliente de bajo nivel y un envoltorio «síncrono» que sigue devolviendo `Promise` | `EdgarClient(config)`, `SyncEdgarClient`, `createSyncClient` |
| `src/core/` (15: `attachments`, `collections`, `company`, `exhibits`, `facts`, `filing`, `financials`, `form-10k`, `form-10q`, `form-13f`, `form-8k`, `global-functions`, `index`, `ownership`, `periodic-report`) | Espejo de `core/` de Python. `Financials` devuelve `StatementTable {periods, rows[{concept, values}]}`, sin pandas | `Company.lookup`, `profile()`, `sic()`, `getFilings`, `getFacts`, `getFinancials`, `Filing.getAttachments/getExhibits/text/obj/extractItems/getItem/xbrl`, `EightK.hasItem`, `ThirteenF.topHoldings`, `setIdentity`, `fullTextSearch`, `searchFilings` |
| `src/core/xbrl/` (9: `as-reported`, `index`, `instance-document`, `instance`, `linkbases`, `queries`, `rendered-reports`, `report-html-parser`, `statements`) | Espejo de `core/xbrl/` de Python. Añade métodos que Python no tiene | `XBRLInstance.getBalanceSheet/getIncomeStatement/getCashFlowStatement/getFactsByConcept`, `AsReportedStatements.getStatement`, `parseReportHtml` |
| `src/endpoints/` (5: `company`, `filings`, `fulltext`, `index`, `xbrl`) | Espejo de `endpoints/` | `FilingsEndpoints.parseAtomFeed`, `FullTextSearchEndpoints.search`, `XbrlEndpoints.getFrames` |
| `src/exceptions/` (3: `base`, `errors`, `index`) | Jerarquía de errores más rica que la de Python | `InvalidUserAgentError`, `TimeoutError`, `NetworkError`, `InvalidCIKError`, `CompanyNotFoundError`, `XMLParsingError`, `ConceptNotFoundError`, `ErrorWithContext`, `ErrorHandler.isRetryable/getRetryDelay` (429: 5 s·2ⁿ hasta 60 s; resto: 1 s·2ⁿ hasta 30 s) |
| `src/parsers/` (7: `current-events`, `financial-forms`, `index`, `item-extractor`, `items`, `ownership-forms`, `thirteenf`) | Espejo de `parsers/`; el algoritmo de `ItemExtractor` es idéntico | `ItemExtractor.extractItems`, `OwnershipFormParser.parseAll`, `ThirteenFParser` |
| `src/types/` (12: `analytics`, `company`, `config`, `current-events`, `filing`, `financial-forms`, `index`, `institutional-holdings`, `ownership-forms`, `parsing`, `proxy-statements`, `xbrl`) | Interfaces de TypeScript | `EdgarClientConfig {userAgent, rateLimitDelay, maxRetries, timeout, cache}`, `RequestOptions`, `ParsedOwnershipForm`, `XbrlQueryOptions` |
| `src/utils/` (4: `cache`, `disk-cache`, `http-client`, `index`) | Caché LRU en memoria con estadísticas, caché en disco y cliente HTTP con reintentos | `Cache.get/set/getStats/invalidatePattern/cleanup`, decorador `@cacheable`, `MultiLevelCache` (el nivel persistente es un *stub*), `RequestCache`, `HttpClient.get/getRaw` (*backoff* 2ⁿ s, sin reintentar 4xx salvo 429) |
| `src/__tests__/` (9: `cache`, `current-events`, `edgar-client`, `error-handling`, `financial-forms`, `instance-xbrl`, `ownership-forms`, `parsers`, `xbrl`) | Jest, 121 `it`/`test` | Mismos casos que en Python, más caché y errores |
| `examples/` (5) y `scripts/` (2) | Demos y E2E en vivo (`require('../dist/index.js')`) | `item-extraction-demo.ts` importa `'../typescript/src'`, una ruta incorrecta |
| `tests/fixtures/forms/` (27) | Copia idéntica de los `.txt` de Python | — |

## Reutilizable para el proyecto

**Ninguna fila permite copiar código ni instalarlo con pip, por la AGPL-3.0.** Todo es «solo idea»: se reimplementa desde cero o, mejor, se usa el equivalente de edgartools (MIT).

| Necesidad del proyecto | Ruta exacta y símbolo | Cómo reutilizarlo | Notas |
|---|---|---|---|
| Capa 1: caché y *snapshot* de entrada para las versiones | `python/src/sec_edgar_toolkit/utils/disk_cache.py` · `DiskCache._is_immutable`, `get`, `set` | Solo idea | Regla: todo lo que cuelga de `/Archives/` es inmutable y se guarda sin TTL; `data.sec.gov` (submissions, companyfacts) lleva TTL. Para el *snapshot*, guardar los bytes crudos por hash de URL, con `{url, timestamp}`, da reproducibilidad y trazabilidad. edgartools ya cachea (`CACHE_RULES`); lo que hay que construir es el *snapshot* por versión |
| Capa 1: estados *as-reported* y segmentos (sección 4 «desglose de ingresos por segmento»; sección 6 «ingresos por línea y mix») | `python/src/sec_edgar_toolkit/core/xbrl/as_reported.py` · `AsReportedStatements.get_statement`, `_items_for_node`; `core/xbrl/linkbases.py` · `PresentationLinkbase.ordered_concepts`, `LabelLinkbase.label_for` | Solo idea | Truco útil: aceptar solo las filas dimensionales cuyos miembros aparecen en el árbol de presentación del rol, para no mezclar desgloses de otras notas. edgartools `xbrl/` cubre dimensiones y cosido multiperiodo, así que se usa edgartools |
| Principio 3, trazabilidad: cada cifra con su fuente | `python/src/sec_edgar_toolkit/core/facts.py` · `CompanyFacts.get_fact` (`accn`, `filed`, `form`, `end`, `start`); `core/xbrl/queries.py` · `build_fact_records` (`accession_number`, `period`=frame) | Solo idea | Esquema mínimo de fuente por cifra: concepto + `accn` + `filed` + periodo (`start`/`end`). edgartools da los mismos campos |
| Capa 1/tests: cuadrar cifras con la presentación de la SEC (escala, negativos) | `python/src/sec_edgar_toolkit/core/xbrl/report_html.py` · `parse_report_html`, `_parse_multipliers`, `parse_report_number`, `normalize_period_label` | Solo idea | Los R-files de `FilingSummary.xml` sirven de segunda fuente para validar escala y signo en los tests contra el 10-K de AAPL |
| Capas 1 y 4: texto del 10-K, Items 1, 1A y 7 (secciones 4, 5 y 8; MD&A para catalizadores) | `python/src/sec_edgar_toolkit/parsers/item_extractor.py` · `ItemExtractor._extract_items_from_content`, `_is_in_toc`; `parsers/items.py` · `TenKItem` | Solo idea | Heurística para saltar el índice: elegir la coincidencia del encabezado que abarca más texto. Es frágil, porque corta en referencias cruzadas («see Item 7.») y no distingue Part I/II en el 10-Q. Se usan `TenK.business`, `.risk_factors` y `.management_discussion` de edgartools |
| Capa 1: comparables (sección 7 y anexo A5) y medianas sectoriales | `python/src/sec_edgar_toolkit/endpoints/xbrl.py` · `XbrlEndpoints.get_frames` | Solo idea | El endpoint público `data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/CY{año}[Q{n}[I]].json` da un concepto para todas las empresas en un periodo: base para medianas por SIC. Hay que comprobar antes si edgartools lo expone |
| Capa 1: alertas de riesgo por texto (sección 8: «going concern», «material weakness») | `python/src/sec_edgar_toolkit/endpoints/fulltext.py` · `FullTextSearchEndpoints.search` | Solo idea | El `_id` de cada resultado es `accession:document`; los parámetros son `forms`, `dateRange=custom`, `startdt`/`enddt` y `ciks` |
| Capa 1: gobierno (sección 9) y estructura accionarial (sección 1) | `python/src/sec_edgar_toolkit/core/ownership.py` · `OwnershipForm.owners`, `.footnotes`; `core/thirteenf.py` · `ThirteenF.top_holdings`, `by_issuer` | Solo idea | Cubren Form 4 (insiders, roles) y el 13F de una gestora. No dan los accionistas de un emisor. edgartools (`ownership`, `thirteenf`, `beneficial_ownership`) cubre más |
| Capa 4: catalizadores a partir de los 8-K de resultados | `python/src/sec_edgar_toolkit/core/form_8k.py` · `EightK.has_item("2.02")`, `press_releases`; `core/attachments.py` · `Attachment.is_press_release` | Solo idea | Identificar la nota de prensa por el tipo EX-99* de la página índice, no por el nombre del archivo. edgartools `EarningsRelease` ya parsea sus tablas |
| Capa 2: lista de conceptos (incluido IFRS para 20-F) y lección de errores | `python/src/sec_edgar_toolkit/core/financials.py` · `INCOME_STATEMENT_CONCEPTS`, `BALANCE_SHEET_CONCEPTS`, `CASH_FLOW_CONCEPTS`, `IFRS_INCOME_STATEMENT_CONCEPTS`, `_collect` | Solo idea | **Contraejemplo**: no filtra por duración ni por `frame`, se queda con 4 periodos e ignora el filing. En nuestros tests hay que exigir duración de unos 365 días y el `accn` del filing |
| CI/tests: test en vivo con oráculo (fase 2, «las cifras de AAPL cuadran con el 10-K») | `python/scripts/live_features_e2e.py` · `check()`; `python/scripts/live_e2e.py` | Solo idea | Oráculo público: AAPL FY2025, `NetIncomeLoss` = 112.010 M USD y BPA básico 7,49 (2025-09-27). Patrón: `tests/` sin red y, aparte, `scripts/live_*` o un marcador `@pytest.mark.live` que se ejecuta a mano |
| CI/tests: tests de la capa 1 sin red | `python/tests/test_instance_xbrl.py` · `LocalHttp.get_raw` con XML en línea | Solo idea | Los lectores reciben un objeto con `get_raw(url)` (*duck typing*), así que en los tests se inyectan archivos locales |
| CI | `.github/workflows/python-ci.yml` | Solo idea (escribir el nuestro) | Filtros `paths:`, matriz de versiones, `ruff check`, `ruff format --check`, `mypy` y `pytest --cov`. Al nuestro hay que añadirle `windows-latest` y 3.13, que aquí faltan |
| Configuración: dependencias opcionales con error útil | `python/pyproject.toml` · `[project.optional-dependencies]`; `python/src/sec_edgar_toolkit/utils/optional_deps.py` · `require_pandas` | Solo idea | Extras propios `[pdf]` (weasyprint), `[ia]` (cliente LLM) y `[ui]` (streamlit), con un mensaje que diga qué instalar |
| Docs/onboarding: seguridad, cita y aviso legal (sección L) | `SECURITY.md`; `CITATION.cff`; `README.md` § Disclaimer | Solo idea | Aviso de no afiliación con la SEC y «data as-is, verify independently» para el texto legal. `SECURITY.md` propio con canal privado de reporte |
| UI Streamlit, editor, versiones, plantilla/PDF, LLM, datos de mercado, gobierno de agentes de IA | — | — | Este repo no los contiene (ver «Lo que NO contiene») |

**Qué cubre de cada sección de [estructura-informe.md](../estructura-informe.md)** (siempre como idea; edgartools lo cubre igual o mejor):

| Sección | Lo que hay aquí | Lo que falta |
|---|---|---|
| 1 Portada / market data | Perfil desde submissions: `Company.sic_description`, `fiscal_year_end`, `exchange`, `tickers` | Precio, market cap, EV, nº de acciones (no usa `dei:EntityCommonStockSharesOutstanding`), máx/mín 12m, comportamiento relativo |
| 1 Estructura accionarial | Form 3/4/5 (`OwnershipForm`), 13F por gestora (`ThirteenF`) | 13D/G (hay SC 13G en los fixtures, sin parser), agregación por emisor, DEF 14A |
| 1, 6 y A1: datos financieros | `Financials` (4 periodos, conceptos fijos), `CompanyFacts.get_fact` (histórico completo), `CASH_FLOW_CONCEPTS` con capex, dividendos, recompras, D&A y SBC | EBITDA, FCF, DFN, ROE, ROCE, TTM, estimaciones |
| 2 Conclusiones / 3 La compañía en 8 gráficos | — | Todo |
| 4 Descripción del negocio | Item 1 (`TenK.business`), segmentos *as-reported* (`AsReportedStatements`) | Resumen con IA |
| 5 Industria y mercado | `get_frames` (agregados de un concepto entre empresas) | Tamaño y CAGR del mercado |
| 7 Valoración | `get_frames` como base de peers | DCF, WACC, múltiplos |
| 8 Análisis de riesgos | Item 1A (`TenK.risk_factors`), búsqueda de texto completo | Resumen con IA y citas. `FinancialFormParser.get_risk_factors` (severidad por palabras clave) no sirve |
| 9 Gobierno corporativo | Roles de Form 4 (director, *officer*, 10 %) | Consejo, retribución, comisión de auditoría, auditor (DEF 14A solo tiene tipos) |
| A4 Comportamiento histórico | `CompanyFacts.get_fact`, `Company.get_filings(deep=True)` (pagina más allá de los ~1000 filings recientes) | Ratios |
| A5 Comparables | `XbrlEndpoints.get_frames` | Tabla de peers |
| L Información legal | Disclaimer del README | — |

## Patrones de organización y onboarding

| Patrón | Qué hace bien | ¿Trasladable? |
|---|---|---|
| Fachada documentada en tres capas | El docstring de `__init__.py` enseña las 3 formas de uso (objetos → fluida → JSON crudo), con un ejemplo de cada una | Sí: el docstring del paquete y el README explican capas 1-4 → UI con un ejemplo mínimo |
| Parsers puros separados del I/O | `instance_document.py`, `linkbases.py` y `report_html.py` declaran «No I/O happens in this module». La lectura de red está en `RenderedReportReader`/`AsReportedStatements`, con el HTTP inyectado (`get_raw`) | Sí: convención para `ingesta/` y `calculo/`, que facilita testear sin red |
| Núcleo ligero con extras | Base con `requests` únicamente; pandas y lxml son opcionales, con un error accionable si faltan | Sí, para weasyprint, kaleido, streamlit y LLM |
| Configuración por entorno | `SEC_EDGAR_TOOLKIT_USER_AGENT`, `SEC_EDGAR_TOOLKIT_CACHE_DIR` y `.env.example` | Ya lo hacemos con `EDGAR_IDENTITY`; añadir la ruta de caché y *snapshots* fuera de OneDrive |
| Tests sin red y E2E en vivo separados | `responses` y *stubs* en `tests/`; `scripts/live_*.py` con `check()` y salida no cero si falla | Sí, con un marcador pytest `live` que no se ejecute en la CI |
| CI por subpaquete y release por tag | `paths:`, matriz de versiones y publicación al crear `v*` (PyPI, conda, npm OIDC) | Parcial: el filtro de rutas y la matriz sí; la publicación no aplica a un SaaS |
| Paridad documentada entre lenguajes | Tabla «Functionality Comparison» en el README | La idea de una tabla de capacidades por capa sí |
| Seguridad y cita | `SECURITY.md` (OWASP) y `CITATION.cff` | Sí, `SECURITY.md` |
| Lo que hace mal | No hay `CONTRIBUTING.md` (aunque el README lo enlaza), CHANGELOG, `.pre-commit-config.yaml` (pre-commit está en `dev`), dependabot, plantillas de issue/PR, sitio de docs ni `CLAUDE.md`/`.claude`. Los *badges* son estáticos. Los ejemplos están rotos. El `Makefile` (black) no coincide con la CI (`ruff format`). Hay dos workflows de TS duplicados | Evitarlo: `CONTRIBUTING` y `CLAUDE.md` propios; los ejemplos se ejecutan en la CI |

## Lo que NO contiene

Verificado con `grep -rliE` sobre `.py`, `.ts`, `.js`, `.md`, `.yml` y `.toml`, excluidos los fixtures. Los únicos aciertos fueron palabras sueltas como «charter», «clearAllMocks» o campos `market_cap: None`.

- **Precio y datos de mercado** (yfinance, Alpha Vantage, market cap, acciones en circulación por `dei`). `FinancialMetrics.market_cap`/`pe_ratio` siempre valen `None` («Would need stock price data»).
- **Métricas de la capa 2**: EBITDA, FCF, deuda neta, ROIC, EV, DCF, WACC, TTM, ajuste por *splits*, cosido multiperiodo y forecasting. Solo hay D/A, D/E y ratios heurísticos.
- **Vencimientos de deuda** (`LongTermDebtMaturities…`): no aparecen.
- **Gráficos** (Plotly, matplotlib, kaleido), **plantillas HTML/Jinja2 y PDF** (WeasyPrint, reportlab).
- **UI y API web** (Streamlit, FastAPI, Flask), **editor**, **persistencia y versiones** (SQLAlchemy, SQLite, *snapshot*).
- **LLM y prompts** (OpenAI, Anthropic, LangChain, Ollama).
- **Parsers de DEF 14A (proxy), auditor y 13D/G**: `types/proxy_statements.py` solo tiene tipos.
- **Gobierno de agentes de IA**: no hay `CLAUDE.md`, `.claude/` ni skills.
- **Onboarding**: no hay `CONTRIBUTING.md`, CHANGELOG, `docs/`, `.pre-commit-config.yaml`, dependabot ni plantillas de issue/PR.
- **Soporte declarado de Python 3.13 y CI en Windows**.

## Riesgos

| Tipo | Riesgo |
|---|---|
| Licencia | **AGPL-3.0**: si se incorpora o se instala con pip en el SaaS, hay que publicar el código del servicio a sus usuarios. Solo se toman ideas y se reimplementan; los fixtures son datos públicos de la SEC y se descargan directamente de EDGAR |
| Dependencias | Las de Python son ligeras (`requests`; pandas y lxml opcionales). El parseo de XML de terceros usa ElementTree o lxml (`recover=True`, `huge_tree` opcional) sin `defusedxml`. En TS, `node-fetch` 2 está en modo mantenimiento. Los lockfiles no se versionan aunque el Dockerfile usa `--frozen-lockfile` |
| Windows / Python 3.13 | Clasificadores y CI cubren solo 3.8-3.12 en Ubuntu; `.python-version` es 3.8 (EOL). El `Makefile` es POSIX (`rm -rf`, `find`). `AsyncEdgarClient` usa `asyncio.get_event_loop()` dentro de una corrutina (con bucle activo, así que funciona). El código usa `pathlib` y no tiene rutas POSIX fijas, por lo que en principio funcionaría en Windows, pero no está probado |
| Calidad: errores confirmados al leer el código | `parsers/current_events.py::_extract_item_content`: el patrón `[^]*?` es inválido en Python («unterminated character set»), así que `get_current_events()` falla en cuanto encuentra un «ITEM x.xx». `Financials._collect` no filtra por duración, por lo que puede mezclar valores trimestrales publicados en el 10-K, e ignora el filing (`accession_number`). `get_frames(instantaneous=True)` sin trimestre no añade la `I`. `OwnershipFormParser` solo reconoce `"true"` en `isDirector`/`isOfficer`; muchos Form 4 reales usan `1`/`0`, sin cubrir en tests (fixtures sintéticos con `true`) |
| Calidad: heurísticas poco fiables | `FinancialFormParser` (regex «$ + número»; *quick ratio* = 0,8 × activo corriente / pasivo corriente) y `CurrentEventParser` (nombres por regex `[A-Z][a-z]+ [A-Z][a-z]+`). `ItemExtractor` puede cortar en referencias cruzadas y confundir Part I y Part II del 10-Q, y no tiene tests unitarios en Python |
| Calidad: tests y fixtures | 20 de los 27 fixtures son errores S3 `NoSuchKey`; 6 de los 7 reales están mal etiquetados; los mismos ~19,7 MB están duplicados en `python/` y `typescript/`. Hay aserciones siempre verdaderas (`… is None or True`, `len(x) >= 0`). Los *badges* de cobertura son estáticos. 3 de los 7 ejemplos de Python no funcionan (usan `await` sobre métodos síncronos) |
| Solapamiento | Todo lo útil está mejor resuelto en edgartools (MIT), que es la dependencia elegida. Consultar este repo solo si edgartools no cubre algo concreto, como los frames o la búsqueda de texto completo |
