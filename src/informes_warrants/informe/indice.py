"""Índice A-I del informe (B6): la tabla de contenidos y la numeración del PDF.

Es el índice que definió el usuario (docs/estructura-informe.md, 2026-10-11) y que pasó a ser la tabla de contenidos
y la numeración del PDF (decisión del 2026-10-14: se mantienen el formato y todo lo demás; solo cambia la enumeración).
Las plantillas (general y sectorial) colocan cada bloque bajo su apartado con las macros de `_indice.html.j2`; todos
los apartados salen siempre, para que la numeración no tenga huecos (sin datos, una línea que lo dice).
"""

INDICE: tuple[tuple[str, str, tuple[tuple[int, str], ...]], ...] = (
    ("A", "Resumen ejecutivo y contexto de la tesis", ((1, "Ficha de empresa"), (2, "Resumen ejecutivo y contexto de la tesis"))),
    ("B", "Perfil corporativo y modelo de negocio", ((3, "¿Qué hace la empresa?"), (4, "Estructura corporativa"),
                                                     (5, "Equipo directivo"), (6, "Pipeline y catalizadores"))),
    ("C", "Análisis fundamental y métricas financieras", ((7, "Estado de resultados"), (8, "Balance de situación"),
                                                          (9, "Flujo de caja"), (10, "Métricas de valoración"),
                                                          (11, "Rentabilidad y eficiencia"), (12, "Criterios de valoración personales"))),
    ("D", "Mercado objetivo y posicionamiento competitivo", ((13, "Tamaño de mercado (TAM, SAM y SOM)"), (14, "Análisis competitivo"))),
    ("E", "Opciones y flujo de derivados", ((15, "Cadena de opciones"), (16, "Posicionamiento institucional en derivados"),
                                            (17, "Volatilidad implícita"))),
    ("F", "Posicionamiento institucional y fondos", ((18, "Accionistas institucionales e insiders"), (19, "Posicionamiento en corto"))),
    ("G", "Riesgos y due diligence", ((20, "Riesgos principales"), (21, "Historial de resultados anteriores"))),
    ("H", "Tesis de inversión y gestión de la posición", ((22, "Tesis de inversión consolidada"), (23, "Checklist de entrada"),
                                                          (24, "Gestión del riesgo"), (25, "Seguimiento post-entrada"))),
    ("I", "Apéndices", ((26, "Fuentes y referencias"),)),
)
SECCIONES = {letra: titulo for letra, titulo, _ in INDICE}
APARTADOS = {n: titulo for _, _, apartados in INDICE for n, titulo in apartados}
