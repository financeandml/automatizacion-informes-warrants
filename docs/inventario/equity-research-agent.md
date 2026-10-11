# equity-research-agent

- **Repo / alcance / licencia**: `github.com/CarlosFinEngg/equity-research-agent` (copia local `scratchpad/repos/equity-research-agent-main`); alcance: todo el repo; licencia **MIT** (`LICENSE`, "Copyright (c) 2025 Yaran Zhou"). Paquete declarado en `pyproject.toml` como `efund-agent` 0.1.0, `requires-python >=3.11`.
- **Cobertura**: 27 archivos en total. Leídos completos: 26 (todo el código Python, prompts, README, LICENSE, `.gitignore`, `pyproject.toml`). Solo firmas: 0. Por muestreo: 1 (`uv.lock`, 610 KB: cabecera, nº de paquetes —218 `[[package]]`—, marcadores de resolución para 3.11/3.12/≥3.13 y wheels Windows/cp313 de `numpy`, `pandas`, `shapely`, `greenlet`, `py-mini-racer`, `pexpect`). No hay tests, fixtures, datos ni imágenes.

## Qué contiene

Sistema multiagente sobre **Google ADK** (`google-adk==1.1.0`) que analiza **acciones chinas A-share** (tickers de 6 dígitos, datos vía `akshare`) y genera un informe en **chino** en Markdown → HTML → PDF (WeasyPrint).

| Ruta | Qué hace | API/elementos clave (nombres exactos) |
|---|---|---|
| `README.md` | Descripción, estructura, instalación con `uv sync`, `.env`, ejecución `adk web` / `adk run stock_analysis_agent`, convención de nombres de informes, disclaimer | Salida `reports/equity_research_report_<company_name>_<ticker>_<YYYYMMDD>.md/.html/.pdf`; variables `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `SMITHERY_API_KEY`. Menciona carpeta `mcp/` que no existe en el repo |
| `pyproject.toml` | ~190 dependencias **todas fijadas con `==`** (volcado de `pip freeze`, incluye jupyter/ipykernel/debugpy) | `google-adk`, `litellm`, `akshare`, `weasyprint==65.1`, `markdown`, `jinja2`, `playwright`, `mcp[cli]`, `mcp-query-table`, `sqlalchemy`, `pandas`, `numpy`, `schedule`, `pandoc` |
| `uv.lock` | Lockfile de uv (muestreado) | 218 paquetes; resuelve para Python <3.12, 3.12 y ≥3.13; wheels `win_amd64` presentes (incl. cp313) |
| `.gitignore` | Ignora venv, `.env`, `reports/*`, **`*.md`** y **`*test*`** (oculta todo test y Markdown), y archivos privados del autor | `reports/*`, `!reports/`, `*.ipynb*` |
| `LICENSE` | MIT | — |
| `stock_analysis_agent/__init__.py` | Expone el agente raíz para ADK | `root_agent` |
| `stock_analysis_agent/agent.py` | Orquestación: un `ParallelAgent` con 4 subagentes y un `LlmAgent` coordinador con herramientas | `analysis_agent = ParallelAgent(name="equity_research_pipeline", sub_agents=[fundamental_agent, technical_agent, fund_agent, policy_agent])`; `root_agent = LlmAgent(name="coordinator_agent", tools=[get_current_time, AgentTool(google_search_agent), AgentTool(analysis_agent), combine_reports], output_key="root_agent_output")`; selección de modelo `LiteLlm(model=MODEL)` si no es Gemini |
| `stock_analysis_agent/config.py` | Lista de modelos y modelo activo, validado con `assert` | `GEMINI_LIST`, `OTHER_LIST` (`openai/gpt-4o-mini`, `openai/gpt-4.1-mini`, `openai/o4-mini`), `MODEL = "gemini-2.5-pro-preview-06-05"` |
| `stock_analysis_agent/prompt.py` | Prompt del coordinador (3 pasos: ticker→nombre, análisis paralelo, `combine_reports`) | `COORDINATOR_AGENT_PROMPT` |
| `stock_analysis_agent/callbacks.py` | Callbacks ADK: vuelca `state[f"{agent_name}_output"]` a `reports/{agent_name}_report.md`; log del estado | `save_agent_output(callback_context: CallbackContext)`, `call_log(callback_context)` |
| `stock_analysis_agent/tools.py` | Herramientas comunes: hora, agente buscador, **ensamblado de informe y exportación HTML/PDF**, email SMTP, programación diaria | `get_current_time() -> dict`; `google_search_agent` (`LlmAgent` + `google_search`); `combine_reports(provided_ticker, company_name) -> dict` (concatena `fundamental/technical/fund/policy_agent_report.md` con separadores `<!-- ===== X SECTION ===== -->`, `markdown.markdown(..., extensions=["tables"])`, CSS embebido, `HTML(string=...).write_pdf(path, stylesheets=[CSS(string=...)])` con `@page { size: A4; margin: 2cm; }`; devuelve `{"status","output_report_name","report_path"}`); `email_report(report_path, recipient_email)` (smtplib STARTTLS, credenciales de ejemplo en el código); `schedule_email_report(report_path, recipient_email, schedule_time)` (bucle infinito `schedule`) |
| `sub_agents/*/__init__.py` (4) | Reexportan cada agente | `fundamental_agent`, `technical_agent`, `fund_agent`, `policy_agent` |
| `sub_agents/fundamental_agent/agent.py` | `LlmAgent` de análisis fundamental con callbacks | `output_key="fundamental_agent_output"`, `before_agent_callback=call_log`, `after_agent_callback=save_agent_output` |
| `sub_agents/fundamental_agent/tools.py` | Indicadores financieros históricos de akshare a dict anidado `{fecha: {indicador: str}}` | `fetch_stock_financial_indicators(symbol, start_year) -> Dict` (`ak.stock_financial_analysis_indicator`) |
| `sub_agents/fundamental_agent/prompt.py` | Prompt largo (chino) con **plantilla de secciones** de análisis fundamental: rentabilidad, crecimiento, liquidez/solvencia, eficiencia/rotación, flujo de caja, inversión/dividendos, estructura de capital, composición del beneficio, **DuPont**; cada sección = datos → tendencia → insights | `FUNDAMENTAL_AGENT_PROMPT`; regla "Source Exclusivity" (solo datos de la herramienta, no calcular ratios ya provistos) |
| `sub_agents/technical_agent/agent.py` | `LlmAgent` técnico | `output_key="technical_agent_output"` |
| `sub_agents/technical_agent/tools.py` | Cálculo determinista de indicadores técnicos sobre precios diarios (pandas/numpy) | `calculate_technical_indicators(provided_ticker) -> dict`: volatilidad 20d anualizada (log-returns·√252), RSI 14 (media simple), MACD 12/26/9, Bollinger 20±2σ, KDJ 9, `volume_amplification` (vol/MA20), MA5…MA250, flags de máximos/mínimos 20/126/252/histórico, rachas alcistas/bajistas, rachas de volumen, precio-volumen, cruces de medias y de bandas; fuente `ak.stock_zh_a_hist(adjust="qfq")` |
| `sub_agents/technical_agent/prompt.py` | Prompt con estructura de informe técnico en 8 secciones (resumen, tendencia, momentum, volatilidad, señales, patrones, tendencia primaria con regresión 250d, insights) | `TECHNICAL_AGENT_PROMPT` |
| `sub_agents/fund_agent/agent.py` | `LlmAgent` de flujos de fondos | `output_key="fund_agent_output"` |
| `sub_agents/fund_agent/tools.py` | Wrappers akshare de flujos de capital, distribución de coste, tenencias institucionales, Stock Connect | `get_last_quarter()` (formato `"YYYYQ"`), `fetch_stock_individual_fund_flow(stock, market)`, `fetch_stock_chip_distribution(symbol, adjust="")`, `fetch_stock_institute_hold_detail(stock, quarter)`, `fetch_stock_hsgt_individual_detail(symbol, start_date, end_date)`; patrón común `df.astype(str)` → dict por clave; errores devueltos como `{"status":"error","message"}` |
| `sub_agents/fund_agent/prompt.py` | Prompt de flujos de fondos y tenencias institucionales con estructura de 5 secciones | `FUND_AGENT_PROMPT` (cita las herramientas por nombre akshare, no por el de la función Python) |
| `sub_agents/policy_agent/agent.py` | `LlmAgent` de política/regulación con `AgentTool(google_search_agent_for_policy)`; MCP `sequential-thinking` comentado; `load_dotenv("stock_analysis_agent/.env")` | `output_key="policy_agent_output"`, `smithery_api_key` |
| `sub_agents/policy_agent/tools.py` | Subagente buscador para política | `google_search_agent_for_policy` |
| `sub_agents/policy_agent/prompt.py` | Prompt (chino) de análisis de políticas en 6 ejes (macro, regulación sectorial, regional, comercio internacional, medio ambiente/seguridad, consumo) con calificación alto/medio/bajo y exigencia de citar fuentes | `POLICY_AGENT_PROMPT` |

## Reutilizable para el proyecto

| Necesidad del proyecto | Ruta exacta y símbolo | Cómo reutilizarlo | Notas |
|---|---|---|---|
| Plantilla/PDF (capa 3): HTML → PDF con WeasyPrint | `stock_analysis_agent/tools.py` · `combine_reports` (bloque `CSS(string=...)` + `HTML(string=...).write_pdf(..., stylesheets=[css])`) | Solo idea / copiar ~10 líneas con atribución MIT | Patrón ya elegido en `plan.md`. Sustituir `markdown.markdown` por plantilla Jinja2; pasar `base_url` para imágenes Plotly; corregir que el PDF se genera desde `html_content` (sin `<head>`), no desde `html_full` |
| Plantilla/PDF: CSS de página A4 y tablas | `stock_analysis_agent/tools.py` · cadena CSS `@page { size: A4; margin: 2cm; }`, `table/th/td` | Copiar como punto de partida del CSS de impresión | Muy básico: sin cabeceras/pies, numeración, saltos de página ni marca corporativa |
| Composición del documento por secciones | `stock_analysis_agent/tools.py` · `combine_reports` (orden fijo `categories`, comentarios separadores) + `callbacks.py` · `save_agent_output` | Solo idea | Encaja con el editor híbrido: cada bloque como fragmento independiente ensamblado en orden fijo. En el proyecto, en BD (SQLite) en lugar de archivos `reports/*.md` |
| LLM (capa 4): orquestación multiagente paralela | `stock_analysis_agent/agent.py` · `ParallelAgent` + `LlmAgent` coordinador + `AgentTool` | Solo idea (no añadir `google-adk`) | Patrón "un agente por sección del informe, en paralelo, cada uno con `output_key`" aplicable a secciones 2, 4, 5, 8 de `estructura-informe.md` |
| LLM: abstracción de proveedor de modelo | `stock_analysis_agent/config.py` · `MODEL`, `GEMINI_LIST`, `OTHER_LIST`; `LiteLlm(model=MODEL)` en cada `agent.py` | Solo idea (config centralizada de modelo + validación al arrancar) | En el proyecto, mejor en `pydantic-settings`/`.env` que constante en código |
| LLM: diseño de prompts "solo con datos de la herramienta" | `sub_agents/fundamental_agent/prompt.py` · `FUNDAMENTAL_AGENT_PROMPT` ("Source Exclusivity", "do not compute ratios that are already provided", marcar huecos de datos) | Solo idea / adaptar texto con atribución | Muy alineado con el principio del proyecto de que la IA solo redacta sobre números deterministas (capa 2) |
| Sección 2 Conclusiones / 6 Análisis financiero (estructura narrativa) | `sub_agents/fundamental_agent/prompt.py` · bloques Rentabilidad, Crecimiento, Liquidez y solvencia, Eficiencia, Flujo de caja, Dividendos, Estructura de capital, Composición del beneficio, DuPont | Solo idea (checklist de qué comentar por dimensión: dato → tendencia → insight) | Cubre la redacción de la sección 6 y la parte A) de la sección 2; los datos los da la capa 2, no akshare |
| Sección 6: descomposición DuPont del ROE | `sub_agents/fundamental_agent/prompt.py` · bloque "DuPont 分析" | Solo idea; implementar como cálculo determinista en capa 2 | En el repo lo calcula el LLM; en el proyecto debe ser código |
| Sección 1 (portada, comportamiento en bolsa) y capa 2: indicadores sobre precios | `sub_agents/technical_agent/tools.py` · `calculate_technical_indicators` (volatilidad anualizada, MA5–MA250, máximos/mínimos 20/126/252, `volume_amplification`) | Copiar fórmulas con atribución MIT, reescritas para DataFrame de yfinance (`Close`, `Volume`) | Útil para "máximo/mínimo 12m", volatilidad y medias; columnas en chino de akshare; bucles `df.loc` lentos; RSI con media simple (no Wilder) |
| Sección 9 Gobierno / estructura accionarial (tabla de top-5 institucionales y variación QoQ) | `sub_agents/fund_agent/prompt.py` · sección "3. 机构持仓分析" | Solo idea de presentación | Datos en el proyecto: 13F/13D/G vía edgartools |
| Sección 8 Riesgos (calificación alto/medio/bajo y citas de fuente) | `sub_agents/policy_agent/prompt.py` · `POLICY_AGENT_PROMPT` | Solo idea (escala de impacto y exigencia de fuente) | El contenido regulatorio es de China; no trasladable |
| Utilidad de periodo trimestral | `sub_agents/fund_agent/tools.py` · `get_last_quarter` | Solo idea | Para versiones trimestrales el proyecto debe usar el periodo fiscal del 10-Q, no el calendario |
| Patrón de herramientas con salida serializable y errores como dict | `sub_agents/*/tools.py` (`df.astype(str)` → dict, `{"status":"error",...}`) | Solo idea | Convertir todo a `str` pierde tipos; en el proyecto usar Pydantic |
| Docs/onboarding: disclaimer de no asesoramiento | `README.md` · sección "Disclaimer" | Solo idea | El proyecto ya tiene texto legal propio |

## Patrones de organización y onboarding

- **Estructura por agente**: cada subagente vive en `sub_agents/<nombre>/` con tres archivos idénticos `agent.py` / `prompt.py` / `tools.py` + `__init__.py`. Es predecible y fácil de ampliar ("añadir una sección = copiar una carpeta"). **Trasladable** a `capa4_ia/<seccion>/{prompt,tools}.py`.
- **Prompts separados del código** en `prompt.py` como constantes `*_PROMPT`, con docstring de módulo. Trasladable (mejor aún en archivos `.md`/`.j2` versionados).
- **Convención `output_key = f"{agent_name}_output"`** y callbacks genéricos (`save_agent_output`) que usan esa convención: un único sitio para persistir resultados. Trasladable como idea.
- **Config central** del modelo en `config.py` con `assert` de validación al importar. Idea trasladable, implementación no (constante en código).
- **Reproducibilidad con `uv sync` + `uv.lock`**, documentada en el README. Trasladable.
- **Convención de nombres de salida** documentada (`equity_research_report_<empresa>_<ticker>_<YYYYMMDD>`). Útil para snapshots trimestrales.
- Carencias: sin tests, sin CI, sin CONTRIBUTING, sin `.env.example`, sin tipado consistente, sin logging (usa `print`), `pyproject.toml` es un volcado de `pip freeze` con dependencias de desarrollo mezcladas, `.gitignore` ignora `*.md` y `*test*` (bloquea añadir docs y tests), importaciones `from ...config import *`. Sin `CLAUDE.md`/`.claude/`.

## Lo que NO contiene

Verificado con `grep -riE 'yfinance|edgar|sec\.gov|plotly|streamlit|jinja|sqlite|pytest|test_'` y lectura completa:

- Ingesta SEC/EDGAR (10-K, XBRL, edgartools) y datos de EEUU: todo es akshare (China A-share).
- Precio vía yfinance o cualquier fuente de mercado de EEUU; índices/ETF sectoriales para comportamiento relativo.
- Cálculo determinista de métricas fundamentales (los ratios vienen precalculados de akshare), múltiplos, EV, DCF/WACC, proyecciones, comparables.
- Gráficos (Plotly ni ningún otro); no hay imágenes en el PDF.
- Plantilla Jinja2 (`jinja2` solo aparece como dependencia fijada, no se usa); el HTML es una f-string.
- UI Streamlit, editor de bloques, vista previa PDF.
- Versionado/snapshots, base de datos (SQLAlchemy figura en dependencias pero no se usa), aprobación/inmutabilidad.
- Resumen de Risk Factors / MD&A de un 10-K.
- Tests, fixtures, CI, CONTRIBUTING, `.env.example`, CLAUDE.md/.claude/skills.
- Soporte de idioma español/inglés en salida (prompts fuerzan chino; HTML `lang="zh"`).

## Riesgos

- **Licencia**: MIT, compatible; copiar fragmentos con aviso de copyright "Yaran Zhou". `akshare` es MIT pero los datos que extrae (Eastmoney, Sina) tienen términos propios; irrelevante si no se usa.
- **Dependencias**: ~190 pins exactos de mediados de 2025 (`google-adk==1.1.0`, `litellm==1.72.0`, `playwright`, `google-cloud-*`, jupyter). No adoptar el repo como dependencia; solo copiar ideas. `pandoc==2.4` (wrapper PyPI) y `py-mini-racer` (motor V8) son innecesarios y frágiles.
- **Windows**: el README advierte que solo se probó en Linux. WeasyPrint necesita GTK/Pango en Windows (ya anotado en `plan.md`). `pexpect` está fijado sin marcador de plataforma. Rutas relativas (`reports/`, `stock_analysis_agent/.env`) dependen del directorio de trabajo; `save_agent_output` falla si no existe `reports/`.
- **Python 3.13**: `uv.lock` resuelve para ≥3.13 y hay wheels `cp313-win_amd64` de numpy/pandas/shapely/greenlet; los pins antiguos pueden no tener wheels 3.13 en todos los casos (no verificado al no instalar).
- **Calidad / bugs detectados**:
  - `combine_reports` genera el PDF desde `html_content` (fragmento sin `<head>`/charset) en vez de `html_full`.
  - `calculate_technical_indicators` usa `indicators_list[-10:-1]`: devuelve 9 días y **excluye el último**, contradiciendo su docstring y el prompt ("20 días", "foco en el día más reciente"); docstring dice "seis meses" pero `start_date = "19910101"`.
  - `ParallelAgent` + escritura a archivos fijos `reports/<agente>_report.md`: ejecuciones concurrentes de distintos tickers se pisan.
  - `email_report` tiene credenciales SMTP de ejemplo en el código y devuelve `success` aunque falle; `schedule_email_report` es un bucle infinito bloqueante; ninguna de las dos está registrada como herramienta pese a que el README anuncia el envío por email.
  - El LLM calcula regresiones, p-valores, patrones chartistas y DuPont dentro del prompt: riesgo de cifras alucinadas, contrario al principio de cálculo determinista del proyecto.
  - Sin tests ni tipado; `df.astype(str)` elimina tipos numéricos.
