# Requisitos pendientes

Lo que hace falta definir o aportar para construir el SaaS. Cada punto incluye una **propuesta por defecto**: si no se indica otra cosa, se aplica esa.

## A. Plantilla del informe

| # | Necesito | Formato ideal | Propuesta por defecto |
|---|---|---|---|
| A1 | Ejemplo maquetado del informe | ✅ Estilo similar a los informes de Morningstar ([identidad-corporativa.md](identidad-corporativa.md)) | — |
| A2 | Página: tamaño, orientación, márgenes, columnas | Indicación o el propio ejemplo | A4 vertical, columna lateral de ladillos como en la referencia |
| A3 | Identidad: logo, colores, tipografías | ✅ Logo y nombre en `Plantilla/`; burdeos casi negro, negro y blanco. Burdeos `#2B0B02`; tipografía Montserrat (títulos) + Inter (texto); logos vectorizados | — |
| A4 | Cabecera y pie de cada página | Lista de elementos | Empresa, ticker, fecha, nº de página, aviso legal breve |
| A5 | Portada: bloques y su orden | Boceto o ejemplo | Igual que la página 1 de la referencia |
| A6 | Índice definitivo: secciones que se quedan, salen o se añaden, y su orden | Marcar sobre [estructura-informe.md](estructura-informe.md) | Índice completo actual |
| A7 | Por sección: tablas y gráficos exactos, años históricos y estimados | Lista por sección | 5 años históricos + 3 estimados, en USD Mn |
| A8 | Idioma del informe y formato numérico | — | Español, coma decimal, negativos entre paréntesis (piezas: edgartools `format_value` y `moneyfmt`; hay que combinarlas) |
| A9 | Texto legal / disclaimer propio | ✅ `plantillas/legal/descargo.md` | — |
| A10 | Autoría: analistas, contacto, entidad emisora | Datos | — |

## B. Editor (human-in-the-loop)

| # | Decisión | Propuesta por defecto |
|---|---|---|
| B1 | Bloques editables y cuáles precarga la IA | IA: riesgos, catalizadores (MD&A), descripción del negocio. Vacíos: tesis, conclusiones, industria |
| B2 | Formato de edición | Markdown con vista renderizada (nativo en Streamlit; el WYSIWYG requiere un componente de terceros) |
| B3 | Estimaciones que ajusta el analista | Crecimiento de ventas, margen EBITDA, capex/ventas, circulante, tasa fiscal, WACC (Rf, ERP, beta), g. Valores iniciales: media histórica de 3-5 años |
| B4 | ¿El informe emite recomendación o precio objetivo? | No (como la referencia: análisis sin recomendación). Implica requisitos legales si es «sí» |
| B5 | ¿Qué puede hacer el analista con el bloque fijo? | Solo ocultar o mostrar tablas y gráficos. Los ajustes (p. ej., EBITDA recurrente) se hacen como partidas explícitas con justificación, visibles en el informe |
| B6 | Usuarios y aprobación | Un analista que redacta y aprueba (localhost, sin login) |
| B7 | Vista previa | Botón «Generar vista previa» (WeasyPrint tarda unos segundos, no es en tiempo real) |
| B8 | Guardado | Autoguardado del borrador en cada cambio |
| B9 | Control de la IA | Botón para regenerar cada bloque; citas del 10-K visibles junto a cada viñeta |

## C. Sistema de versiones

| # | Decisión | Propuesta por defecto |
|---|---|---|
| C1 | ¿Cómo se crea una versión nueva? | El analista la crea manualmente. Al abrir la app se avisa si hay un 10-Q/10-K nuevo desde la última versión |
| C2 | Nomenclatura del periodo | Año fiscal de la empresa, p. ej. `AAPL · FY2026 Q2 · v1` (el ejercicio de Apple acaba en septiembre) |
| C3 | Estados | `borrador` → `aprobado` (inmutable). Para corregir uno aprobado se crea una revisión `v2` |
| C4 | Herencia | La versión nueva copia la tesis, los textos y las estimaciones de la anterior aprobada |
| C5 | Comparación entre versiones | Diferencias de texto de la tesis, tabla de estimaciones antes y después, y variación de métricas clave |
| C6 | Almacenamiento | SQLite + carpeta de PDFs y *snapshots* **fuera de OneDrive** (la sincronización puede corromper SQLite), con la ruta configurable en `.env`. También fuera: la caché de edgartools (`EDGAR_LOCAL_DATA_DIR`, por defecto `~/.edgar`) |
| C7 | Retención | Indefinida |
| C8 | Salida | Descarga del PDF (sin envío por email en esta fase) |

## D. Análisis del proyecto

### Hecho
- Estructura Python (`pyproject.toml`, `src/`, tests), configuración de `EDGAR_IDENTITY` y CLI mínima.
- Documentación: [plan.md](plan.md), [estructura-informe.md](estructura-informe.md), [repositorios-base.md](repositorios-base.md).
- Repositorio en GitHub (`origin`), pero **6 commits sin subir** (`git push` pendiente).

### Falta en el código (por fase del plan)
| Fase | Falta |
|---|---|
| 0 | CI (GitHub Actions: tests + ruff, en Ubuntu y Windows), `CONTRIBUTING`/guía para colaboradores, versión de Python fijada, `edgartools>=5.61.1,<6`. Patrones a reutilizar: CI de edgar_analytics, carriles fast/network del `conftest` de edgartools, `CLAUDE.md` y `.claude/` de edgartools |
| 1 | Módulo `ingesta/`: estados de 5 años, precio, texto del 10-K, vencimientos de deuda, *snapshot*. `datos.py` actual (solo último 10-K) se sustituye |
| 2 | Módulo `calculo/`: orquestar edgar_analytics + dividendos + P/FCF; tests contra el 10-K de AAPL |
| 3 | `visual/` + `plantillas/`: gráficos Plotly/kaleido, tablas, plantilla Jinja2, PDF WeasyPrint (**bloqueado por A**) |
| 4 | `ia/`: `LLMSettings`, prompts de riesgos/MD&A con citas |
| 5 | `almacenamiento/`: modelos SQLAlchemy, versiones (**bloqueado por C**) |
| 6 | `ui/`: Streamlit (**bloqueado por B**) |
| 7-8 | DCF, comparables, gobierno corporativo, proyecciones; usuarios y despliegue |
| — | Dependencias en `pyproject.toml`: edgar_analytics, yfinance, plotly, kaleido, jinja2, weasyprint, streamlit, sqlalchemy, cliente LLM |

### Riesgos técnicos detectados
- **Python 3.14** (el instalado por defecto) es muy reciente: WeasyPrint, kaleido, pyarrow o las librerías de LLM pueden no tener versión compatible. Propuesta: fijar **Python 3.13** (también instalado).
- **WeasyPrint en Windows** necesita GTK (instalación aparte, se documentará en el README).
- **LLM por defecto del repo base (Ollama + llama4):** llama4 es un modelo muy grande, inviable en un portátil normal. Hace falta elegir un modelo local pequeño o una API.
- **Sectores con contabilidad distinta** (bancos, aseguradoras, REITs): EBITDA, EV y deuda neta no aplican igual. La detección ya existe (edgartools `classify_business_category`, `Company.is_financial_institution()`; edgar_analytics `compute_all_scores(is_financial=...)`); solo hay que decidir si se excluyen o si tienen plantilla propia.
- **Emisores extranjeros (20-F)** y empresas sin XBRL completo: cobertura parcial.

## E. Lo que necesito de ti (además de A, B y C)

| # | Necesito | Para |
|---|---|---|
| E1 | Rellenar `EDGAR_IDENTITY` en `.env` (nombre + email) | Fase 1: sin esto no hay acceso a la SEC |
| E2 | Proveedor de LLM: API (Anthropic, OpenAI…) con su API key en `.env`, o modelo local con Ollama (y qué hardware tienes) | Fase 4 |
| E3 | Instalar GTK para WeasyPrint (te daré el comando) | Fase 3 |
| E4 | Alcance del universo: ¿todas las cotizadas de EEUU o una lista? ¿Incluir financieras y 20-F? | Fases 1-2 |
| E5 | Selección de comparables: manual por el analista o automática por sector (SIC; ya existe `get_companies_by_industry` en edgartools) | Fase 7 |
| E6 | Índices de referencia para el comportamiento en bolsa (propuesta: S&P 500 + ETF sectorial SPDR; el cálculo ya existe en financial-research-analyst-agent `performance_tracker`, falta el mapeo SIC → ETF) | Fase 3 |
| E7 | Autorización para hacer `git push` a GitHub y confirmar si el repo es público o privado | Publicación |
| E8 | Clave de Alpha Vantage (opcional, solo como respaldo de yfinance) | Fase 1 |
