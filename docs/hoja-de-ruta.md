# Hoja de ruta: de borrador por CLI a SaaS

Propuesta del 2026-10-12, pendiente de validación del usuario. Recoge todo lo que falta, incluidas las tareas pendientes de [requisitos-pendientes.md](requisitos-pendientes.md) y [rigor-del-contenido.md](rigor-del-contenido.md). Cada tarea termina con tests, documentación, commit y, si cambia el PDF, un PDF intermedio para revisión.

## Fase A: primer uso real (uso interno, un analista, localhost)

Objetivo: que el analista genere, complete, emita y versione informes reales de cualquier empresa operativa de EEUU desde una interfaz.

| # | Tarea | Detalle |
|---|---|---|
| A1 | Segmentos y geografía | Plan cerrado de 6 pasos en [rigor-del-contenido.md](rigor-del-contenido.md#tarea-pendiente-segmentos-y-geografía-plan): ejes por prioridad, validación (suma = total), sin subtotales, nombres por miembro, 5 años, contribución al crecimiento, barras apiladas |
| A2 | Apartado 2: resumen ejecutivo | 3-5 «hechos clave» por reglas (mayor cambio, valoración frente a su historia, alarmas, riesgos nuevos) |
| A3 | Apartado 3: qué hace la empresa | Segmentos (A1) y concentración de clientes en la sección de negocio |
| A4 | Apartado 6: catalizadores | Conectar el bloque de IA del MD&A (ya hecho); calendario: vencimientos de deuda (verificado), junta anual y próximos resultados estimados; hechos relevantes del 8-K de 12 meses (1.01, 2.01, 5.02…) |
| A5 | Apartado 14: competencia | Párrafo «Competition» del Item 1 (cita literal), cuotas entre los comparables del analista, ROIC − WACC y estabilidad del margen frente a la mediana |
| A6 | Apartado 18: insiders | Form 4 de 12 meses: compras y ventas en mercado separadas de concesiones y ejercicios, con señal de planes 10b5-1 |
| A7 | Apartado 20: clasificación de riesgos | Por reglas de palabras clave: regulatorio, financiero, competitivo, ejecución y otros |
| A8 | Apartado 21: historial | Alarmas SEC (8-K 4.01/4.02, 10-K/A, NT 10-K/10-Q, debilidad material, *going concern*) y reacción bursátil tras cada 8-K 2.02 |
| A9 | Gráficos pendientes | Cascada EBITDA → FCF y perfil de vencimientos de deuda |
| A10 | Emisores extranjeros en el PDF | `construir` solo busca 10-K: añadir 20-F/40-F (textos del 20-F y cifras en USD, ya resueltos en `ingesta/divisas.py`) |
| A11 | Versiones conectadas al informe | Detectar 10-Q/10-K → construir → guardar contenido, *snapshot* de datos (JSON) y PDF por versión; herencia de lo que aportó el analista |
| A12 | Interfaz Streamlit (fase 7 del plan) | Panel con estados; editor híbrido (bloque fijo de solo lectura, bloque editable en Markdown, estimaciones, escenarios y lista de comparables); vista previa en tiempo real; avisos antes de emitir; botón «Confirmar emisión» |
| A13 | Autoría del informe | Analista, contacto y entidad emisora en la portada y en el aviso legal (requisito A10) |
| A14 | Batería de regresión | 15-20 empresas de sectores distintos generadas en cada cambio, comparando cifras clave (detecta regresiones del normalizador) |

## Fase B: perfeccionar el contenido y la valoración

Objetivo: informe completo según el índice A-I y valoración institucional.

| # | Tarea | Detalle |
|---|---|---|
| B1 | Motor de valoración | Con los modelos y plantillas del usuario (F1); reutilizar FinRobot (SOTP, DDM, ingreso residual, agregador de valoración); PEG y gráfico de rangos de valoración |
| B2 | Plantillas sectoriales en PDF | Banca, seguros, REIT y BDC: las métricas ya se calculan (`calculo/sectoriales.py`); falta su informe |
| B3 | Apartados ejecutables 4 y 5 | Estructura corporativa (filiales, accionistas > 5 %) y equipo directivo (cargos, antigüedad, rentabilidad para el accionista en su mandato, cambios del 8-K 5.02) |
| B4 | Apartados 12 y 23-25 | Criterios de entrada y salida, checklist, gestión del riesgo y seguimiento con los parámetros del fondo (F2); *backtesting* interno con vectorbt |
| B5 | Apartados externos 15-19 | Si se aprueban las fuentes externas (F3): opciones, volatilidad implícita, posiciones en corto, 13F por emisor |
| B6 | Reorganizar el PDF según el índice A-I | Hoy sigue las secciones 01-06 del informe de referencia; incluye tabla de contenidos |
| B7 | Cambios sobre lo «hecho» | Los que queden al final (p. ej. DuPont en rentabilidad) |
| B8 | Historial de recomendaciones | Nuestras versiones emitidas frente a la evolución del precio (si F4 lo incluye) |
| B9 | Comparación entre versiones en la interfaz | Diferencias de textos, estimaciones y recomendación (la lógica ya existe) |

## Fase C: lanzamiento del SaaS

Objetivo: servicio para usuarios externos.

| # | Tarea | Detalle |
|---|---|---|
| C1 | Sustituir vectorbt | Su licencia (Commons Clause) prohíbe venderlo |
| C2 | Usuarios y permisos | Autenticación, roles (analista, revisor), varias empresas cubiertas por usuario |
| C3 | Despliegue | Servidor, base de datos gestionada, copias de seguridad, cachés de la SEC y del mercado |
| C4 | Avisos automáticos | Nuevo 10-Q/10-K → versión detectada → aviso al analista |
| C5 | Rendimiento | Caché de companyfacts y de comparables; generación en segundo plano |
| C6 | Migración a edgartools 6 | Fijado en `<6`: la 6.0 cambia la API (`None` → excepciones) |
| C7 | Legal y licencias | Revisión del aviso legal, atribuciones (MIT/Apache) y licencias de datos |
| C8 | Observabilidad | Registro de errores, tiempos y uso del modelo de lenguaje |
