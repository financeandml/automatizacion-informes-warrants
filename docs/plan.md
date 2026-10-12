# Plan de desarrollo

SaaS que, a partir de un ticker de EEUU, genera un informe borrador con datos oficiales de la SEC. El analista lo revisa, completa la tesis y lo versiona cada trimestre.

Contenido del informe: [estructura-informe.md](estructura-informe.md). Código reutilizable: [repositorios-base.md](repositorios-base.md).

## Arquitectura en 4 capas

```
ticker ─► [1 Ingesta] ─► [2 Cálculo] ─► [3 Visual] ─► informe borrador ─► [4 IA + analista] ─► versión aprobada
            SEC + precio   pandas/numpy   gráficos/tablas   HTML/PDF          10-K texto + editor     archivo
```

## Principios del plan maestro

1. **Determinismo:** las capas 1-3 no usan IA. La IA solo trabaja en la capa 4 y siempre la revisa un humano.
2. **Una sola plantilla HTML** para la vista previa y para el PDF: lo que ve el analista es exactamente lo que se descarga.
3. **Trazabilidad:** cada cifra del bloque fijo enlaza a su fuente (concepto XBRL, filing y fecha). Cada viñeta de la IA lleva la cita literal del 10-K.
4. **Versiones inmutables:** una versión aprobada no se modifica y guarda el *snapshot* de los datos con los que se generó.
5. **Reutilizar antes que construir:** antes de cualquier tarea se consulta el inventario completo de `repositorios-github/` ([inventario/README.md](inventario/README.md)) y se razona qué se reutiliza.

Cada capa vive en su carpeta de `src/informes_warrants/` (índice de módulos en el docstring de cada `__init__.py`). Qué se reutilizó de cada repo base y por qué está en el docstring de cada módulo y en el [inventario](inventario/README.md).

### Capa 1 — Ingesta (`ingesta/`)

| Necesidad | Cómo se resuelve | Estado |
|---|---|---|
| Estados financieros (5 ejercicios + LTM) | edgartools `Company.get_facts()` (companyfacts) leído por el normalizador SEC (`calculo/normalizador.py`), con el XBRL del último 10-K como contraste | ✅ |
| LTM y ajuste por *splits* | edgartools `ttm/` (`TTMCalculator`) dentro del normalizador (`FuenteLTM`). **No** usar `compute_ttm` de edgar_analytics | ✅ |
| Precio, histórico, comportamiento relativo, tipo libre de riesgo | yfinance (`ingesta/mercado.py`); Rf del CSV público de FRED (DGS10) | ✅ |
| Acciones en circulación | Portada (dei) del último filing, con control de antigüedad (`acciones_en_circulacion`) | ✅ |
| Texto del 10-K (Items 1 y 1A) | edgartools `TenK` (`ingesta/riesgos.py`) | ✅ (MD&A: pendiente de conectar) |
| Gobierno | edgartools `ProxyStatement` y `extract_auditor_info` (`ingesta/gobierno.py`) | ✅ |
| Comparables | SEC: CIK por SIC (`browse-edgar`, Atom) + tickers oficiales + tamaño por API *frames* (`ingesta/comparables.py`) | ✅ (propuesta orientativa; el analista introduce la lista) |
| Vencimientos de deuda | Concepto **bruto** `LongTermDebtMaturitiesRepaymentsOfPrincipal…` (verificado en AAPL) | Pendiente |
| Segmentos y geografía | edgartools `FactQuery.by_dimension` con validación propia ([plan](rigor-del-contenido.md#tarea-pendiente-segmentos-y-geografía-plan)) | Pendiente |
| *Snapshot* por versión | JSON propio de los datos usados (sin pickle ni el `CacheLayer` de edgar_analytics), fuera de OneDrive | Pendiente |

### Capa 2 — Motor de cálculo (`calculo/`)

Toda cifra sale de aquí (regla 9). Las fórmulas de edgar_analytics y FinRobot se **reimplementaron** sobre las partidas del normalizador, con atribución, en lugar de usarlos como dependencia: sus definiciones difieren (p. ej. el EBITDA de edgar_analytics incluye resultados no operativos) y trabajan sobre DataFrames por etiqueta.

| Bloque | Módulo | Origen |
|---|---|---|
| Normalizador SEC (anual y LTM, partidas derivadas trazables) | `normalizador.py` | Propio; jerarquía de ingresos de edgartools `RevenueDeduplicator` |
| Márgenes, FCF (y tras SBC), DFN, ROE, ROIC, ROCE, múltiplos | `metricas.py` | Propio (edgar_analytics como contraste) |
| Semáforo de calidad | `calidad.py` | stock-screener `DataQualityChecker`, edgartools `validate_balance_sheet` (ideas) |
| DCF por escenarios, sensibilidades, DCF inverso, beta | `dcf.py` | financial-research-analyst-agent `dcf_model` (patrón) + FinRobot `dcf.py` (DCF inverso, flujo terminal) |
| Proyección hasta el BPA | `proyeccion.py` | Propio (no existía) |
| Comparables (medianas y valor implícito) | `valoracion_relativa.py` | FinRobot `multiples.py` (reglas de la mediana) |
| Analítica de márgenes y uso del capital | `analitica.py` | Propio (no existía) |
| Altman, Beneish, Piotroski | `puntuaciones.py` | edgar_analytics `scores.py` (fórmulas y umbrales) |
| Notas de los ratios y metodología | `notas.py`, `definiciones.py` | Propio |
| Métricas sectoriales | `sectoriales.py` | Propio sobre `informe/perfiles.py` |

Tests *golden* con el 10-K FY2023 de AAPL (`tests/fixtures/aapl_10k_2023`).

### Capa 3 — Presentación (`visual/` y `plantillas/`)

| Necesidad | Cómo se resuelve | Estado |
|---|---|---|
| Gráficos | matplotlib en SVG con los tres colores de la marca (`visual/graficos.py`) | ✅ (cascada, vencimientos y barras apiladas de segmentos: pendientes) |
| Plantilla A4 (cabecera, pie, numeración) | Jinja2 + CSS propio (`plantillas/informe/`); no existía en ningún repo | ✅ |
| Tablas y formato español (coma decimal, negativos entre paréntesis) | Filtros `num`, `pct` y `var` (`informe/plantillas.py`) | ✅ |
| PDF | WeasyPrint (patrón de equity-research-agent `combine_reports`, corregido) | ✅ |

### Capa 4 — IA cualitativa y panel del analista

| Necesidad | Reutilizar | Construir |
|---|---|---|
| Configuración del LLM | financial-research-analyst-agent `src/config.py`: copiar **solo** `LLMSettings` (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_TEMPERATURE` = 0.1, `LLM_MAX_TOKENS` = 4096); el resto de sub-settings usa `Field(env=...)`, que Pydantic v2 ignora | Reducirlo a lo que usa este proyecto |
| Resumen de MD&A (catalizadores) y riesgos (Item 1A) | Texto de edgartools; patrón `key_risk`/`key_catalyst` de financial-research-analyst-agent `llm_insight_engine`. Las `edgar/ai/skills` son skills para agentes de desarrollo, no prompts del producto | Prompts propios: viñeta + cita literal del 10-K |
| Verificar que cada cita existe en el 10-K | mtcb `ExactMatchValidator`/`FuzzyMatchValidator` (Apache-2.0); edgartools `DocumentSearch.ranked_search` (BM25) | — |
| RAG, si el texto excede el contexto | edgartools `ChunkExtractor` + BM25; mtcb solo para elegir el *chunking*. No usar financial-research-analyst-agent `src/rag` (trunca a 200.000 caracteres y su filtro falla en silencio) | Solo si hace falta |
| Backend API | financial-research-analyst-agent `src/api` solo como patrón (19 rutas no se registran y varias devuelven datos fijos) | Endpoints propios si se necesitan |
| UI | **Streamlit en localhost**; financial-research-analyst-agent `frontend/` (`components/plotly_charts.py`, `utils/theme.py`, `frontend/.streamlit/config.toml`) como base | Dashboard + editor híbrido + vista previa (no existe en ningún repo) |

## Flujo al introducir un ticker

1. El analista escribe `AAPL` en el dashboard.
2. Estado «Extrayendo datos de la SEC…» → capa 1: último 10-K/10-Q, estados financieros y precio. Se guarda el *snapshot*.
3. Estado «Calculando métricas…» → capa 2.
4. Estado «Generando gráficos y tablas…» → capa 3.
5. Estado «Resumiendo el 10-K…» → capa 4 (IA): riesgos y catalizadores.
6. Estado «Listo para revisión» → editor híbrido.

## Editor híbrido y versiones

Definidos en detalle en [editor-y-versiones.md](editor-y-versiones.md). En resumen:

- **Bloques:** 19 AUTO (código), 4 PLANTILLA (texto con datos), 2 IA (riesgos y catalizadores, con cita literal) y 7 ANALISTA (marcados con `[[ANALISTA: …]]`; bloquean la emisión).
- **Izquierda, bloque fijo:** solo lectura, con la fuente de cada cifra. El analista solo puede ajustar los comparables y marcar partidas no recurrentes, siempre con motivo.
- **Derecha, bloque editable:** Markdown con las plantillas ya rellenas, las estimaciones (recalculan proyección y DCF) y la recomendación, que el SaaS propone y el analista confirma.
- **Vista previa en tiempo real:** HTML en cada cambio y PDF recompilado en segundo plano.
- **Emisión:** apartado «Confirmar emisión del informe»; la versión pasa a `emitida` y queda inmutable.
- **Versiones:** se detectan automáticamente con cada 10-Q/10-K (sin enmiendas) y el analista las confirma. Se nombran por año fiscal (`AAPL · FY2026 Q3 · v1`), heredan solo lo que aportó el analista y se guardan en SQLite fuera de OneDrive.

## Estructura del código

```
src/informes_warrants/
  cli.py          # punto de entrada: informes-warrants -h
  config.py       # identidad SEC y carpeta de datos (fuera de OneDrive)
  ingesta/        # capa 1: SEC y mercado
  calculo/        # capa 2: motor matemático (toda cifra sale de aquí)
  informe/        # bloques, estimaciones, composición y render del informe
  visual/         # capa 3: gráficos SVG y PDF
  plantillas/     # plantilla HTML/CSS, bloques Markdown, marca, fuentes (OFL) y texto legal
  ia/             # capa 4: uso mínimo del modelo de lenguaje
  almacenamiento/ # versiones: estados, herencia, comparación, SQLite, detección
  ui/             # Streamlit en localhost (pendiente, fase 7)
```

La lógica (capas 1-4) no depende de la UI, así que la interfaz se puede cambiar sin tocar el núcleo.

## Fases

| Fase | Entregable | Hito verificable |
|---|---|---|
| 0. Base | Estructura, configuración, tests, CI (GitHub Actions en Ubuntu **y Windows**: los repos base solo usan Ubuntu), `edgartools>=5.61.1,<6` (la 6.0 cambia la API) | ✅ Hecho: Python 3.13, dependencias fijadas, ruff, CI en Ubuntu y Windows, CONTRIBUTING |
| 1. Ingesta | ✅ 5 ejercicios + LTM normalizados (companyfacts) contrastados con el XBRL del 10-K, cotización, histórico, comportamiento vs SPY/ETF, Rf, comparables, gobierno, riesgos y texto del 10-K. Falta: *snapshot* por versión, vencimientos de deuda y segmentos | `informes-warrants informe AAPL` |
| 2. Cálculo | ✅ Normalizador SEC, métricas propias, DCF, beta y semáforo, con tests *golden* del 10-K FY2023 de AAPL | Las cifras de AAPL cuadran al dólar con el 10-K |
| 3. Visual | ✅ Gráficos SVG, tablas, plantilla HTML A4 y PDF de 10 páginas ([ejemplo](ejemplos/AAPL_FY2025_borrador.pdf)). Falta el PDF de las plantillas sectoriales (banca, seguros, REIT, BDC) | **Primer informe borrador PDF completo por CLI (MVP)** ✅ |
| 4. IA | ✅ Proveedor, selección con cita literal y los 2 bloques de IA ([ia.md](ia.md)); los riesgos ya están en el informe; falta conectar los catalizadores del MD&A | `informes-warrants riesgos AAPL` |
| 5. Versiones | ✅ Estados, herencia, comparación, SQLite inmutable y detección; falta el snapshot y el PDF por versión (dependen de las fases 1-3) | `informes-warrants versiones detectar AAPL` |
| 6. Rigor del contenido | Las 8 carencias y los apartados «parciales» del índice ([rigor-del-contenido.md](rigor-del-contenido.md)). ✅ Carencias 1-3 y 5-8 (LTM, escenarios, DCF inverso, BPA, comparables, SBC, gobierno, puntuaciones, cambios del Item 1A, notas y metodología). Pendiente: segmentos (plan cerrado), los apartados parciales del índice y el motor de valoración con los modelos que aportará el usuario ([requisitos F1](requisitos-pendientes.md#f-aportaciones-futuras-del-usuario-tareas-pendientes)) | PDF intermedio revisado en cada paso |
| 7. UI | Streamlit: dashboard con estados, editor híbrido, vista previa (sobre los bloques ya cerrados en la fase 6) | Flujo completo en localhost |
| 8. SaaS | Usuarios, autenticación, multiempresa, despliegue, avisos legales | Acceso externo |

## Decisiones tomadas

| Tema | Decisión | Origen |
|---|---|---|
| UI | Streamlit en localhost | Usuario |
| PDF | Plantilla HTML → WeasyPrint (GTK con MSYS2 en Windows) | equity-research-agent |
| LLM | llama4 en OpenRouter (si hay key) > `gpt-oss-120b` en Groq (activo) > Ollama `llama3.2:3b` local; mismo código para todos los proveedores | [ia.md](ia.md) |
| Uso de la IA | Mínimo: 2 bloques, solo elige y resume fragmentos literales | Usuario |
| Editor | Markdown, vista previa en tiempo real, emisión con confirmación del analista | Usuario |
| Recomendación | Sí: el SaaS la propone por potencial y el analista la confirma; se muestra siempre el precio objetivo calculado y el analista puede fijar el suyo | Usuario |
| Comparables | La propuesta automática por SIC es orientativa y no entra en el precio objetivo; la valoración por múltiplos exige la lista del analista; sin ella, aviso antes de emitir (no bloquea ni sale en el informe). Motor de valoración completo: con los modelos que aportará el usuario | Usuario (2026-10-12) |
| Contenido | Enfoque determinista. Primero los apartados «parciales» del índice; lo «hecho» se mantiene y sus cambios van al final; lo «ejecutable», lo «externo» y lo del analista se aparcan | Usuario (2026-10-12) |
| Versiones | Detección automática + confirmación; año fiscal; SQLite fuera de OneDrive | Usuario |
| Alcance | Todas las empresas de EEUU: plantilla general + perfiles sectoriales validados (banca, seguros, REIT, BDC/fondos cerrados) y emisores extranjeros en USD; el resto, «plantilla pendiente de validar» | Usuario + [editor-y-versiones.md](editor-y-versiones.md#alcance) |
