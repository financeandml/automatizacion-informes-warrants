"""Definición del informe: qué bloques tiene, quién los produce y cómo se compone.

- secciones.py: lista de bloques (AUTO, PLANTILLA, IA, ANALISTA).
- construir.py: reúne los datos (construir) y compone el contexto del informe (componer, sin red).
- estimaciones.py: supuestos editables por el analista y sus escenarios.
- plantillas.py: relleno de las plantillas Markdown y marcadores [[ANALISTA: …]].
- render.py: contexto → HTML → PDF.
- cobertura.py y perfiles.py: qué plantilla usa cada empresa (general o sectorial).
- bloque_fijo.py: los dos ajustes permitidos sobre las cifras (comparables y no recurrentes).
"""
