"""Apartado 22 (P8): cada supuesto de la tesis atado a la cifra del modelo que lo recoge.

Revisión del 2026-10-15: el apartado solo ataba las ventas y el margen; ahora lista todos los supuestos que mueven el
precio objetivo con su cifra y dónde está, para que la tesis del analista (texto debajo) los explique uno a uno. No
calcula nada: toma las cifras que ya están en el contexto del informe (calculo/ y el modelo de valoración).
Cada fila: {"supuesto", "valor", "tipo" ("pct", "rango_pct", "usd", "var", "texto"), "donde"}.
"""


def _fila(supuesto: str, valor, tipo: str, donde: str) -> dict:
    return {"supuesto": supuesto, "valor": valor, "tipo": tipo, "donde": donde}


def cifras_generales(c: dict) -> list[dict]:
    est = c["estimaciones"]
    filas = [
        _fila("Crecimiento anual de las ventas (años explícitos)", (est.crecimiento_ventas[0], est.crecimiento_ventas[-1]), "rango_pct",
              "Estimaciones (apartado 10) y Entradas del modelo"),
        _fila("Margen EBITDA (años explícitos)", (est.margen_ebitda[0], est.margen_ebitda[-1]), "rango_pct", "Estimaciones (apartado 10)"),
        _fila("Coste del capital (WACC)", c.get("wacc_motor") or c.get("wacc"), "pct", "Hoja WACC del modelo"),
        _fila("Crecimiento a perpetuidad (g)", est.g, "pct", "Entradas del modelo"),
    ]
    if c.get("motor_perpetuidad") is not None:
        filas.append(_fila("Valor terminal por perpetuidad", c["motor_perpetuidad"], "pct", "Hoja DCF de cada segmento"))
    filas += [
        _fila("Valor DCF por acción (modelo de valoración)", c.get("valor_dcf"), "usd", "Consolidated y Síntesis del modelo"),
        _fila("Valor por comparables", c.get("valor_multiplos") if c.get("comparables_del_analista") else "falta la lista del analista",
              "usd" if c.get("comparables_del_analista") else "texto", "Comparables (apartado 10)"),
        _fila("Precio objetivo", c.get("precio_objetivo"), "usd", "Derivación del precio objetivo (apartado 10)"),
        _fila("Potencial frente a la cotización", c.get("potencial"), "var", "Portada"),
        _fila("Recomendación propuesta", c.get("recomendacion"), "texto", "Sistema de recomendación (apartado 26)"),
    ]
    return filas


def cifras_sectoriales(c: dict) -> list[dict]:
    est, v = c["estimaciones"], c.get("valoracion") or {}
    filas = [_fila("Coste del capital (Ke)", v.get("ke"), "pct", "Supuestos (apartado 10)"),
             _fila("Crecimiento a perpetuidad (g)", est.g, "pct", "Supuestos (apartado 10)")]
    if c.get("rentabilidad_sostenible") is not None:
        filas.append(_fila("Rentabilidad sostenible del valor contable justificado", c["rentabilidad_sostenible"], "pct",
                           "Valor contable justificado (apartado 10)"))
    filas += [_fila(f"Valor por {m.nombre.lower()}", m.valor, "usd", "Derivación del precio objetivo (apartado 10)")
              for m in c.get("metodos") or [] if m.valor is not None]
    filas += [_fila("Precio objetivo", c.get("precio_objetivo"), "usd", "Derivación del precio objetivo (apartado 10)"),
              _fila("Potencial frente a la cotización", c.get("potencial"), "var", "Portada"),
              _fila("Recomendación propuesta", c.get("recomendacion"), "texto", "Sistema de recomendación (apartado 26)")]
    return filas
