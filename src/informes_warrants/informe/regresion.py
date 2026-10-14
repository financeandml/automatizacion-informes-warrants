"""Batería de regresión (A14): cifras clave de las empresas de prueba, guardadas y comparadas en cada cambio.

Sin alucinaciones: cada cifra la calcula el propio SaaS (`construir`) a partir de la SEC y se guarda junto al
filing del que sale. Una diferencia nunca se acepta sola: se revisa y, si es correcta (p. ej. un 10-Q nuevo o
una corrección verificada del normalizador), se regenera a mano con `informes-warrants regresion --actualizar`.

Solo se comparan las cifras de la SEC, que no cambian mientras no haya filings nuevos. Las que dependen del
mercado (cotización, beta, tipo libre de riesgo y, con ellas, EV, DCF y precio objetivo) cambian cada día:
se guardan como referencia, pero no se comparan.

Idea de edgartools `RenderedStatement.to_dict` (instantánea serializable de los estados); el resto es propio.
"""

import json
import math
from pathlib import Path

from ..calculo.normalizador import LTM

EMPRESAS = ("AAPL", "IOVA", "ORCL", "NFLX", "MSFT", "JNJ", "KO", "TSLA", "XOM", "RIVN",
            "JPM", "TRV", "O", "ARCC")  # las cuatro últimas, una por plantilla sectorial (B2)
CARPETA = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "regresion"
TOLERANCIA = 1e-9  # relativa: las cifras de la SEC deben salir idénticas
PARTIDAS_LTM = ("ingresos", "resultado_operativo", "beneficio_neto", "bpa_diluido", "acciones_diluidas", "caja", "deuda_cp",
                "deuda_lp", "patrimonio", "flujo_operativo", "capex")
FUNDAMENTALES = ("ebitda", "fcf", "fcf_tras_sbc", "dfn", "deuda_neta_ajustada")


def _sin_nan(x):
    return None if isinstance(x, float) and math.isnan(x) else x


def _sectorial(c: dict) -> dict:
    """Plantillas sectoriales (B2): partidas y métricas del perfil de cada ejercicio y del LTM."""
    def resultado(r):
        return None if r is None else {"datos": {k: d.valor for k, d in r.datos.items()},
                                       "metricas": {k: _sin_nan(v) for k, v in r.metricas.items()}}

    return {"perfil": c["perfil"], "anuales": {str(a): resultado(r) for a, r in c["historico"].items()}, "ltm": resultado(c["ltm"]),
            "acciones": c["mercado"].acciones,
            "calidad": {"nivel": str(c["calidad"].nivel), "errores": list(c["calidad"].errores), "avisos": list(c["calidad"].avisos)}}


def cifras_clave(c: dict) -> dict:
    """Instantánea de un informe construido: cifras de la SEC (se comparan) y de mercado (solo referencia)."""
    if c.get("perfil"):
        mercado = {"cotizacion": c["cotizacion"].precio, "precio_modelo": c["precio_modelo"], "precio_objetivo": c["precio_objetivo"]}
        origen = {"filing": c["filing"]["accession"], "ultimo_periodico": c["filing"].get("ultimo_periodico"),
                  "fecha_ltm": c.get("fecha_ltm"), "fecha": c["fecha"]}
        return json.loads(json.dumps({"ticker": c["ticker"], "origen": origen, "sec": _sectorial(c), "mercado_referencia": mercado},
                                     ensure_ascii=False, default=str))
    e = c["estados_ltm"]  # sin 10-Q utilizable, el contexto ya trae el último ejercicio con la clave LTM
    sec = {
        "ltm": {p: e.valor(p, LTM) for p in PARTIDAS_LTM},
        "fundamentales_ltm": {k: c["fund_ltm"].get(k) for k in FUNDAMENTALES},
        "acciones_del_dcf": c["datos_dcf"]["acciones"],
        "anuales": {str(a): {p: c["estados"].valor(p, a) for p in ("ingresos", "resultado_operativo", "beneficio_neto")}
                    for a in c["ejercicios"]},
        "segmentos": {eje: {"ejercicios": d.ejercicios, "miembros": sorted(d.miembros)} for eje, d in c["segmentos"].items()},
        "trimestres": [{"fin": str(t["fin"]), "ingresos": t["ingresos"], "bpa": t["bpa"]} for t in c["trimestres"]],
        "calidad": {"nivel": str(c["calidad"].nivel), "errores": list(c["calidad"].errores), "avisos": list(c["calidad"].avisos)},
    }
    mercado = {"cotizacion": c["cotizacion"].precio, "valor_dcf": c["valor_dcf"], "precio_objetivo": c["precio_objetivo"]}
    origen = {"filing": c["filing"]["accession"], "ultimo_periodico": c["filing"].get("ultimo_periodico"),
              "fecha_ltm": c.get("fecha_ltm"), "fecha": c["fecha"]}
    # Ida y vuelta por JSON: la instantánea recién calculada y la guardada tienen los mismos tipos (listas, textos)
    return json.loads(json.dumps({"ticker": c["ticker"], "origen": origen, "sec": sec, "mercado_referencia": mercado},
                                 ensure_ascii=False, default=str))


def _iguales(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=TOLERANCIA, abs_tol=1e-9)
    return a == b


def diferencias(antes: dict, ahora: dict, ruta: str = "") -> list[str]:
    """Diferencias de las cifras de la SEC entre dos instantáneas (vacía = todo igual)."""
    if isinstance(antes, dict) and isinstance(ahora, dict):
        salida = []
        for k in sorted(set(antes) | set(ahora)):
            salida += diferencias(antes.get(k), ahora.get(k), f"{ruta}.{k}" if ruta else k)
        return salida
    if isinstance(antes, list) and isinstance(ahora, list) and len(antes) == len(ahora):
        salida = []
        for i, (x, y) in enumerate(zip(antes, ahora, strict=True)):
            salida += diferencias(x, y, f"{ruta}[{i}]")
        return salida
    return [] if _iguales(antes, ahora) else [f"{ruta}: {antes!r} → {ahora!r}"]


def comparar(antes: dict, ahora: dict) -> dict:
    """Resultado de la comparación: si cambió el filing de origen, las diferencias son datos nuevos de la SEC."""
    nuevo_filing = (antes["origen"]["filing"], antes["origen"]["ultimo_periodico"]) != \
        (ahora["origen"]["filing"], ahora["origen"]["ultimo_periodico"])
    return {"ticker": ahora["ticker"], "nuevo_filing": nuevo_filing, "diferencias": diferencias(antes["sec"], ahora["sec"])}


def ruta(ticker: str, carpeta: Path = CARPETA) -> Path:
    return carpeta / f"{ticker.upper()}.json"


def guardar(instantanea: dict, carpeta: Path = CARPETA) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = ruta(instantanea["ticker"], carpeta)
    destino.write_text(json.dumps(instantanea, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    return destino


def cargar(ticker: str, carpeta: Path = CARPETA) -> dict | None:
    try:
        return json.loads(ruta(ticker, carpeta).read_text(encoding="utf-8"))
    except OSError:
        return None
