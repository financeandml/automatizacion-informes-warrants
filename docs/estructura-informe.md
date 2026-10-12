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
| 1. Ficha de empresa | Hecho | Portada: mercado, datos financieros (2 FY + LTM + 3 estimados), múltiplos LTM, comportamiento en bolsa |
| 2. Resumen ejecutivo y contexto de la tesis | Parcial | Titular automático, recomendación e indicadores; faltan los «hechos clave» por reglas; la tesis es del analista |
| **B. Perfil corporativo y modelo de negocio** | | |
| 3. ¿Qué hace la empresa? | Parcial | Cita del Item 1; **segmentos y geografía pendientes** ([plan](rigor-del-contenido.md#tarea-pendiente-segmentos-y-geografía-plan)) |
| 4. Estructura corporativa | Ejecutable | Filiales (Exhibit 21), accionistas > 5 % (proxy, 13D/G): verificado en AAPL |
| 5. Equipo directivo | Ejecutable | La retribución ya está en «Gobierno»; faltan cargos y trayectoria |
| 6. Pipeline y catalizadores | Parcial | Bloque de catalizadores del MD&A hecho (`ia/bloques.py`), sin conectar; falta el calendario (vencimientos, junta, resultados) |
| **C. Análisis fundamental y métricas financieras** | | |
| 7. Estado de resultados | Hecho | 5 FY + LTM; proyección hasta el BPA (`calculo/proyeccion.py`) |
| 8. Balance de situación | Hecho | 5 FY + LTM; DFN |
| 9. Flujo de caja | Hecho | FCF y FCF tras remuneración en acciones; dividendos y recompras |
| 10. Métricas de valoración | Parcial (avanzado) | Múltiplos LTM, DCF por escenarios, DCF inverso y comparables. Sin la lista del analista, precio solo por DCF y aviso antes de emitir (no bloquea). Pendiente: PEG y el **motor de valoración** con los modelos que aportará el usuario. El consenso es externo |
| 11. Rentabilidad y eficiencia | Hecho | ROE, ROIC, ROA, ROCE, márgenes y notas de contexto |
| 12. Criterios de valoración personales | Ejecutable | Necesita los umbrales del fondo |
| **D. Mercado objetivo y posicionamiento competitivo** | | |
| 13. Tamaño de mercado (TAM/SAM/SOM) | Analista | Sin fuente pública rigurosa |
| 14. Análisis competitivo | Parcial | Tabla de comparables; faltan el párrafo «Competition» del Item 1, las cuotas entre comparables y la evidencia de ventaja competitiva |
| **E. Opciones y flujo de derivados** | | |
| 15. Cadena de opciones | Externo | yfinance (sin auditar) |
| 16. Posicionamiento institucional en derivados | Externo | *Sweeps*: datos de pago; *dark pool*: FINRA, con retraso |
| 17. Volatilidad implícita | Externo | yfinance; el ranking de volatilidad necesita historial propio |
| **F. Posicionamiento institucional y fondos** | | |
| 18. Accionistas institucionales e insiders | Parcial | Form 4 de 12 meses (compras y ventas en mercado, separadas de la retribución) y accionistas > 5 %, verificados en AAPL (faltan en el PDF); 13F por emisor: ejecutable (datos trimestrales de la SEC) |
| 19. Posicionamiento en corto | Externo | FINRA / yfinance |
| **G. Riesgos y *due diligence*** | | |
| 20. Riesgos principales | Parcial (avanzado) | 5 principales con cita (IA), cambios frente al 10-K anterior y Altman, Beneish y Piotroski; la clasificación por tipo se decidirá sobre la propuesta R5 |
| 21. Historial de resultados anteriores | Parcial | Resultados de la empresa: alarmas SEC verificadas (8-K 4.01/4.02, 10-K/A), falta en el PDF; reacción bursátil a 5 sesiones tras cada publicación de resultados, sin comparar (idea: ai-hedge-fund `event_study`) |
| **H. Tesis de inversión y gestión de la posición** | | |
| 22. Tesis de inversión consolidada | Analista | Plantilla que ate cada asunción a una cifra del modelo |
| 23. Checklist de entrada | Ejecutable | Umbrales del apartado 12 + casillas del analista |
| 24. Gestión del riesgo | Ejecutable | Stop por volatilidad, tamaño por presupuesto de riesgo, liquidez (parámetros del fondo) |
| 25. Seguimiento post-entrada | Ejecutable | Indicadores, fechas de revisión y criterios de salida, enlazados con las versiones |
| **I. Apéndices** | | |
| 26. Fuentes y referencias | Parcial (avanzado) | Anexo A (trazabilidad de cada partida) y anexo B (metodología y documentos usados) |

## Bloques actuales del informe

El PDF de hoy se compone de los 32 bloques de [`informe/secciones.py`](../src/informes_warrants/informe/secciones.py): 19 AUTO, 4 PLANTILLA, 2 IA y 7 ANALISTA (detalle en [editor-y-versiones.md](editor-y-versiones.md)). Siguen el índice del informe de referencia inicial (Lighthouse/IEAF sobre Treelogic, solo como índice de contenidos):
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
