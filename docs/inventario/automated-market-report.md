# automated-market-report

- **Repo / alcance / licencia**: github.com/hgnx/automated-market-report (copia local `automated-market-report-main`, último cambio de agosto de 2023). Alcance: todo el repo. **Sin licencia**: no hay `LICENSE` y la búsqueda de "licen" no da resultados, así que todos los derechos están reservados. **Solo se pueden tomar ideas, no código.** La fuente `assets/NotoSansKR[wght].ttf` es de Google Noto (licencia OFL propia, independiente del repo).
- **Cobertura**: 18 archivos en total. **16 leídos completos** (10 `.py` en `tools/`, `main.py`, `setup.py`, `README.md`, `assets/README.md`, `requirements.txt`, `.gitignore`), **0 solo por firmas**, **2 caracterizados por muestreo**: `output.pdf` (las 2 páginas, vistas enteras: PDF 1.4 generado con ReportLab y fechado el 2023-08-16) y `assets/NotoSansKR[wght].ttf` (10,4 MB, TrueType variable, de él solo se miró la cabecera). 16 + 0 + 2 = 18.

## Qué contiene

Es un script de un solo flujo, sin paquete instalable: `tools/` no tiene `__init__.py` y funciona como *namespace package*. Genera un PDF diario de mercado en A4, de 2 páginas.

| Ruta | Qué hace | API/elementos clave (nombres exactos) |
|---|---|---|
| `main.py` | Orquesta todo a nivel de módulo, sin funciones `main`: registra la fuente, define la plantilla ReportLab, la cabecera y los pies de tabla, llama a cada módulo de `tools`, maqueta las tablas lado a lado, monta el `story`, genera `output.pdf` y borra los PNG temporales | `COMPANY_NAME`, `AUTHOR`, `AUTHOR_EMAIL`, `FILE_NAME`, `ASSETS_FOLDER`, `class MyDocTemplate(BaseDocTemplate)` (`__init__` con `Frame` de 6×10 in centrado; `afterFlowable` notifica `TOCEntry`, aunque no se usa ningún índice), `header_table` (5 columnas: empresa / título / autor+email+fecha), `add_news_items`, `add_news_source`, `create_table(data, column_widths, row_heights, styles)`, constantes `TOTAL_TABLE_WIDTH`, `COLUMN_WIDTH`, `TABLE_ROW_HEIGHT`; metadatos del PDF `title`/`author`/`subject` |
| `setup.py` | No es un setup de packaging: es un asistente interactivo que pide la clave de FRED y escribe `config.ini` (secciones `api.fred` e `info.src`) | `banner()`, `configparser.RawConfigParser` |
| `tools/indices.py` | Cierre y rentabilidades 1D/1W/MTD/1M/YTD de 13 índices mundiales vía yfinance, con reintentos | `indices_symbol` (dict nombre→ticker: `^DJI`, `^GSPC`, `^IXIC`, `^RUT`, `^STOXX`…), `get_indices_data(ticker, max_retries=3, wait_time=5) -> tuple`, `get_all_indices_data() -> list[list]` |
| `tools/ficc.py` | Lo mismo para divisas y materias primas (yfinance) y para los rendimientos del Tesoro de EEUU (FRED). Lee `config.ini` al importarse y hace `sys.exit` si falta | `ficc_symbol` (`DGS2`, `DGS10`, `T10Y2Y`, `DX-Y.NYB`, `EUR=X`, `CL=F`, `GC=F`…), `us_yield(ticker)` (`fredapi.Fred.get_series` con `frequency`/`aggregation_method="eop"`/`units="pch"`), `get_other_data(ticker)`, `get_all_ficc_data()` |
| `tools/etfs.py` | Variación diaria (%) de los 11 ETF sectoriales SPDR | `get_etf_data(ETF, max_retries, wait_time)`, `etfs_symbol` (sector GICS→ETF: `XLK`, `XLV`, `XLF`, `XLY`, `XLC`, `XLI`, `XLP`, `XLE`, `XLU`, `XLRE`, `XLB`) |
| `tools/us_plots.py` | 3 gráficos Plotly exportados a PNG con `write_image` (necesita kaleido): intradía horario del NASDAQ y del S&P 500 (líneas) y variación sectorial (barras) | `create_nasdaq_graph(filename)`, `create_sp500_graph(filename)`, `create_sector_change_graph(filename)`, `create_plots()` (escribe en `assets/`) |
| `tools/top_movers.py` | Raspa las tablas de mayores subidas y bajadas de CNN Money con `pd.read_html` | `URL`, `get_similar_column_name(df, col_str)`, `process_data(df)`, `get_top_movers_data()` |
| `tools/calendar.py` | Calendario económico de Investing.com (importancia 3, UTC) con `urllib` + `pd.read_html`; filtra los valores no numéricos | `URL`, `USER_AGENT`, `DEFAULT_HEADERS`, `is_valid_value`, `fetch_data(url, user_agent, max_retries, wait_time)`, `extract_and_process_data(raw_data)`, `get_all_economic_data()` (devuelve filas de reserva "No important event today" / "Error…") |
| `tools/mainnews.py` | Raspa titulares de Reuters (Macro Matters) y FT (Markets) con BeautifulSoup y selectores CSS con clases *hash*; acorta las URL | `parse(url, …)`, `extract_reuters`, `extract_ft`, `get_news`, `get_shortened_news`, `format_news_title`, `format_news_url` |
| `tools/url_shortener.py` | Acortador con alternativas en cadena: is.gd → v.gd → tinyurl | `isgd`, `vgd`, `tinyurl`, `get_shortened_url(url)` |
| `tools/tablestyle.py` | Estilos de tabla ReportLab declarados como listas de comandos y combinables con `+` | `header_style`, `common_style` (fuente `NotoSansKR` de 5 pt, sin rejilla), `overview_style`, `movers_style`, `events_style`, `news_style` |
| `tools/misc.py` | Lee `info.src` de `config.ini` y hace `sys.exit` si falta | `src` |
| `README.md` | Funciones, tabla de fuentes de datos (proveedor y librería), instalación en 6 pasos, mejoras futuras (checklist) y descargo de responsabilidad | — |
| `assets/README.md` | Atribución de la fuente Noto Sans KR | — |
| `requirements.txt` | Versiones fijadas: `fredapi==0.5.1`, `pandas==2.0.3`, `plotly==5.16.0`, `reportlab==4.0.4`, `beautifulsoup4==4.12.2`, `requests==2.31.0`, `tqdm==4.66.1`, `yfinance==0.2.28`, `configparser==6.0.0` | Faltan `kaleido` (para `write_image`) y `lxml`/`html5lib` (para `read_html`) |
| `.gitignore` | Ignora `*.ini` (la clave API), `*.png`, `.env`, notebooks y `.vscode` | — |
| `output.pdf` | Ejemplo de salida. Página 1: cabecera, tablas de índices y FICC, 3 gráficos, mayores subidas y bajadas, eventos del día. Página 2: cabecera repetida y titulares con URL acortada | Producer: ReportLab |
| `assets/NotoSansKR[wght].ttf` | Fuente variable CJK que se registra con `TTFont('NotoSansKR', …)` | — |

## Reutilizable para el proyecto

Todo es **solo idea**, porque el repo no tiene licencia. Los nombres de librería (fredapi, yfinance) se refieren a dependencias pip de terceros con licencia propia, no al código de este repo.

| Necesidad del proyecto | Ruta exacta y símbolo | Cómo reutilizarlo | Notas |
|---|---|---|---|
| Capa 1 / datos de mercado: rentabilidad relativa (estructura §1, «Comportamiento relativo en bolsa»: -1m/-3m/-12m/YTD vs índice) | `tools/indices.py` `get_indices_data` (patrón 1D/1W/MTD/1M/YTD sobre `history`) | Solo idea | Reescribirlo con una sola descarga diaria y calcular las ventanas en pandas (aquí hay 4 llamadas por ticker). Añadir -3a y -5a y base 100 |
| Capa 1 / E6 índices de referencia (S&P 500 + ETF sectorial SPDR) | `tools/etfs.py` `etfs_symbol`; `tools/indices.py` `indices_symbol` (`^GSPC`) | Solo idea; la lista de tickers SPDR es un dato público | Confirma la propuesta E6. Hace falta mapear SIC o sector → ETF por cuenta propia |
| Capa 2 / Valoración (§7, DCF: Rf del WACC) | `tools/ficc.py` `us_yield` con FRED `DGS10` | Idea + dependencia pip `fredapi` (o la API REST de FRED directamente) | Rf = UST 10Y desde FRED, fuente oficial y gratuita. Requiere `FRED_API_KEY` en `.env` |
| Capa 1 / robustez de la ingesta | `fetch_data`, `get_indices_data`, `get_top_movers_data` (bucle `max_retries`/`wait_time`, y si falla todo una fila «Error» de reserva) | Solo idea | Usar `tenacity` o reintentos propios. Una fila de reserva («dato no disponible») permite generar el borrador aunque falle una fuente |
| Capa 3 / gráficos (§3, «La compañía en 8 gráficos») | `tools/us_plots.py` `create_*_graph` → `fig.write_image` → `Image` en una rejilla de 3 columnas (`table_graph`) | Solo idea | Mini-gráficos en rejilla de 3 por fila con tamaño fijo. El proyecto debe exportar SVG (kaleido) en vez de PNG |
| Capa 3 / plantilla: cabecera de página (A4) | `main.py` `header_table` (empresa / título / autor+email+fecha, `LINEBELOW`) | Solo idea | Cabecera de 3 zonas repetida en cada página. En WeasyPrint se hace con `@page { @top-left/@top-center/@top-right }` |
| Capa 3 / tablas densas | `tools/tablestyle.py` (`common_style` + estilo específico combinados) | Solo idea | Patrón de un estilo base más un estilo por tipo de tabla. Equivale a una clase CSS base + modificadores. Línea solo bajo la cabecera y números alineados a la derecha |
| Plantilla/PDF: metadatos | `main.py` `MyDocTemplate(..., title=, author=, subject=)` | Solo idea | En WeasyPrint: `<title>` y `<meta name="author">` en la plantilla Jinja2 |
| Plantilla/PDF: limpieza de temporales | `main.py`, bloque «Remove used images» | Solo idea | Mejor usar `tempfile` o SVG en línea en el HTML |
| Configuración / secretos | `setup.py` (asistente que escribe `config.ini`) + `.gitignore` `*.ini` | Solo idea (el proyecto usa `.env`) | Contraejemplo de lo que no hay que hacer: leer la configuración al importar con `sys.exit` y con ruta relativa al cwd |
| Docs/onboarding | `README.md`, tabla «Data Sources» (categoría / proveedor / librería) | Solo idea | Merece la pena copiar el formato de tabla de fuentes en el README del proyecto. Sirve también para la trazabilidad |
| Legal (§L) | `README.md`, sección «Disclaimer» | No (el proyecto ya tiene `plantillas/legal/descargo.md`) | — |

**Cobertura de `estructura-informe.md`**: §1, solo las ideas para «Comportamiento relativo en bolsa» (ventanas de rentabilidad e índice o ETF sectorial de referencia); §3, solo el patrón de rejilla de gráficos; §7, solo la idea de Rf desde FRED. No cubre las secciones 2, 4, 5, 6, 8, 9, A1-A5 ni L (sus datos son de mercado diario, no de empresa).

## Patrones de organización y onboarding

- **Bien hecho y trasladable**: un módulo por fuente de datos (`tools/<fuente>.py`), cada uno con una función pública `get_all_*_data()` que devuelve filas listas para tabla (encabezado + filas). Es un contrato simple entre ingesta y maquetación. El README tiene una tabla de fuentes, una instalación numerada en pocos pasos, una lista de mejoras como checklist y un descargo. Las dependencias tienen la versión fijada. Hay un `output.pdf` de ejemplo para ver el resultado sin ejecutar nada (idea útil: incluir un PDF de AAPL de referencia en `docs/`). Los secretos están fuera de git (`*.ini`).
- **Mal hecho, no trasladable**: la lógica está a nivel de módulo en `main.py` (no se puede importar ni testear). La configuración se lee como efecto secundario al importar, con `sys.exit`. Las rutas dependen del cwd (`os.getcwd()`, `config.ini`). El código de reintentos está duplicado en 6 sitios. Se usa `print` en vez de `logging`. Faltan type hints en la mitad de las funciones. No hay tests, CI, CLI con argumentos, `pyproject.toml`, `LICENSE`, `CONTRIBUTING` ni CLAUDE.md/.claude.

## Lo que NO contiene

Comprobado con `find` y con `grep -rniE` sobre `.py`, `.md` y `.txt` (patrones: test, jinja, weasy, html, streamlit, sqlite, sqlalchemy, llm, openai, anthropic, edgar, sec.gov, xbrl, logging, argparse, dotenv, license):
- Datos SEC/EDGAR, XBRL, estados financieros, 10-K/10-Q (capa 1 de empresa).
- Métricas fundamentales, múltiplos, EV, DCF, comparables, proyecciones (capa 2).
- Plantilla HTML/Jinja2 y WeasyPrint (usa ReportLab, una opción ya descartada en el plan); exportación SVG.
- LLM o IA de cualquier tipo, resúmenes, citas (capa 4); análisis de sentimiento (solo figura como mejora futura).
- UI Streamlit, editor, vista previa.
- Versiones, *snapshots*, persistencia, SQLite/SQLAlchemy.
- Tests, CI (no hay `.github/`), `pyproject.toml`, CLI con argumentos, `logging`, `.env`/dotenv.
- `LICENSE`, `CONTRIBUTING`, CLAUDE.md, `.claude/`, skills.
- Formato numérico localizado (coma decimal, negativos entre paréntesis) e i18n.

## Riesgos

- **Licencia**: sin licencia, así que no se puede copiar ni adaptar código, ni siquiera fragmentos. Solo ideas, reescritas desde cero.
- **Fuentes frágiles o con términos de uso restrictivos**: raspado de CNN Money (`money.cnn.com/data/hotstocks`, probablemente obsoleto), Investing.com, Reuters y FT con selectores CSS de clases *hash* (se rompen al cambiar el sitio, y Reuters y FT prohíben el raspado). Además depende de acortadores externos (is.gd, v.gd, tinyurl). Nada de esto sirve para un SaaS.
- **Dependencias**: `pandas==2.0.3` no tiene *wheels* para Python 3.12/3.13, así que el entorno no se puede instalar en 3.13. `yfinance==0.2.28` está obsoleto frente a los cambios de la API de Yahoo. Al `requirements.txt` le faltan `kaleido` y `lxml`/`html5lib`. `configparser==6.0.0` es un *backport* innecesario.
- **Windows**: funciona (`cls`/`clear`, `os.path`). Pero depende del cwd, y el nombre de fuente con corchetes `NotoSansKR[wght].ttf` puede dar problemas al escapar rutas en shells. La fuente CJK de 10 MB es innecesaria para el proyecto (Montserrat + Inter).
- **Calidad y corrección**: en `us_yield` se usa `abs()` en las variaciones de rendimientos (falsea el diferencial negativo `T10Y2Y`). En `get_other_data`/`get_indices_data` se pasan a la vez `period` y `start`. `afterFlowable`/`TOCEntry` es código muerto. Hay `except:` sin tipo. No hay tests.
