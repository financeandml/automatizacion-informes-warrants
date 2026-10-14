"""Cuatro hechos clave del resumen ejecutivo (A2), elegidos por reglas sobre la analítica ya calculada.

Patrón de financial-research-analyst-agent `src/tools/insight_engine.py` (`_obs`, `_rank_observations`;
Copyright (c) 2024 Gopal Saini, licencia MIT): cada regla produce una observación con su relevancia y se
ordenan. Cambios: sin IA, sin iconos ni «confianza»; cada hecho lleva sus cifras (que la plantilla
`hechos_clave.md.j2` redacta) y, para que los cuatro cubran aspectos distintos, se toma como mucho uno por tema
(crecimiento, rentabilidad, balance, valoración, riesgos). Los temas solo ordenan: no se muestran como etiqueta
(la etiqueta temática es la propuesta R1, aparcada en P1).

Umbrales de relevancia (fijos y documentados):
  crecimiento de ventas LTM: alta ≥ 20 %, media ≥ 8 % (en valor absoluto)
  variación del margen operativo: alta ≥ 300 pb, media ≥ 100 pb
  ROIC − WACC: alta si < 0, media si ≥ 10 pp
  autonomía de caja: crítica < 24 meses; alta si consume caja
  deuda neta / EBITDA: alta ≥ 3x, media ≥ 2x o caja neta
  potencial frente al precio objetivo: alta ≥ 30 %, media ≥ 15 %
  múltiplo frente a su historia: alta si está en el percentil ≥ 90 o ≤ 10
  alarmas de la SEC: crítica; Beneish M o Altman Z en zona de riesgo: alta
  cliente con ≥ 20 % de los ingresos: alta (≥ 10 %: media); compras agrupadas de insiders: alta
Perfiles sectoriales (B2, `observaciones_sectoriales`):
  ROE (ROTE, NII) − Ke: alta si < 0, media si ≥ 5 pp
  múltiplo principal frente al justificado por la rentabilidad: alta ≥ 30 %, media ≥ 15 % (por encima o por debajo)
  dividendo: alta si no está cubierto (pago > 100 % del FFO o cobertura del NII < 1x); si no, media
"""

RELEVANCIA = {"critica": 4, "alta": 3, "media": 2, "baja": 1}
TEMAS = ("crecimiento", "rentabilidad", "balance", "valoracion", "riesgos")
NUMERO_HECHOS = 4


def _nivel(valor: float, alta: float, media: float) -> str:
    return "alta" if abs(valor) >= alta else "media" if abs(valor) >= media else "baja"


def observaciones(e: dict) -> list[dict]:
    """Observaciones candidatas con {clave, tema, relevancia, …cifras}. `e`: entradas ya calculadas (None = sin dato)."""
    obs = []

    def anadir(clave, tema, relevancia, **cifras):
        obs.append({"clave": clave, "tema": tema, "relevancia": relevancia, **cifras})

    if e.get("crecimiento") is not None and e.get("ingresos"):
        anadir("crecimiento", "crecimiento", _nivel(e["crecimiento"], 0.20, 0.08), ingresos=e["ingresos"], crecimiento=e["crecimiento"])
    if e.get("variacion_margen_pb") is not None:
        anadir("margen", "rentabilidad", _nivel(e["variacion_margen_pb"], 300, 100), pb=e["variacion_margen_pb"],
               margen_inicio=e["margen_inicio"], margen_fin=e["margen_fin"], anio_inicio=e["anio_inicio"], principal=e.get("principal"))
    if e.get("roic_menos_wacc") is not None:
        diferencia = e["roic_menos_wacc"]
        anadir("roic_wacc", "rentabilidad", "alta" if diferencia < 0 else "media" if diferencia >= 0.10 else "baja",
               roic=e["roic"], wacc=e["wacc"], diferencia=diferencia)
    if e.get("meses_caja") is not None:
        anadir("autonomia", "balance", "critica" if e["meses_caja"] < 24 else "alta", meses=e["meses_caja"])
    elif e.get("dfn") is not None:
        ratio = e.get("dfn_ebitda")
        nivel = "media" if e["dfn"] < 0 else ("alta" if ratio is not None and ratio >= 3 else "media" if ratio is not None and ratio >= 2
                                                else "baja")
        anadir("apalancamiento", "balance", nivel, dfn=e["dfn"], dfn_ebitda=ratio)
    if e.get("potencial") is not None:
        anadir("potencial", "valoracion", _nivel(e["potencial"], 0.30, 0.15), potencial=e["potencial"],
               precio_objetivo=e["precio_objetivo"], recomendacion=e["recomendacion"])
    if e.get("percentil") is not None:
        p = e["percentil"]
        anadir("historia", "valoracion", "alta" if p >= 0.9 or p <= 0.1 else "baja", percentil=p, metrica=e["metrica_historica"],
               actual=e["multiplo_actual"], mediana=e["multiplo_mediana"])
    if e.get("alarmas"):
        anadir("alarma", "riesgos", "critica", alarma=e["alarmas"][0], numero=len(e["alarmas"]))
    for nombre, lectura in (e.get("puntuaciones") or {}).items():
        if (nombre == "Beneish M" and "probable" in lectura) or (nombre == "Altman Z" and "riesgo" in lectura):
            anadir("puntuacion", "riesgos", "alta", puntuacion=nombre, lectura=lectura)
    if e.get("cliente_principal"):
        c = e["cliente_principal"]
        anadir("cliente", "riesgos", _nivel(c["porcentaje"], 0.20, 0.10), cliente=c["cliente"], porcentaje=c["porcentaje"], anio=c["anio"])
    if e.get("compras_agrupadas"):
        anadir("insiders", "riesgos", "alta", compradores=len(e["compras_agrupadas"]["compradores"]))
    return obs


def observaciones_sectoriales(e: dict) -> list[dict]:
    """Banca, seguros, REIT y BDC: rentabilidad frente a Ke, múltiplo frente al justificado y dividendo, más las
    observaciones comunes de `observaciones` (potencial, alarmas e insiders)."""
    obs = observaciones({k: e.get(k) for k in ("potencial", "precio_objetivo", "recomendacion", "alarmas", "compras_agrupadas")})
    if e.get("diferencial") is not None:
        d = e["diferencial"]
        obs.append({"clave": "rentabilidad", "tema": "rentabilidad", "relevancia": "alta" if d < 0 else "media" if d >= 0.05 else "baja",
                    "nombre": e["rentabilidad_nombre"], "valor": e["rentabilidad"], "ke": e["ke"], "diferencial": d})
    if e.get("prima") is not None:
        obs.append({"clave": "multiplo", "tema": "valoracion", "relevancia": _nivel(e["prima"], 0.30, 0.15), "actual": e["multiplo"],
                    "justo": e["multiplo_justo"], "prima": e["prima"], "base": e["base_nombre"]})
    if e.get("rentabilidad_dividendo") is not None:
        payout, cobertura = e.get("payout_ffo"), e.get("cobertura_dividendo")
        descubierto = (payout is not None and payout > 1) or (cobertura is not None and cobertura < 1)
        obs.append({"clave": "dividendo", "tema": "balance", "relevancia": "alta" if descubierto else "media",
                    "rentabilidad": e["rentabilidad_dividendo"], "payout_ffo": payout, "cobertura": cobertura})
    return obs


def seleccionar(obs: list[dict], n: int = NUMERO_HECHOS) -> list[dict]:
    """Los `n` hechos más relevantes, como mucho uno por tema; si faltan temas, se completa con los siguientes."""
    orden = sorted(obs, key=lambda o: (-RELEVANCIA[o["relevancia"]], TEMAS.index(o["tema"])))
    elegidos, temas = [], set()
    for o in orden:
        if o["tema"] not in temas and len(elegidos) < n:
            elegidos.append(o)
            temas.add(o["tema"])
    for o in orden:
        if len(elegidos) >= n:
            break
        if o not in elegidos:
            elegidos.append(o)
    return sorted(elegidos, key=lambda o: TEMAS.index(o["tema"]))
