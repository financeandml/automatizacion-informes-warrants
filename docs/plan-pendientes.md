# Plan de los pendientes y de la API de Gemini (2026-10-15)

Decisiones del usuario del 2026-10-15 y plan de trabajo de cada pendiente de la [hoja de ruta](hoja-de-ruta.md). Cada plan sigue las reglas del proyecto: reutilizar antes que construir (inventario), cero alucinaciones financieras (ninguna cifra la produce la IA) y avisos que no bloquean la emisión.

## 1. API de Gemini en lugar de FactSet

**Proceso.**
1. El usuario crea una clave gratuita en Google AI Studio y la pone en `.env` como `GEMINI_API_KEY` (nunca en el chat ni en el repositorio).
2. Proveedor `gemini` en `ia/llm.py`: Gemini tiene una API compatible con OpenAI, así que entra por el mismo camino que Groq y Ollama, sin dependencias nuevas. Modelo rápido (`gemini-2.5-flash`) para borradores y clasificaciones.
3. `ia/gemini.py`: llamada nativa con **búsqueda de Google y citas** (*grounding*) solo para los datos que no están en la SEC (consenso). Devuelve el texto, las URL citadas y el fragmento que respalda cada frase.
4. Verificación por código (regla 9): una cifra del consenso solo se admite si aparece literalmente en la fuente citada, que el código descarga y comprueba; si no, se descarta. Sale como «fuente externa, no auditada, con fecha» y **nunca entra sola en la valoración**: el analista la confirma o la copia a sus entradas.
5. Tiempos: caché por empresa y día, llamadas en paralelo con la descarga de la SEC y límite de espera; si Gemini falla o no hay clave, el informe sale igual sin ese borrador (aviso).

**¿Sustituye a FactSet?** En parte. FactSet es una base de datos con licencia que agrega las estimaciones de cada analista. Gemini no tiene consenso propio: lo **busca en webs públicas** que publican la media (ventas y BPA del año en curso y del siguiente, número de analistas). Resuelve el consenso actual con su fuente, y con la verificación literal no inventa cifras. No da series históricas del consenso, sus revisiones ni el detalle por analista, ni garantiza exactitud (las webs no están auditadas). Por eso entra como borrador externo verificable. La *guidance* de la propia empresa sí es oficial: los 8-K de resultados (anexo 99.1), que edgartools ya extrae (`EarningsRelease.guidance`).

**Qué más resuelve de una vez** (todas con borrador marcado, revisión del analista y sin cifras nuevas):

| Uso | Pendiente | Por qué Gemini |
|---|---|---|
| Etiqueta temática de los hechos clave | P1 | Clasificación de textos que ya genera el código |
| Taxonomía de los riesgos del Item 1A | P2 | Clasificación de títulos literales |
| Consenso con fuente y *guidance* de los 8-K | P22 | Búsqueda con citas y contexto largo (anexo 99.1 completo) |
| Miembros de segmento entre ejercicios y 10-Q | F7, P21 | Emparejar nombres que cambian (KO, ORCL); las cifras y la validación contra el total siguen en código |
| Citas del 10-K sobre el tamaño de mercado | P15 | Localizar frases literales en el 10-K completo (hasta 1 millón de tokens) |
| Borrador de la tesis atado a las cifras del modelo | P8 | Redacción sobre cifras que ya están en el informe |
| Matriz probabilidad × impacto | P16 | Borrador para el analista |
| Riesgos, catalizadores y competencia (hoy Groq) | — | El 10-K entero en una llamada: mejor selección, misma verificación literal |

**Riesgos y control.**
- Plan gratuito con límites de uso: caché y una llamada por bloque.
- En el plan gratuito, Google puede usar lo enviado para mejorar sus productos: solo se envía texto público de la SEC y del propio informe, nunca claves ni datos del fondo.
- Si cambia el modelo, se cambia en `.env` (`LLM_MODEL`).

## 2. Decisiones del usuario (2026-10-15)

P17 no (se integrarán más adelante) · P19 sí · P21 estandarizado · F7 se prueba con Gemini · P3 se cierra (sin valoración de empresas sin beneficios) · P4 con foco en empresas americanas · P5 cuando sea necesario · P6, P7 y P9 se integran · P8 se revisa · P10 aceptado · P11 aceptado, encajado en el índice.

## 3. Plan de cada pendiente

Orden de trabajo: primero lo que no depende de Gemini (de menor a mayor esfuerzo); después Gemini, cuando esté la clave.

| # | Análisis | Infraestructura existente (inventario y proyecto) | Integración parcial → completa |
|---|---|---|---|
| P3 | Sin beneficios no hay valoración fundamentada (usuario) | — | Se cierra: el DCF negativo ya no entra en el precio objetivo y queda marcado para el analista |
| P10 | El apartado 26 no fecha las fuentes externas | Fechas de consulta ya guardadas (yfinance, FINRA, Damodaran) | ✅ Hecho (2026-10-15) |
| P6 | Ficha sin bolsa, cierre fiscal ni empleados | edgartools `Company` (bolsa, `fiscal_year_end`); empleados: el texto «Human Capital» del Item 1 (inventario: no hay tag US GAAP; FRAA usa yfinance, sin trazabilidad) | ✅ Hecho (2026-10-15): bolsa, cierre y empleados (frase literal; «n.d.» si edgartools no extrae el Item 1, p. ej. XOM y TSLA) |
| P7 | El calendario no trae dividendos | Comprobado: ni el XBRL de los 10-Q/10-K ni companyfacts traen las fechas (KO, AAPL, JNJ, JPM, XOM); sí la frase del 8-K. FRAA `dividend_analyzer` deduce la frecuencia de los pagos de yfinance (idea de la cadencia, sin fechas de la SEC) | ✅ Hecho (2026-10-15): dividendo declarado en el 8-K con su frase → siguiente estimado por la cadencia mediana; sin 8-K de dividendos, sin evento |
| P11 | Tenedores institucionales hoy de yfinance (A6) | edgartools `ThirteenF` es por gestora; la SEC publica cada trimestre los **conjuntos de datos del 13F** (todas las gestoras, por CUSIP) | ✅ Hecho (2026-10-15): índice SQLite por trimestre (≈40 s una vez), control de coherencia acciones/valor (valor en miles corregido, incoherentes descartados), en el apartado 18 |
| P19 | DDM e ingreso residual en la plantilla general | FinRobot (Apache-2.0) `compute/operators/` DDM y ingreso residual; el DDM sectorial (B2) ya existe | ✅ Hecho (2026-10-15): `calculo/accionista.py` (FinRobot adaptado), métodos «DDM» e «Ingreso residual» en la derivación (peso 0) y hoja «DDM y RI» del libro con fórmulas, contrastada con el informe |
| P21 | Medida del resultado por segmento distinta de `OperatingIncomeLoss` (JNJ) y segmentos que cambian de nombre (KO) | Normalizador de segmentos (validación contra el total); dominios declarados por la empresa | Lista **estándar** de tags de resultado por segmento por prioridad en el normalizador, con la medida usada en el informe → equivalencias de miembros entre ejercicios (dominios declarados; Gemini como apoyo, con las cifras validadas por código) |
| P9 | Real frente a estimado con cada 10-Q | Las versiones guardan el resumen y las estimaciones (R16); los trimestres del normalizador | Comparación del trimestre real con la proyección de la versión anterior (ventas, EBIT, BPA) en el apartado 25 → aviso en la interfaz al detectar el 10-Q |
| P8 | Revisión: el apartado 22 solo ata ventas y margen | `perspectivas.md.j2`; borradores de la IA (`ia/borradores.py`) | Tabla «supuesto → cifra del modelo» (crecimiento, margen, WACC, g, valor terminal, precio de cada método) → borrador de la tesis sobre esa tabla |
| P5 | Ajuste de partidas no recurrentes definido, sin conectar | `informe/bloque_fijo.py` (`PartidaNoRecurrente`); edgartools `EarningsRelease.eps_reconciliation` (ajustes que declara la empresa) | Entrada del analista en la interfaz → EBITDA recurrente en el informe y en el motor (solo si el analista marca partidas) |
| P4 | 20-F/40-F: faltan los conceptos IFRS en el normalizador | edgar_analytics `synonyms.py` (`ifrs-full:`), edgartools `CurrencyConverter` y `_IFRS_FALLBACK_MAPPINGS`; `ingesta/divisas.py` | Listas `ifrs-full` en el normalizador para las partidas esenciales, solo emisores con ADR en NYSE/Nasdaq → PDF completo con la conversión a USD y aviso de normas IFRS |
| P1 | Hechos clave sin etiqueta temática | `calculo/hechos_clave.py` (tema por reglas); proveedor de IA | Etiqueta por reglas (ya hay `tema`) → borrador de Gemini que la afina, marcado |
| P2 | Riesgos sin clasificar por tipo | Títulos literales del Item 1A; selección con cita (`ia/seleccion.py`) | Taxonomía fija (mercado, operativo, financiero, regulatorio, competencia, tecnológico, legal) → clasificación de cada título con Gemini y verificación de que el título existe |
| P22 | Consenso de analistas | Ver §1; FinRobot `forward_estimates.py` (FMP/Yahoo, idea) | *Guidance* de los 8-K con cita (oficial) → consenso con Gemini y verificación literal, como entrada opcional del motor |
| F7 | LTM por segmento | `segmentos_ltm` (provisional, validado contra el total LTM) | Emparejamiento de miembros entre 10-K y 10-Q con Gemini cuando los nombres no coinciden; las cifras siguen en código |
