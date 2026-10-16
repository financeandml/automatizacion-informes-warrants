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
| P21 | Medida del resultado por segmento distinta de `OperatingIncomeLoss` (JNJ) y segmentos que cambian de nombre (KO) | Normalizador de segmentos (validación contra el total); dominios declarados por la empresa | ✅ Hecho (2026-10-15): lista estándar de medidas por prioridad y partidas de conciliación (corporativo, eliminaciones y segmentos que ya no existen); KO valida sus 5 años y el motor lo valora por segmentos; JNJ, con su medida; suma de partes solo con resultado operativo |
| P9 | Real frente a estimado con cada 10-Q | Las versiones guardan el resumen y las estimaciones (R16); los trimestres del normalizador | ✅ Hecho (2026-10-15): tabla en el apartado 25 y aviso antes de emitir si la desviación supera el 5 % |
| P8 | Revisión: el apartado 22 solo ata ventas y margen | `perspectivas.md.j2`; borradores de la IA (`ia/borradores.py`) | ✅ Revisado y completado (2026-10-15): tabla «supuesto → cifra del modelo» en el apartado 22 (general y sectorial), sobre la que escribe el analista |
| P5 | Ajuste de partidas no recurrentes definido, sin conectar | `informe/bloque_fijo.py` (`PartidaNoRecurrente`); edgartools `EarningsRelease.eps_reconciliation` (ajustes que declara la empresa) | Decisión (2026-10-15): se conecta cuando el analista marque su primera partida no recurrente; hoy ninguna versión lo hace y conectarlo cambiaría el EBITDA de la SEC en todo el informe sin motivo |
| P4 | 20-F/40-F: faltan los conceptos IFRS en el normalizador | edgar_analytics `synonyms.py` (`ifrs-full:`), edgartools `CurrencyConverter` y `_IFRS_FALLBACK_MAPPINGS`; `ingesta/divisas.py` | ✅ Hecho (2026-10-15): 20-F/40-F en el flujo, equivalentes IFRS verificados (NVO, TSM), cifras en USD (medio/cierre), por ADS (con detección de XBRL ya por ADS), último ejercicio del XBRL si companyfacts no lo trae; segmentos en otra moneda, sin desglose |
| P1 | Hechos clave sin etiqueta temática | `calculo/hechos_clave.py` (tema por reglas); proveedor de IA | ✅ Hecho (2026-10-15): etiqueta temática por código y lectura de la IA sin cifras nuevas (Gemini con clave; si no, el proveedor activo) |
| P2 | Riesgos sin clasificar por tipo | Títulos literales del Item 1A; selección con cita (`ia/seleccion.py`) | ✅ Hecho (2026-10-15): categoría (R5) y supuesto amenazado, validados contra listas cerradas, en el apartado 20 |
| P22 | Consenso de analistas | Ver §1; FinRobot `forward_estimates.py` (FMP/Yahoo, idea) | ✅ Hecho (2026-10-15): guidance del comunicado de resultados con cita literal (funciona con cualquier proveedor) y consenso con Gemini verificado en su fuente; la prueba real del consenso espera la clave |
| F7 | LTM por segmento | `segmentos_ltm` (provisional, validado contra el total LTM) | ✅ Hecho (2026-10-15): conciliación del 10-Q incluida y emparejamiento de nombres por la IA validado por la suma del LTM |

## 4. Segunda tanda (decisiones del usuario, 2026-10-15)

| # | Decisión | Estado |
|---|---|---|
| P12 | Se queda como está (quizás en el futuro) | Aparcada |
| P13 | No es necesaria | Cerrada |
| P14 | Se hará en el futuro | Aparcada |
| P15 | Integrar | ✅ Citas literales del Item 1 que cifran el mercado (dinero o pacientes), apartado 13 |
| P16 | Con la API de Gemini | ✅ Matriz probabilidad × impacto (valores cerrados) en la misma llamada que la clasificación de riesgos, apartado 20 |
| P18 | Solo si siguen en la empresa | ✅ Los que presentan Form 4 en 12 meses: Form 3 por su CIK o, si es anterior a 2003, su primer Form 4 («≥») |
| P20 | Lo decide el analista y lo marca el SaaS | ✅ Aviso antes de emitir y en la interfaz en banca, seguros, REIT y BDC |
| C1 | Sustituir vectorbt | ✅ No se usa ni es dependencia |
| C2 | Repositorio en GitHub con acceso controlado por el usuario; uso intuitivo para cualquiera | ✅ Primeros pasos, guía de 4 pasos, conexiones y diagnóstico en la interfaz. La visibilidad del repositorio (hoy público) la decide el usuario en GitHub |
| C3 | Descargar de GitHub y abrir en localhost | ✅ `instalar.ps1` / `instalar.sh` y `abrir.bat` / `abrir.sh`; probado desde un clon limpio (3,5 min de instalación, 175 tests, informe de KO en 76 s) |
| C4 | Avisos de informes nuevos, sin complicarse | ✅ Una consulta al día por empresa seguida al abrir la interfaz |
| C5 | Rendimiento y seguridad, prioritarios | ✅ Plan abajo |
| C6 | No migrar a edgartools 6 | Cerrada: se mantiene `<6` |
| C7, C9 | Equipo legal / sin planes | Fuera del alcance |
| C8 | Observabilidad | ✅ Plan abajo |
| C10 | Solo si ayuda a instalar y usar | ✅ README «Puesta en marcha (5 minutos)» y guía en la interfaz |
| C11 | Optimización, limpieza y pruebas | ✅ Sin código muerto (todos los módulos se usan), sin caracteres de control, prueba desde cero y AppTest de la interfaz |

**C5, plan interno.** Rendimiento: medir por etapas (C8) → atacar lo que más pesa: comparables en paralelo y normalizando solo las 3 partidas que usan; consultas independientes del informe en paralelo; evaluador del modelo con el grafo inverso en caché (36 s → 1,8 s); diagnóstico de la interfaz solo a petición. Resultado: `reunir` de MSFT de 318 s a 51 s. Interfaz (2026-10-15): cargar los datos y generar el PDF y el Excel van en segundo plano (`ui/tareas.py`; se puede ir a otras pantallas y las descargas quedan en la barra lateral) y el editor solo recompone el informe, la vista previa y el libro si cambia algo del analista (antes, unos 4 s en cada clic). La IA sigue con Groq (`LLM_PROVIDER=groq` en el `.env` local) mientras Google rechace el proyecto de Gemini: los reintentos de Gemini eran los 168 s de la IA. Barrido del 2026-10-16 (IOVA, medido): carga de 264 s a 30-60 s hasta abrir el editor (avisos de edgartools que calculaban sugerencias por cada concepto ausente: 68 s; comparación de riesgos con cotas de difflib: 18 s → 3 s, mismo resultado; Form 3 en paralelo; IA con menos tokens y respaldo por cupo, ver docs/ia.md); los borradores llegan después en segundo plano; datos y tareas sobreviven a recargar el navegador (ticker y pantalla en la dirección); ticker inexistente con aviso claro y nombre de la empresa al escribirlo; campos con borde; errores de pantalla como aviso, no como traza. Navegación (2026-10-16): la vista previa ya no va incrustada (2,4 MB por clic, casi todo fuentes en base64): la sirve un servidor local de solo lectura en 127.0.0.1 (`ui/vista.py`) y el navegador guarda en caché las fuentes; el aviso de tareas solo se refresca si hay algo en curso. Sin congelaciones (2026-10-16): la carga, los borradores, la emisión y cada recomposición del informe (~3 s de CPU) van en procesos de trabajo y no en hilos, porque el Python puro acaparaba el intérprete (GIL) y la página no respondía; medido con IOVA real: peor respuesta de la página 0,13 s durante la carga. El selector de pantalla y el ticker usan claves fijas de sesión (con el valor inicial como parámetro, Streamlit los reiniciaba y la pantalla volvía sola a la anterior). Seguridad: interfaz solo en `localhost` y con protección XSRF; claves solo en el `.env` local (ignorado por git), nunca en registros ni en URLs (Gemini, en cabecera); textos de terceros escapados en el HTML; datos fuera de OneDrive.

**C8, plan interno.** Registro rotativo (5 × 1 MB) y tiempos por etapa (`reunir`, `componer`, `pdf`, `excel`, `ia`) en la carpeta de datos; `informes-warrants diagnostico` y «Configuración → Diagnóstico» comprueban Python, dependencias, PDF, LibreOffice, identidad y claves (presentes o no, nunca su valor) y resumen tiempos y errores.
