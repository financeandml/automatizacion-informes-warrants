"""Capa 1: obtención de datos (SEC y mercado). Aquí no se calcula ninguna cifra del informe.

- estados.py: estados del último 10-K tal como los presenta edgartools (comando `datos`).
- mercado.py: cotización, histórico, comportamiento frente al S&P 500 y al ETF sectorial, tipo libre de riesgo.
- comparables.py: comparables modelo (sector de Damodaran o código SIC; tamaño y datos de la SEC) y sus datos LTM.
- damodaran.py: beta desapalancada del sector y clasificación de empresas por sector (Damodaran, NYU Stern).
- gobierno.py: auditor y retribución (proxy DEF 14A).
- riesgos.py: títulos del Item 1A y comparación con el informe anual anterior.
- insiders.py: Form 4, accionistas de más del 5 % (proxy) y 13D/13G.
- eventos.py: 8-K (resultados, hechos relevantes) y alarmas de la SEC.
- competencia.py: apartado «Competition» del Item 1, literal.
- nombres.py: nombre de la empresa legible (la SEC registra muchos en mayúsculas).
- divisas.py: conversión a USD de los emisores extranjeros (20-F).
"""
