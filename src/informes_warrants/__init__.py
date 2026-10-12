"""Automatización de informes sobre empresas cotizadas en EEUU (Warrants & Co.).

Flujo: ingesta/ (SEC y mercado) → calculo/ (cifras deterministas) → informe/ (bloques, plantillas,
estimaciones) → visual/ (gráficos y PDF) → almacenamiento/ (versiones). ia/ solo elige y resume
fragmentos literales del 10-K. Punto de entrada: cli.py (`informes-warrants -h`); configuración: config.py.
"""

__version__ = "0.1.0"
