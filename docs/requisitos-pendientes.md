# Requisitos pendientes

Lo que hace falta definir o aportar para construir el SaaS. Cada punto incluye una **propuesta por defecto**: si no se indica otra cosa, se aplica esa.

## A. Plantilla del informe

| # | Necesito | Formato ideal | Propuesta por defecto |
|---|---|---|---|
| A1 | Ejemplo maquetado del informe | ✅ Estilo similar a los informes de Morningstar ([identidad-corporativa.md](identidad-corporativa.md)) | — |
| A2 | Página: tamaño, orientación, márgenes, columnas | Indicación o el propio ejemplo | A4 vertical, columna lateral de ladillos como en la referencia |
| A3 | Identidad: logo, colores, tipografías | ✅ Logo y nombre vectoriales en `src/informes_warrants/plantillas/marca/`; burdeos `#2B0B02`; tipografía Montserrat (títulos) + Inter (texto); logos vectorizados | — |
| A4 | Cabecera y pie de cada página | Lista de elementos | Empresa, ticker, fecha, nº de página, aviso legal breve |
| A5 | Portada: bloques y su orden | Boceto o ejemplo | Igual que la página 1 de la referencia |
| A6 | Índice definitivo | ✅ Índice A-I del usuario (26 apartados) con su estado en [estructura-informe.md](estructura-informe.md) | — |
| A7 | Por sección: tablas y gráficos exactos, años históricos y estimados | Lista por sección | 5 ejercicios + LTM + 5 periodos estimados de doce meses, en USD Mn |
| A8 | Idioma del informe y formato numérico | ✅ Español, coma decimal, negativos entre paréntesis en tablas y signo en el texto (filtros `num`, `pct`, `var`) | — |
| A9 | Texto legal / disclaimer propio | ✅ `plantillas/legal/descargo.md` | — |
| A10 | Autoría: analistas, contacto, entidad emisora | Datos | — |

## B. Editor — ✅ resuelto

Decidido por el usuario y detallado en [editor-y-versiones.md](editor-y-versiones.md):
- IA mínima: código, después plantilla y, por último, marcador para el analista.
- Edición en Markdown con vista previa en tiempo real.
- Recomendación sí: la propone el SaaS y la confirma el analista.
- El analista solo puede ajustar los comparables y las partidas no recurrentes.
- Emisión con confirmación del analista.

## C. Sistema de versiones — ✅ resuelto

Detección automática con confirmación del analista, nombre por año fiscal, herencia de lo que aportó el analista, comparación entre versiones y SQLite fuera de OneDrive ([editor-y-versiones.md](editor-y-versiones.md#versiones)).

## D. Análisis del proyecto

### Hecho
- Estructura Python (`pyproject.toml`, `src/`, tests), configuración de `EDGAR_IDENTITY` y CLI mínima.
- Documentación: [plan.md](plan.md), [estructura-informe.md](estructura-informe.md), [repositorios-base.md](repositorios-base.md).
- Repositorio público en GitHub (`origin`), sincronizado con `git push`.

### Estado del código
El estado de cada fase está en una sola tabla: [plan.md, «Fases»](plan.md#fases).

### Riesgos técnicos detectados
- ~~**Python 3.14**~~ ✅ Resuelto: el proyecto usa Python 3.13 (`requires-python >= 3.11`).
- ~~**WeasyPrint en Windows**~~ ✅ Resuelto: GTK con MSYS2, documentado en el README y detectado automáticamente.
- ~~**LLM por defecto del repo base (Ollama + llama4)**~~ ✅ Resuelto: llama4 vía Groq y `llama3.2:3b` en local ([ia.md](ia.md)).
- ~~**Sectores con contabilidad distinta**~~ ✅ Resuelto: perfiles sectoriales de banca, seguros, REIT y BDC/fondos cerrados, validados con empresas reales ([editor-y-versiones.md](editor-y-versiones.md#alcance)).
- ~~**Emisores extranjeros (20-F)**~~ ✅ Resuelto: textos del 20-F y cifras en USD. Las empresas que remiten sus riesgos a un anexo pasan ese bloque al analista.

## E. Datos del usuario

| # | Necesito | Estado |
|---|---|---|
| E1 | `EDGAR_IDENTITY` en `.env` | ✅ Configurado |
| E2 | Proveedor de LLM | ✅ Integrado: `gpt-oss-120b` en Groq (activo) + Ollama local. Groq retiró llama4; para usarlo, `OPENROUTER_API_KEY` (opcional, de pago, [ia.md](ia.md)) |
| E3 | GTK para WeasyPrint | ✅ Instalado (MSYS2 + pango) y probado |
| E4 | Alcance del universo | ✅ Plantilla general + 4 perfiles sectoriales validados con 12 empresas + extranjeros en USD; SPAC/ETF/fondos abiertos, «plantilla pendiente de validar» |
| E5 | Comparables | ✅ Propuesta automática por SIC, **solo orientativa**: sin la lista del analista, aviso antes de emitir (no bloquea); la valoración por múltiplos entra en el precio objetivo únicamente con esa lista (`--comparables`) |
| E6 | Índices de referencia | ✅ S&P 500 + ETF sectorial SPDR asignado por SIC (`ingesta/mercado.SIC_A_ETF`) |
| E7 | `git push` | ✅ Autorizado; el repo es público |
| E8 | Clave de Alpha Vantage (opcional) | Opcional, como respaldo de yfinance |
| E9 | Universo de comparables por SIC | ✅ Sin *bulk*: CIK por SIC (SEC Atom) + tickers oficiales + tamaño por API *frames*; aviso «Revisar» y lista editable (`--comparables`) |
| E10 | Remuneración en acciones en el DCF | ✅ Como coste en el flujo de caja (usuario, 2026-10-12) |
| E11 | Probabilidades de los escenarios | ✅ 25/50/25 editables |

## F. Aportaciones futuras del usuario (tareas pendientes)

| # | Qué | Estado |
|---|---|---|
| F1 | **Motor de valoración**: modelos, plantillas e información que aportará el usuario | Pendiente. Mientras tanto, el informe funciona con lo hecho: DCF por escenarios, DCF inverso y comparables con la lista del analista |
| ~~F2~~ | ~~Parámetros del fondo~~ | ✅ Los pone el analista bajo su responsabilidad (2026-10-12) |
| ~~F3~~ | ~~Fuentes externas~~ | ✅ Aceptadas **solo** para opciones y posiciones en corto, etiquetadas «no auditadas» (2026-10-12) |
| ~~F4~~ | ~~Alcance del apartado 21~~ | ✅ Resultados de la empresa; reacción bursátil a 5 sesiones, sin comparar (2026-10-12) |
| ~~F5~~ | ~~Autoría~~ | ✅ Cada persona introduce sus datos en el SaaS (configuración de la interfaz) (2026-10-12) |
| F6 | Valoración de las propuestas R1-R18 de los informes de referencia ([propuestas-referencias.md](propuestas-referencias.md)) | ✅ Valoradas (2026-10-12): R2-R4, R6-R14 y R16-R18 hechas; R1 y R5 aparcadas hasta terminar el SaaS; R15 en espera de los documentos ([hoja-de-ruta.md](hoja-de-ruta.md#tareas-pendientes-fuera-de-las-fases)) |
