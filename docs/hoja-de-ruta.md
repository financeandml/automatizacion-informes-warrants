# Hoja de ruta: de borrador por CLI a SaaS

Estado a 2026-10-12. Recoge todo lo que falta, incluidas las tareas pendientes de [requisitos-pendientes.md](requisitos-pendientes.md) y [rigor-del-contenido.md](rigor-del-contenido.md). Cada tarea termina con tests, documentación, commit y, si cambia el PDF, un PDF intermedio para revisión.

Las ideas de los informes de referencia (R1-R18) están en [propuestas-referencias.md](propuestas-referencias.md). **No se implementan sin valoración del usuario.** En la tabla figuran como «propuesta R…».

**Empresas de prueba:** IOVA, ORCL y NFLX (más AAPL, que es la referencia de los tests).

## Cerrado al 100 %

- ~~Carencias 1-3 y 5-8 del contenido~~: LTM, escenarios, DCF inverso, proyección hasta el BPA, comparables con aviso, remuneración en acciones como coste, gobierno, puntuaciones, cambios del Item 1A, notas y anexo de metodología.
- ~~Comparables automáticos orientativos~~: aviso antes de emitir, sin bloquear la emisión y sin texto interno en el informe.
- ~~Proyecto ordenado para recién llegados~~: índices de la documentación y de los módulos, README.
- ~~Normalizador con las empresas de prueba~~ (2026-10-12):
  - BAI declarado por componentes (ORCL).
  - Ajuste de acciones y BPA por desdoblamientos (NFLX 10:1 en 2025).
- ~~Decisiones del usuario F2-F4~~:
  - Parámetros del fondo: los pone el analista.
  - Fuentes externas: solo para opciones y posiciones en corto.
  - Apartado 21: resultados de la empresa.

## Fase A: primer uso real (un analista, en su ordenador)

Objetivo: que el analista genere, complete, emita (PDF descargable) y versione informes reales de cualquier empresa operativa de EEUU desde una interfaz.

| # | Tarea | Decisiones del usuario y detalle | Estado |
|---|---|---|---|
| A1 | Segmentos y geografía | Los tres desgloses solo si suman el total; 5 años; LTM solo si la empresa lo publica. Plan de 6 pasos en [rigor-del-contenido.md](rigor-del-contenido.md#tarea-pendiente-segmentos-y-geografía-plan) | Lista para empezar |
| A2 | Apartado 2: resumen ejecutivo | 4 hechos clave por reglas (propuesta R1: etiquetas temáticas) | Lista para empezar |
| A3 | Apartado 3: qué hace la empresa | Segmentos (A1) y concentración de clientes | Tras A1 |
| A4 | Apartado 6: catalizadores | Bloque de IA del MD&A conectado; en el informe, la propuesta automática; editable en la interfaz (A12). Calendario: vencimientos de deuda (verificado), junta anual y próximos resultados estimados **siempre posteriores a la fecha de emisión**; hechos relevantes del 8-K de 12 meses. Pipeline de biotecnológicas: propuesta R4 | Lista para empezar |
| A5 | Apartado 14: competencia | Párrafo «Competition» del Item 1 y cuotas entre los comparables del analista, en español; ROIC − WACC y estabilidad del margen frente a la mediana; crecimiento de los comparables: propuesta R10 | Lista para empezar |
| A6 | Apartado 18: insiders y accionistas | Form 4 de 12 meses: solo compras y ventas en mercado, separadas de la retribución en acciones; accionistas > 5 % (proxy y 13D/G) | Lista para empezar |
| A7 | Apartado 20: clasificación de riesgos | **No se ejecuta.** Taxonomía a decidir sobre la propuesta R5. Autonomía de caja y dilución: propuesta R2 | Pendiente de decisión |
| A8 | Apartado 21: historial de resultados | Resultados de la empresa; alarmas SEC (8-K 4.01/4.02, 10-K/A, NT 10-K/10-Q, debilidad material, *going concern*); reacción bursátil a 5 sesiones tras cada 8-K 2.02, sin comparar con índices; tabla de 8 trimestres: propuesta R3 | Lista para empezar |
| A9 | Gráficos pendientes | Cascada EBITDA → FCF y perfil de vencimientos de deuda | Lista para empezar |
| A10 | Emisores extranjeros en el PDF | `construir` solo busca 10-K: añadir 20-F/40-F (textos del 20-F y cifras en USD, ya resueltos en `ingesta/divisas.py`) | Lista para empezar |
| A11 | Versiones conectadas al informe | Detectar 10-Q/10-K → construir → guardar contenido, *snapshot* de datos (JSON) y PDF por versión; herencia de lo que aportó el analista | Lista para empezar |
| A12 | Interfaz Streamlit (un analista, en su ordenador) | Panel con estados; editor híbrido (cifras de solo lectura, textos en Markdown, estimaciones, escenarios, comparables y catalizadores editables); vista previa en tiempo real; avisos antes de emitir; botón «Confirmar emisión»; descarga del PDF | Tras A1-A11 |
| A13 | Autoría | Nombre y contacto del analista y contacto de la empresa en la portada (propuesta R6) | Faltan los datos (nombre, correo, teléfono, empresa) |
| A14 | Batería de regresión | IOVA, ORCL, NFLX, AAPL y una muestra de sectores (MSFT, JNJ, XOM, TSLA, RIVN, KO) generadas en cada cambio, comparando cifras clave | Lista para empezar |

## Fase B: perfeccionar el contenido y la valoración

| # | Tarea | Detalle | Estado |
|---|---|---|---|
| B1 | Motor de valoración | Con los documentos del usuario (aviso pendiente); reutilizar FinRobot (SOTP, DDM, ingreso residual, agregador). Candidatas: R8, R11, R12, R14, R15 | Esperando documentos |
| B2 | Plantillas sectoriales en PDF | Banca, seguros, REIT y BDC (las métricas ya se calculan en `calculo/sectoriales.py`) | Lista para empezar |
| B3 | Apartados 4 y 5 | Estructura corporativa (filiales) y equipo directivo (cargos, antigüedad, rentabilidad para el accionista en su mandato, cambios del 8-K 5.02) | Lista para empezar |
| B4 | Apartados 12 y 23-25 | Criterios, checklist, gestión del riesgo y seguimiento con los parámetros que fija el analista bajo su responsabilidad; pruebas históricas internas con vectorbt | Lista para empezar |
| B5 | Apartados 15-17 y 19 | Opciones, volatilidad implícita y posiciones en corto con fuentes externas etiquetadas «no auditadas» (aprobado **solo** para esto); 13F por emisor desde la SEC | Lista para empezar |
| B6 | Reorganizar el PDF según el índice A-I | Más adelante, por decisión del usuario (hoy se mantienen las secciones 01-06); con tabla de contenidos | Aplazado |
| B7 | Cambios sobre lo «hecho» | DuPont; propuestas R9, R13, R18 si se aprueban | Al final |
| ~~B8~~ | ~~Historial de nuestras recomendaciones en el apartado 21~~ | Descartado: el apartado 21 es de la empresa. El historial de recomendaciones como aviso legal es la propuesta R17 | Descartado |
| B9 | Comparación entre versiones en la interfaz | Diferencias de textos, estimaciones y recomendación (la lógica ya existe); propuesta R16 | Tras A11 y A12 |

## Fase C: lanzamiento del SaaS

| # | Tarea | Detalle |
|---|---|---|
| C1 | Sustituir vectorbt | Commons Clause: prohíbe venderlo (uso interno permitido hasta entonces) |
| C2 | Usuarios y permisos | Autenticación, roles (analista, revisor), varias empresas cubiertas por usuario |
| C3 | Despliegue | Servidor, base de datos gestionada, copias de seguridad, cachés de la SEC y del mercado |
| C4 | Avisos automáticos | Nuevo 10-Q/10-K → versión detectada → aviso al analista |
| C5 | Rendimiento | Caché de companyfacts y de comparables; generación en segundo plano |
| C6 | Migración a edgartools 6 | Fijado en `<6`: la 6.0 cambia la API |
| C7 | Legal y licencias | Aviso legal (sistema de recomendación: propuesta R7), atribuciones (MIT/Apache) y licencias de datos |
| C8 | Observabilidad | Registro de errores, tiempos y uso del modelo de lenguaje |
