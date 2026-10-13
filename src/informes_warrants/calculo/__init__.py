"""Capa 2: motor matemático. Toda cifra y todo ratio del informe sale de aquí (regla 9 de CLAUDE.md).

- normalizador.py: único traductor de tags XBRL a partidas (anual, LTM, trimestres, segmentos, clientes y
  vencimientos de deuda); trazabilidad de cada dato.
- metricas.py: márgenes, FCF, rentabilidades, múltiplos y componentes del EV.
- calidad.py: semáforo de calidad de los datos (bloquea la emisión si la SEC no cuadra).
- dcf.py: DCF por escenarios, sensibilidades, DCF inverso, beta y atribución de cambios entre versiones.
- proyeccion.py: cuenta de resultados, flujo de caja y balance proyectados.
- valoracion_relativa.py: medianas y rangos de comparables, valor implícito y suma de partes.
- historico.py: múltiplos frente a su propia historia. sintesis.py: derivación del precio objetivo.
- historial.py: historial de recomendaciones. hechos_clave.py: los 4 hechos del resumen ejecutivo.
- insiders.py: compras y ventas de insiders. calendario.py: fechas estimadas de catalizadores.
- analitica.py: puente del margen, apalancamiento operativo, uso del capital, autonomía de caja, origen del
  crecimiento, cascada EBITDA → FCF, reacción a los resultados, cuotas y estabilidad del margen.
- puntuaciones.py: Altman Z, Beneish M y Piotroski F.
- notas.py: notas de contexto de los ratios.
- sectoriales.py: métricas de banca, seguros, REIT y BDC.
- definiciones.py: texto del anexo de metodología.
"""
