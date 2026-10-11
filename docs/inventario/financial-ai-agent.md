# financial-ai-agent

- **Repo / alcance / licencia**: URL original desconocida (copia local `scratchpad/repos/financial-ai-agent-main`; las rutas del `.coverage` apuntan a `/Users/elena/Code/lenaar/financial-ai-agent/`). Alcance: todo el repo. **Sin licencia**: no hay `LICENSE` (solo aparece la palabra en `.dockerignore`), así que todos los derechos están reservados. **Solo se pueden tomar ideas; no se copia código.**
- **Cobertura**: 25 archivos en total. **Leídos completos: 21** (los 9 `.py` raíz, los 2 tests, `README.md`, `docs/testing_best_practices.md`, `requirements.txt`, `pytest.ini`, `env.example`, `.gitignore`, `.dockerignore`, `Dockerfile`, `.vscode/launch.json.example` y `data/financial_data.csv`, que son 7 filas). **Solo firmas: 0.** **Por muestreo: 4**: las 3 capturas `images/*.jpg` (visualizadas) y `.coverage`, una BD SQLite de coverage.py 7.9.1 de la que se sacaron el esquema y las rutas.

## Qué contiene

Es un prototipo pequeño (unas 200 líneas de Python, todo en la raíz y sin paquete) que monta un **agente LangGraph + LangChain/OpenAI (`gpt-4.1-nano`, temperatura 0) con una UI Streamlit**. Lee un CSV de un año por fila, pide al LLM que lo «analice», busca a los competidores con Tavily, compara, hace un bucle de *feedback* y redacta un informe en texto libre. **Ninguna cifra se calcula de forma determinista: todo lo hace el LLM.**

| Ruta | Qué hace | API/elementos clave (nombres exactos) |
|---|---|---|
| `main.py` | App Streamlit: formulario → `graph.stream` → vuelca cada evento con `st.write` y muestra el informe final | `main()`; `st.set_page_config(page_title="Financial Analysis Agent", layout="centered")`; widgets `st.text_input` (task, competitors), `st.file_uploader(type=["csv"])`, `st.number_input` (max_revisions 1-10), `st.button("Start")`; `initial_state = {task, competitors_names, csv_data, max_revisions}`; `with get_memory_saver() as checkpointer`; `st.success`/`st.warning`/`st.error`. Duplica la instancia de `ChatOpenAI` de `model.py` |
| `agent.py` | Construye el grafo LangGraph | `should_continue_node(state)` (si `revisions > max_revisions` devuelve `END`, si no `"collect_feedback"`); `build_graph_agent(checkpointer)`: `StateGraph(State)`, 7 nodos, `add_conditional_edges("compare_performance", …)` **y además** `add_edge("compare_performance","write_report")`; `set_entry_point("gather_financial_data")`; `compile(checkpointer=…)` |
| `nodes.py` | Los 7 nodos del grafo | `gather_financial_data_node` (CSV → LLM → `financial_data`, muta `state.update`); `analyze_financial_data_node` (→ `financial_analysis`); `analyze_competitors_node` (genera las consultas con `model.with_structured_output(Queries)` y las lanza en paralelo con `ThreadPoolExecutor(max_workers=len(competitors_names))` → `full_content`); `compare_performance_node` (→ `performance_comparison`, `revisions+1`); `collect_feedback_node` (→ `feedback`); `research_feedback_node` (nuevas búsquedas en Tavily → `full_content`); `write_report_node` (→ `report`) |
| `state.py` | Estado del grafo y esquema de la salida estructurada | `class State(TypedDict)`: `competitors_names, csv_data, feedback, financial_analysis, financial_data, full_content, max_revisions, performance_comparison, report, revisions, task`; `class Queries(BaseModel): queries: List[str]` |
| `prompts.py` | 7 prompts de sistema como constantes de módulo | `GATHER_FINANCIAL_PROMPT`, `ANALYZE_DATA_PROMPT` («Base all conclusions strictly on the provided data»), `ANALYZE_COMPETITORS_PROMPT` (3 consultas con ejemplo bueno/malo), `COMPARE_PERFORMANCE_PROMPT`, `FEEDBACK_PROMPT` (revisor sénior), `WRITE_REPORT_PROMPT` (estructura: Executive summary / Detailed analysis / Competitive positioning / Strategic recommendations / Supporting data), `RESEARCH_FEEDBACK_PROMPT` |
| `model.py` | Cliente LLM global, creado al importar | `model = ChatOpenAI(model="gpt-4.1-nano", temperature=0.0)`; `generate_model_response(content, prompt) -> str` (`SystemMessage` + `HumanMessage`) |
| `search_tool.py` | Cliente Tavily global con caché | `TavilyResponse` (TypedDict); `tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))`; `@functools.lru_cache cached_search(query)` (`max_results=2`); crea un `TTLCache(maxsize=100, ttl=3600)` que no se usa e importa `cachetools`, que no está en `requirements.txt` |
| `memory.py` | Checkpointer y configuración del hilo | `get_memory_saver()` → `SqliteSaver.from_conn_string(":memory:")`; `get_thread_config()` → `thread_id: 1` fijo |
| `csv_data.py` | CSV en texto → `pd.read_csv(StringIO)` → `to_string` → frase para el LLM | `get_csv_data(state) -> str` (imports sin usar: `SystemMessage`, `model`) |
| `README.md` | Descripción, estructura, instalación, formato del CSV, capturas, tests, Docker y diagrama mermaid del flujo | El diagrama **no coincide con `agent.py`** (pone la decisión después de `Collect Feedback` y con las ramas invertidas); pide copiar `.env.example`, pero el archivo se llama `env.example` |
| `docs/testing_best_practices.md` | Guía de 10 reglas para tests unitarios | Comportamiento antes que implementación; mock donde se importa; `test_<scenario>_<expected_outcome>`; Arrange-Act-Assert; casos de error; preservar el estado; casos límite; aislamiento; tests de integración |
| `tests/test_nodes.py` | 7 tests con `unittest.mock.patch` en el punto de importación | `TestGatherFinancialDataNode` (5: CSV OK, CSV vacío, conserva el estado, error de CSV, error del modelo); `TestAnalyzeFinancialDataNode` (2: error del modelo, `KeyError` sin `financial_data`). Patrón `@patch('nodes.generate_model_response')` |
| `tests/test_state.py` | 5 tests triviales sobre dicts (un `TypedDict` no valida en tiempo de ejecución) | `TestState.test_state_creation_with_required_fields`, `…optional_fields`, `…field_types`, `…field_access`, `…field_update` |
| `pytest.ini` | Configuración de pytest con cobertura | `testpaths = tests`; `addopts = -v --cov=. --cov-report=term-missing` |
| `requirements.txt` | 13 dependencias sin fijar o con mínimos muy bajos | `langgraph>=0.0.19`, `langchain_community`, `langchain_openai`, `langchain-tavily`, `langgraph-checkpoint-sqlite`, `openai>=1.0.0`, `pandas>=2.0.0`, `python-dotenv`, `pytest`, `pytest-cov`, `pytest-mock`, `streamlit>=1.45.0`, `tavily-python` |
| `Dockerfile` | Imagen `python:3.11-slim` con usuario no root, *healthcheck* y Streamlit en el puerto 8501 | `useradd -m -u 1000 appuser`; `HEALTHCHECK … curl -f http://localhost:8501/_stcore/health`; `CMD ["streamlit","run","main.py","--server.port=8501","--server.address=0.0.0.0"]` |
| `.dockerignore` | Excluye git, artefactos Python, venv, `.env`, IDE, logs, `data/`, `images/`, `tests/`, `*.md` | — |
| `.gitignore` | `.env`, `__pycache__/`, `*.pyc`, `.DS_Store`, `.vscode/launch.json` | Versiona el ejemplo `launch.json.example` e ignora la copia local |
| `env.example` | Plantilla de secretos | `OPENAI_API_KEY`, `TAVILY_API_KEY` |
| `.vscode/launch.json.example` | Configuración de depuración de VS Code | `"type": "debugpy"`, `"program": "${file}"`, `justMyCode` |
| `data/` (1 CSV) | Datos de ejemplo inventados (USD absolutos, 2019-2024) | Columnas `year,revenue,cost_of_goods_sold,operating_expenses,net_income` |
| `images/` (3 JPG, 78-176 KB, ~800×750) | Capturas de la UI (tema oscuro): formulario, procesamiento (JSON crudo de cada evento) e informe final (`st.success` + JSON con `"report"`) | El informe de ejemplo compara con «Company A»/«Company B», con CAGR inventados, aunque se pidieron Apple y Google (ver Riesgos) |
| `.coverage` | Artefacto de coverage.py 7.9.1 subido por error (SQLite) | Tablas `coverage_schema, meta, file, context, line_bits, arc, tracer`; rutas absolutas de la máquina de la autora |

## Reutilizable para el proyecto

Al no tener licencia, todo es **solo idea**: no se copia código ni el texto de los prompts.

| Necesidad del proyecto | Ruta exacta y símbolo | Cómo reutilizarlo | Notas |
|---|---|---|---|
| UI Streamlit: estados de progreso (plan › «Flujo al introducir un ticker») | `main.py` `main()` (bucle `for event in graph.stream(...)`) | Solo idea | Aprovechar que cada etapa emite un evento y mostrarlo como estado (`st.status`/`st.progress`: «Extrayendo datos de la SEC…»). **No** volcar dicts crudos con `st.write(event)` como hace este repo |
| Capa 4 / LLM: salida estructurada | `nodes.py` `analyze_competitors_node` + `state.py` `Queries(BaseModel)` + `model.with_structured_output(...)` | Solo idea | Mismo mecanismo para las viñetas de riesgos/MD&A con un esquema Pydantic `{punto, cita_10k, item}` verificable (principio de trazabilidad). En el proyecto, con `LLMSettings` multiproveedor |
| Capa 4 / LLM: prompts separados del código | `prompts.py` (constantes `*_PROMPT`) | Solo idea | Llevar los prompts a un módulo o a archivos en `ia/prompts/` para que se puedan revisar sin tocar la lógica. La regla «Base all conclusions strictly on the provided data» es buena práctica general |
| Capa 4 / LLM: bucle crítico-revisor | `agent.py` `should_continue_node` + `nodes.py` `collect_feedback_node` / `research_feedback_node` (límite `max_revisions`) | Solo idea, opcional | Útil como verificación automática: un segundo paso comprueba que cada viñeta tiene cita literal en el 10-K antes de pasarla al analista. El tope de revisiones evita bucles infinitos |
| Sección 2 (Conclusiones) / Sección 1 (titulares de la tesis) | `prompts.py` `WRITE_REPORT_PROMPT` | Solo idea | Estructura genérica de informe (resumen ejecutivo → análisis → posición competitiva → recomendaciones → datos). Para nosotros, sin recomendación (B4) y sobre cifras de la capa 2, nunca calculadas por el LLM |
| Sección 5 (Industria y mercado) / hueco «datos de mercado sectoriales» | `search_tool.py` `cached_search` (Tavily + `lru_cache`); `prompts.py` `ANALYZE_COMPETITORS_PROMPT` (consultas «buenas» vs «malas») | Solo idea | Única pieza que toca el hueco de datos de mercado externos (tamaño, CAGR del sector): búsqueda web con caché. Si se usa, cada dato debe guardar URL y fecha en el *snapshot* y mostrarse como externo |
| Sección A5 (Comparables) | `nodes.py` `analyze_competitors_node` (búsqueda web por competidor en paralelo) | **No reutilizar** | Sacar las cifras de los peers de la web mediante un LLM no es trazable. Los comparables deben salir de XBRL (edgartools/edgar_analytics `analyze(peers=...)`) |
| CI/tests: patrón de mocks | `tests/test_nodes.py` (`@patch('nodes.generate_model_response')`, AAA, casos de error) | Solo idea | Para la capa 4: mockear el cliente LLM donde se importa y probar los casos de error y de entrada vacía |
| Docs/onboarding: guía de testing | `docs/testing_best_practices.md` | Solo idea (redactar la nuestra) | Base de una sección «Cómo escribir tests» en `CONTRIBUTING`, con nomenclatura `test_<escenario>_<resultado>` |
| Docs/onboarding: configuración del IDE | `.vscode/launch.json.example` + `.gitignore` (`.vscode/launch.json`) | Solo idea | Versionar ejemplos (`*.example`) e ignorar las copias locales; lo mismo que `.env.example` |
| Fase 8 (despliegue) | `Dockerfile` (no root, `HEALTHCHECK /_stcore/health`, `--server.address=0.0.0.0`) | Solo idea | Patrón estándar de Streamlit en un contenedor. WeasyPrint añadiría paquetes del sistema (pango/cairo) a la imagen |
| Datos de prueba | `data/financial_data.csv` | Solo idea | Un CSV mínimo como *fixture*. Para nosotros, *snapshots* reales de AAPL |

Secciones de `estructura-informe.md` que cubre: **ninguna con datos reales**. Solo aporta ideas de prompt y flujo para las secciones 1 (titulares), 2 (conclusiones) y 5 (industria, mediante búsqueda web), y un contraejemplo para A5. No aporta nada a las secciones 3, 4, 6, 7, 8, 9, A1-A4 ni L.

## Patrones de organización y onboarding

| Aspecto | Qué hace | ¿Trasladable? |
|---|---|---|
| Estructura | Un archivo por responsabilidad (`state`, `nodes`, `agent`, `prompts`, `model`, `memory`, `search_tool`, `main`) y un árbol comentado en el README | Sí, la idea de separar responsabilidades. Nuestro plan ya lo hace en `src/informes_warrants/` (capas + `ui/`). Lo que **no** se traslada es tenerlo todo en la raíz sin paquete ni `pyproject.toml` |
| README | Secciones ordenadas: About → Features → Structure → Installation → Usage → formato de entrada (CSV de ejemplo) → capturas por etapa → Testing → Docker → diagrama mermaid | Sí: documentar el **formato de entrada** con un ejemplo y poner **capturas por etapa** de la UI ayuda mucho a quien llega nuevo. Hay que evitar que el diagrama se desincronice del código, como pasa aquí |
| Configuración | `env.example` con las claves y `load_dotenv()` | Sí, ya lo usamos (`EDGAR_IDENTITY`). Mejor centralizado en un objeto de configuración que con `os.getenv` disperso |
| Tests | `pytest.ini` con cobertura por defecto y una guía de buenas prácticas en `docs/` | Sí: la guía en `docs/` y `--cov` en `addopts`. No el `.coverage` versionado (va en `.gitignore`) |
| IDE | `launch.json.example` versionado | Sí |
| CI, linters, `pyproject`, CONTRIBUTING, CLAUDE.md/.claude | No existen | — |

## Lo que NO contiene

Verificado con `grep -rliE "jinja|weasyprint|plotly|sqlalchemy|edgar|sec\.gov|yfinance|xbrl|10-K|pdf|github/workflows|CLAUDE|anthropic|ruff|pyproject|CONTRIBUTING|snapshot|version"` (sin coincidencias de código; solo `"version"` en `launch.json.example`) y con un listado completo de archivos:

- Ingesta de la SEC/EDGAR/XBRL, texto del 10-K, Items 1/1A/7: no hay nada. La entrada es un CSV que sube el usuario.
- Precios y datos de mercado (yfinance, Alpha Vantage), market cap, EV.
- Cálculo determinista de métricas o valoración (ratios, CAGR, DCF, múltiplos): todo lo «calcula» el LLM.
- Gráficos (Plotly/kaleido), tablas HTML, plantilla Jinja2, exportación HTML/PDF (WeasyPrint/reportlab).
- Editor híbrido (bloque fijo/editable), vista previa del PDF.
- Versiones, *snapshots* o persistencia real: `SqliteSaver(":memory:")` se pierde en cada ejecución. Tampoco hay SQLAlchemy.
- Configuración LLM multiproveedor ni Anthropic: solo OpenAI, con el modelo fijado en el código.
- Citas o trazabilidad de las fuentes, RAG.
- CI (`.github/workflows`), linters (ruff), `pyproject.toml`, `CONTRIBUTING`, `LICENSE`, `CLAUDE.md`/`.claude`/skills.

## Riesgos

- **Licencia**: sin licencia, así que todos los derechos están reservados. Prohibido copiar código o prompts literales; solo ideas, reescritas desde cero.
- **Calidad y fallos lógicos** (vistos al leer el código, sin ejecutarlo):
  - `compare_performance_node` **no usa `full_content`**: la investigación de los competidores nunca llega al LLM, que **inventa** sus cifras. La captura `frontend_final_report.jpg` muestra «Company A/Company B» con CAGR del 18 % y del 27 % aunque se pidieron Apple y Google. Es un contraejemplo directo de nuestro principio de trazabilidad.
  - En `agent.py`, `compare_performance` tiene a la vez aristas condicionales y una arista fija a `write_report`, así que el informe se redacta en cada vuelta del bucle. El README describe otro flujo.
  - `analyze_competitors_node` falla (`ValueError`) con una lista de competidores vacía (`max_workers=0`). Los nombres no se limpian de espacios (`split(",")`).
  - `main.py`: `final_event` queda sin definir si no hay eventos. `thread_id` es fijo (=1) para todas las ejecuciones.
  - Los clientes `ChatOpenAI` y `TavilyClient` se crean **al importar**, así que los tests de `nodes` probablemente necesitan claves reales o fallan al importar. `cachetools` no está declarado. Se usa `print` en vez de `logging`. `.coverage` está versionado.
- **Dependencias**: todas sin fijar, con mínimos de 2024 (`langgraph>=0.0.19`); la API de LangGraph ha cambiado mucho desde entonces y es frágil. `pydantic` y `langchain_core` llegan solo como dependencias transitivas. LangGraph/LangChain es una dependencia pesada que no necesitamos para un flujo determinista y lineal.
- **Windows / Python 3.13**: todo es Python puro (pandas, streamlit, langgraph, openai, tavily) y no se prevén bloqueos. El Dockerfile usa 3.11. Ninguna dependencia requiere GTK.
- **Encaje**: el enfoque (el LLM calcula y redacta las cifras) es **opuesto** al principio de determinismo de las capas 1-3. Su valor para el proyecto es marginal: ideas de UI con estados, salida estructurada, bucle de revisión y patrones de tests.
