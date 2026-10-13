# Estructura del informe

## Índice objetivo (definido por el usuario, 2026-10-11)

El informe de apertura de posición sigue este índice. Estado a 2026-10-12:
- **Hecho**: implementado y en el PDF.
- **Parcial**: hay una parte; es la prioridad.
- **Ejecutable**: se puede hacer con datos de la SEC o con parámetros del fondo; aparcado.
- **Externo**: necesita fuentes fuera de la SEC (sin auditar); aparcado.
- **Analista**: lo escribe el analista dentro del SaaS.

La maquetación aprobada es la del [ejemplo](ejemplos/AAPL_FY2025_borrador.pdf). Los cambios sobre lo «hecho» se dejan para el final.

| Apartado | Estado | Qué hay y dónde (o qué falta) |
|---|---|---|
| Tabla de contenidos | Ejecutable | WeasyPrint numera páginas (`target-counter`) |
| Descargo de responsabilidad | Hecho | Al final del PDF y una línea en cada pie (`plantillas/legal/descargo.md`) |
| **A. Resumen ejecutivo y contexto de la tesis** | | |
| 1. Ficha de empresa | Hecho | Portada: mercado (con valor contable por acción, capital flotante y volumen en acciones), datos financieros (2 FY + LTM + 3 estimados), múltiplos LTM, comportamiento en bolsa, rango pesimista-optimista y autoría |
| 2. Resumen ejecutivo y contexto de la tesis | Hecho | Titular automático, recomendación, indicadores y 4 hechos clave por reglas (sección 01); la tesis es del analista. Etiquetas temáticas: R1 (P1) |
| **B. Perfil corporativo y modelo de negocio** | | |
| 3. ¿Qué hace la empresa? | Hecho | Cita del Item 1; segmentos (con resultado operativo), producto y geografía de 5 años validados contra el total, con LTM provisional (F7); gráfico, origen del crecimiento y concentración de clientes declarada |
| 4. Estructura corporativa | Hecho | Filiales del Exhibit 21 con sus jurisdicciones y accionistas > 5 % (proxy, 13D/G), en la sección 03 |
| 5. Equipo directivo | Parcial (avanzado) | Quien presenta Form 4 con su cargo, alta como insider (Form 3), rentabilidad de la acción desde entonces y cambios del 8-K 5.02; la trayectoria es del analista |
| 6. Pipeline y catalizadores | Hecho | Catalizadores del MD&A (IA con cita); calendario en borrador «Revisar» con fechas siempre posteriores a la emisión (lo confirma o introduce el analista); hechos relevantes del 8-K de 12 meses; pipeline de biotecnológicas: campo del analista |
| **C. Análisis fundamental y métricas financieras** | | |
| 7. Estado de resultados | Hecho | 5 FY + LTM; últimos 8 trimestres; proyección hasta el BPA (`calculo/proyeccion.py`) |
| 8. Balance de situación | Hecho | 5 FY + LTM; DFN; balance resumido proyectado que cuadra cada año |
| 9. Flujo de caja | Hecho | FCF y FCF tras remuneración en acciones; dividendos y recompras; flujo de caja proyectado y dos gráficos |
| 10. Métricas de valoración | Parcial (avanzado) | Múltiplos LTM, DCF por escenarios con desencadenantes, DCF inverso, comparables (con crecimiento a 3 años), múltiplos frente a su historia, suma de partes, puente del EV con ajustes y derivación ponderada del precio objetivo con gráfico de rangos. Sin la lista del analista, comparables fuera del precio y aviso antes de emitir (no bloquea). Pendiente: PEG y el **motor de valoración** con los modelos del usuario. El consenso es externo |
| 11. Rentabilidad y eficiencia | Hecho | ROE, ROIC, ROA, ROCE, márgenes y notas de contexto |
| 12. Criterios de valoración personales | Hecho | Umbrales del fondo (los fija el analista) evaluados frente al informe |
| **D. Mercado objetivo y posicionamiento competitivo** | | |
| 13. Tamaño de mercado (TAM/SAM/SOM) | Analista | Sin fuente pública rigurosa |
| 14. Análisis competitivo | Hecho | Apartado «Competition» del Item 1 traducido (IA verificada), cuotas de ingresos, ROIC − WACC y estabilidad del margen frente a los comparables del analista, tabla de comparables; la valoración de la ventaja competitiva es del analista |
| **E. Opciones y flujo de derivados** | | |
| 15. Cadena de opciones | Hecho (externo) | Put/call por volumen y posiciones, max pain y actividad inusual (yfinance, no auditado), en la sección 06 |
| 16. Posicionamiento institucional en derivados | Externo | *Sweeps* y *dark pool* necesitan una fuente de pago o FINRA con retraso: fuera por ahora |
| 17. Volatilidad implícita | Hecho (externo) | Implícita ponderada (calls, puts) frente a la realizada a 30 días con cotizaciones propias; el ranking histórico necesita guardar historial |
| **F. Posicionamiento institucional y fondos** | | |
| 18. Accionistas institucionales e insiders | Parcial (avanzado) | Form 4 de 12 meses (compras y ventas en mercado, plan 10b5-1, retribución aparte), accionistas > 5 % (proxy y 13D/13G) y participación institucional de yfinance (externa). Falta: 13F por emisor desde la SEC |
| 19. Posicionamiento en corto | Hecho (externo) | Acciones en corto, % del flotante, días para cubrir y variación mensual (FINRA vía yfinance, no auditado) |
| **G. Riesgos y *due diligence*** | | |
| 20. Riesgos principales | Parcial (avanzado) | 5 principales con cita (IA), cambios frente al 10-K anterior, Altman, Beneish y Piotroski y autonomía de caja (si consume caja); la clasificación por tipo, aparcada (R5) |
| 21. Historial de resultados anteriores | Hecho | Publicaciones de resultados (8-K 2.02) con su trimestre y la reacción a 5 sesiones, sin comparar; alarmas de la SEC de 5 años |
| **H. Tesis de inversión y gestión de la posición** | | |
| 22. Tesis de inversión consolidada | Analista | Plantilla que ate cada asunción a una cifra del modelo |
| 23. Checklist de entrada | Hecho | Criterios cuantitativos automáticos + criterios cualitativos del analista (con borrador de la IA) |
| 24. Gestión del riesgo | Hecho | Stop por volatilidad, tamaño por presupuesto de riesgo, VaR/CVaR, días de liquidez y prueba histórica del stop |
| 25. Seguimiento post-entrada | Hecho | Fechas de revisión del calendario, precio objetivo, stop, versiones por 10-Q/10-K y criterios de salida del analista |
| **I. Apéndices** | | |
| 26. Fuentes y referencias | Parcial (avanzado) | Anexo A (trazabilidad de cada partida) y anexo B (metodología, sistema de recomendación, historial de recomendaciones y documentos usados) |

## Bloques actuales del informe

El PDF de hoy se compone de los 35 bloques de [`informe/secciones.py`](../src/informes_warrants/informe/secciones.py): 19 AUTO, 5 PLANTILLA, 3 IA y 8 ANALISTA (detalle en [editor-y-versiones.md](editor-y-versiones.md)). Siguen el índice del informe de referencia inicial (Lighthouse/IEAF sobre Treelogic, solo como índice de contenidos):
- §1 portada
- §2 conclusiones
- §3 gráficos
- §4 negocio
- §5 industria
- §6 análisis financiero
- §7 valoración
- §8 riesgos
- §9 gobierno
- anexos A1-A6 y aviso legal

Al desarrollar el índice objetivo, cada apartado nuevo se añade como bloque en ese archivo. Qué se reutiliza de los repos base para cada necesidad está en el [inventario](inventario/README.md); el diseño de los apartados parciales, en [rigor-del-contenido.md](rigor-del-contenido.md).
