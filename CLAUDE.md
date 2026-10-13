# Guía del proyecto (personas y agentes de IA)

SaaS que genera informes de análisis (estilo *equity research*) sobre empresas cotizadas en EEUU a partir de datos oficiales de la SEC. El analista los revisa, completa la tesis y los versiona cada trimestre.

**Objetivos.** Medio: que cualquier persona nueva entienda, use y modifique el proyecto sin ayuda. Final: el SaaS de automatización de informes.

## Reglas obligatorias

1. **Reutilizar antes que construir.** Antes de cualquier tarea, consulta [docs/inventario/README.md](docs/inventario/README.md) (análisis del 100 % de los repos base) y deja escrito qué se reutiliza y por qué. Si cambia un zip de `repositorios-github/`, actualiza su ficha.
2. **No saltar pasos ni dejar nada a medias:** cada tarea termina con código, tests, docs y commit, o con una nota explícita de lo que queda.
3. **No borrar nada** que pueda perjudicar el objetivo final; ante la duda, preguntar.
4. **Ahorro de tokens:** leer solo lo necesario (inventario y docs primero), sin repetir información entre documentos.
5. **Repo publicable en todo momento:** sin secretos (`.env` ignorado), sin código de terceros versionado (`repositorios-github/` ignorado), docs al día.
6. **Licencias:** MIT/Apache se puede copiar con atribución (p. ej. FinRobot, Apache-2.0); sec-edgar-toolkit (AGPL-3.0), automated-market-report y financial-ai-agent (sin licencia) solo como referencia; vectorbt (Commons Clause: prohíbe vender) solo para uso interno hasta el lanzamiento, y se sustituye antes de comercializar el SaaS (decisión del usuario, 2026-10-12).
7. **Determinismo e IA mínima:** las cifras salen de código; lo que no, de plantilla; lo que no, lo marca el SaaS para el analista (`[[ANALISTA: …]]`). La IA solo elige y resume fragmentos literales del 10-K (2 bloques) y siempre la revisa un humano.
8. **Datos fuera de OneDrive:** base de datos, cachés y entorno virtual en carpetas locales (`config.directorio_datos`).
9. **Cero alucinaciones financieras:** toda cifra y ratio sale de código determinista; la IA nunca produce ni modifica números. Los tags XBRL equivalentes (`Revenues`, `SalesRevenueNet`, `RevenueFromContractWithCustomer…`) se traducen en **un único normalizador SEC** (`calculo/normalizador.py`), con listas exactas de tags por prioridad (la estandarización automática de edgartools se descartó: etiquetaba mal partidas como los dividendos de AAPL); las partidas calculadas quedan trazadas y avisadas en el semáforo. Ninguna fórmula fuera de `calculo/`.

## Navegación

| Necesito… | Archivo |
|---|---|
| Índice de toda la documentación | [docs/README.md](docs/README.md) |
| Plan, capas, fases y decisiones | [docs/plan.md](docs/plan.md) |
| Contenido del informe (índice) | [docs/estructura-informe.md](docs/estructura-informe.md) |
| Quién produce cada bloque, editor, versiones | [docs/editor-y-versiones.md](docs/editor-y-versiones.md) · código en `src/informes_warrants/informe/` y `almacenamiento/` |
| Modelo de lenguaje (llama4/Groq, Ollama) | [docs/ia.md](docs/ia.md) · `src/informes_warrants/ia/` |
| Cómo contribuir | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Qué reutilizar y dónde (rutas exactas) | [docs/inventario/README.md](docs/inventario/README.md) |
| Resumen de los repos base y licencias | [docs/repositorios-base.md](docs/repositorios-base.md) |
| Identidad corporativa (colores, tipografía, logo) | [docs/identidad-corporativa.md](docs/identidad-corporativa.md) |
| Decisiones pendientes del usuario | [docs/requisitos-pendientes.md](docs/requisitos-pendientes.md) |
| Tareas que faltan (3 fases y pendientes P1-P3) y propuestas de los informes de referencia (valoradas) | [docs/hoja-de-ruta.md](docs/hoja-de-ruta.md) · [docs/propuestas-referencias.md](docs/propuestas-referencias.md) |
| Carencias de contenido, soluciones y orden de trabajo | [docs/rigor-del-contenido.md](docs/rigor-del-contenido.md) |
| Motor matemático y normalizador SEC | `src/informes_warrants/calculo/` (normalizador con LTM, trimestres y segmentos; métricas; DCF con escenarios, DCF inverso y atribución; proyección del BPA, flujo y balance; valoración relativa y suma de partes; múltiplos históricos; síntesis del precio objetivo; historial; puntuaciones; analítica; notas; definiciones; calidad) · tests en `tests/test_calculo.py` y `tests/test_bloque_r.py` |
| Plantilla y PDF del informe | `src/informes_warrants/plantillas/informe/` · `informe/render.py` · [ejemplo](docs/ejemplos/AAPL_FY2025_borrador.pdf) |
| Ingesta (SEC, mercado, comparables, gobierno, riesgos) | `src/informes_warrants/ingesta/` (índice en su `__init__.py`) |
| Configuración de EDGAR | [src/informes_warrants/config.py](src/informes_warrants/config.py), [.env.example](.env.example) |
| Texto legal del informe | [src/informes_warrants/plantillas/legal/descargo.md](src/informes_warrants/plantillas/legal/descargo.md) |

## Flujo de datos

```
ticker → ingesta/ (SEC + precio, snapshot) → calculo/ (métricas) → visual/ + plantillas/ (gráficos, tablas, HTML → PDF)
       → ia/ (riesgos y MD&A con citas) → ui/ (Streamlit: editor híbrido) → almacenamiento/ (versiones)
```

## Marca

Solo tres colores: burdeos `#2B0B02`, negro `#000000` y blanco `#FFFFFF`. Tipografía: Montserrat (títulos) + Inter (texto). Estilo sobrio e institucional, inspirado en Morningstar (sin sus marcas).

## Comandos

```bash
pip install -e ".[dev,pdf]"   # instalar (Python 3.13; entorno fuera de OneDrive)
pytest -m "not red"           # tests sin conexión (CI); `pytest` incluye la SEC real
ruff check src tests          # estilo
informes-warrants -h          # comandos disponibles
```

## Definition of Done

- El razonamiento de reutilización (regla 1) está escrito en el commit o en la doc.
- Hay test que valida la cifra o el comportamiento real (valores *golden* de AAPL para cálculos).
- Docs y [docs/plan.md](docs/plan.md) actualizados si cambia una decisión.
- Commit en español con descripción clara.
