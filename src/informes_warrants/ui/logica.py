"""Lógica de la interfaz (A12), sin Streamlit: se prueba sin conexión y sin navegador.

La interfaz reúne una vez los datos de la SEC y del mercado (`versionado.datos_de_la_version`, con red) y, en cada
cambio del analista, recompone el informe sin red (`componer`): la vista previa HTML tarda lo que tardan el modelo
y los gráficos, no la descarga. Las cifras las sigue calculando solo `calculo/`.
"""

from dataclasses import asdict, fields, replace

from ..informe import versionado
from ..informe.estimaciones import Estimaciones

# Estimaciones que la interfaz presenta en porcentaje (se guardan en tanto por uno)
PORCENTAJES = {"da_sobre_ventas", "capex_sobre_ventas", "circulante_sobre_ventas", "tasa_fiscal", "rf", "erp", "coste_deuda",
               "g", "resultado_financiero_sobre_ventas", "cuota_minoritarios", "variacion_acciones", "payout", "sbc_sobre_ventas",
               "recompras_sobre_fcf", "rentabilidad_sostenible"}
ETIQUETAS = {
    "da_sobre_ventas": "D&A / ventas", "capex_sobre_ventas": "Capex / ventas", "circulante_sobre_ventas": "Circulante / ventas",
    "tasa_fiscal": "Tasa fiscal", "rf": "Tipo libre de riesgo", "erp": "Prima de riesgo", "beta": "Beta",
    "coste_deuda": "Coste de la deuda (antes de impuestos)", "g": "Crecimiento a perpetuidad (g)",
    "anios_convergencia": "Años de convergencia hacia g", "resultado_financiero_sobre_ventas": "Resultado financiero / ventas",
    "cuota_minoritarios": "Cuota de minoritarios", "variacion_acciones": "Variación anual de las acciones", "payout": "Pay-out",
    "sbc_sobre_ventas": "Remuneración en acciones / ventas", "recompras_sobre_fcf": "Recompras / FCF tras SBC",
    "precio_objetivo_analista": "Precio objetivo del analista (USD; vacío = el del modelo)",
    "rentabilidad_sostenible": "ROE (ROTE, NII) sostenible (%; vacío = media de los ejercicios)",
}
OPCIONALES = {"precio_objetivo_analista", "rentabilidad_sostenible"}  # vacío = el valor del modelo
# Banca, seguros, REIT y BDC (B2): sin DCF; la rentabilidad sostenible solo existe en ellos
ESCALARES_SECTORIALES = ("rf", "erp", "beta", "g", "rentabilidad_sostenible", "precio_objetivo_analista")
ESCALARES = tuple(f.name for f in fields(Estimaciones) if f.name in ETIQUETAS and f.name != "rentabilidad_sostenible")


def escalares(c: dict) -> tuple[str, ...]:
    """Supuestos editables del informe: los del DCF solo en la plantilla general."""
    return ESCALARES_SECTORIALES if c.get("perfil") else ESCALARES


def a_pantalla(nombre: str, valor):
    """Valor tal como se edita: los porcentajes, ×100."""
    return None if valor is None else valor * 100 if nombre in PORCENTAJES else valor


def de_pantalla(nombre: str, valor):
    return None if valor is None else valor / 100 if nombre in PORCENTAJES else valor


def editar(base: Estimaciones, **cambios) -> tuple[Estimaciones, list[str]]:
    """Estimaciones con los cambios del analista y sus errores de validación (lista vacía = válidas)."""
    nuevas = replace(base, **{k: v for k, v in cambios.items() if k in {f.name for f in fields(Estimaciones)}})
    return nuevas, nuevas.validar()


recomponer = versionado.recomponer  # la misma recomposición que al guardar la versión


def motivos_para_no_emitir(c: dict) -> list[str]:
    """Lo que impide emitir (vacío = se puede): estimaciones o escenarios no válidos y calidad en rojo. Los apartados
    pendientes del analista no impiden emitir (decisión del usuario, 2026-10-14): son avisos (`pendientes_aviso`)."""
    motivos = [f"Estimaciones: {e}" for e in c["estimaciones"].validar()]
    motivos += [f"Escenarios: {e}" for e in (c["escenarios"].validar() if c["escenarios"] is not None else [])]
    if str(c["calidad"].nivel) == "rojo":
        motivos += [f"Calidad de los datos: {e}" for e in c["calidad"].errores]
    return motivos


def pendientes_aviso(c: dict) -> list[str]:
    """Apartados del analista aún por completar o revisar: se muestran antes de emitir, sin bloquear."""
    return [f"Pendiente del analista: {p}" for p in c["pendientes"]]


def contenido_editable(c: dict) -> dict:
    """Lo que la versión guarda del analista (se hereda en la siguiente)."""
    return {"textos": dict(c["textos"]), "estimaciones": asdict(c["estimaciones"])}


CLAVES_MOTOR = ("crecimientos", "margenes", "pct_perpetuidad", "convencion", "lbo")


def entradas_motor(c: dict):
    """(entradas con las que se calculó el modelo, valores por defecto del motor); (None, None) sin modelo."""
    from ..informe import motor

    m = c.get("motor") or {}
    if not m.get("datos"):
        return None, None
    return motor.entradas(m["datos"], c["estimaciones"]), motor.entradas(m["datos"], replace(c["estimaciones"], motor={}))


def motor_revisado(est: Estimaciones) -> bool:
    return set(est.motor or {}) >= set(CLAVES_MOTOR)


def motor_del_analista(defecto, crecimientos: dict, margenes: dict, pct_perpetuidad: float, convencion: int, lbo: bool,
                       revisado: bool) -> dict:
    """Entradas del motor que guarda la versión (`Estimaciones.motor`): todas si el analista las da por revisadas; si
    no, solo las que cambió (las demás siguen siendo las del motor, marcadas «Revisar» en el libro)."""
    nuevo = {"crecimientos": crecimientos, "margenes": margenes, "pct_perpetuidad": pct_perpetuidad, "convencion": convencion, "lbo": lbo}
    if revisado:
        return nuevo
    propio = {}
    for k in ("crecimientos", "margenes"):
        cambiados = {s: v for s, v in nuevo[k].items()
                     if [round(x, 6) for x in v] != [round(x, 6) for x in getattr(defecto, k).get(s, [])]}
        if cambiados:
            propio[k] = cambiados
    propio |= {k: nuevo[k] for k in ("pct_perpetuidad", "convencion", "lbo") if nuevo[k] != getattr(defecto, k)}
    return propio


def libro_del_motor(c: dict) -> bytes | None:
    """El .xlsx del modelo (general o sectorial) en memoria, para el botón de descarga."""
    import io

    modelo = (c.get("motor") or {}).get("modelo")
    if modelo is None:
        return None
    buffer = io.BytesIO()
    modelo.libro.guardar(buffer)
    return buffer.getvalue()


def comparacion(anterior, actual) -> dict:
    """Qué cambió entre dos versiones (B9): textos (diff), estimaciones y recomendación (almacenamiento/versiones.comparar)
    y la atribución del cambio del valor DCF a cada grupo de supuestos (R16, informe/cambios.comparar)."""
    from ..almacenamiento.versiones import comparar as comparar_versiones
    from ..informe.cambios import comparar as comparar_resumenes

    salida = comparar_versiones(anterior, actual)
    a, b = anterior.contenido.get("resumen"), actual.contenido.get("resumen")
    salida["valoracion"] = comparar_resumenes(a, b) if a and b else None
    return salida
