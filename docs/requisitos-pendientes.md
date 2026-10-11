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
| A6 | Índice definitivo: secciones que se quedan, salen o se añaden, y su orden | Marcar sobre [estructura-informe.md](estructura-informe.md) | Índice completo actual |
| A7 | Por sección: tablas y gráficos exactos, años históricos y estimados | Lista por sección | 5 años históricos + 3 estimados, en USD Mn |
| A8 | Idioma del informe y formato numérico | — | Español, coma decimal, negativos entre paréntesis (piezas: edgartools `format_value` y `moneyfmt`; hay que combinarlas) |
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

### Estado del código (por fase del plan)
| Fase | Estado |
|---|---|
| 0 | ✅ CI (tests + ruff, Ubuntu y Windows), CONTRIBUTING, Python 3.13, `edgartools>=5.61.1,<6` |
| 1 | ✅ Estados de 5 años, contraste de fuentes, mercado, riesgos. Falta: vencimientos de deuda, segmentos y *snapshot* por versión |
| 2 | ✅ Normalizador SEC, métricas, DCF, semáforo, tests *golden*. Falta: valoración por múltiplos de comparables (fase 7) |
| 3 | ✅ Primer PDF completo ([ejemplo](ejemplos/AAPL_FY2025_borrador.pdf)). Falta: gráfico de cascada FCF y de vencimientos de deuda |
| 4 | ✅ LLM, selección con cita literal, bloques de riesgos y catalizadores. Falta conectarlos al borrador (fase 3) |
| 5 | ✅ Estados, herencia, comparación, SQLite inmutable, detección. Falta guardar el *snapshot* y el PDF por versión |
| 6 | Falta: `ui/` Streamlit (diseño cerrado en [editor-y-versiones.md](editor-y-versiones.md)) |
| 7-8 | DCF, comparables, gobierno corporativo, proyecciones; usuarios y despliegue |

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
| E5 | Comparables | ✅ Automáticos por SIC; el analista puede quitar o añadir con motivo |
| E6 | Índices de referencia | ✅ S&P 500 + ETF sectorial SPDR asignado por SIC (mapeo por construir en la fase 3) |
| E7 | `git push` | ✅ Autorizado; el repo es público |
| E8 | Clave de Alpha Vantage (opcional) | Opcional, como respaldo de yfinance |
