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
               "recompras_sobre_fcf"}
ETIQUETAS = {
    "da_sobre_ventas": "D&A / ventas", "capex_sobre_ventas": "Capex / ventas", "circulante_sobre_ventas": "Circulante / ventas",
    "tasa_fiscal": "Tasa fiscal", "rf": "Tipo libre de riesgo", "erp": "Prima de riesgo", "beta": "Beta",
    "coste_deuda": "Coste de la deuda (antes de impuestos)", "g": "Crecimiento a perpetuidad (g)",
    "anios_convergencia": "Años de convergencia hacia g", "resultado_financiero_sobre_ventas": "Resultado financiero / ventas",
    "cuota_minoritarios": "Cuota de minoritarios", "variacion_acciones": "Variación anual de las acciones", "payout": "Pay-out",
    "sbc_sobre_ventas": "Remuneración en acciones / ventas", "recompras_sobre_fcf": "Recompras / FCF tras SBC",
    "precio_objetivo_analista": "Precio objetivo del analista (USD; vacío = el del modelo)",
}
ESCALARES = tuple(f.name for f in fields(Estimaciones) if f.name in ETIQUETAS)


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
    """Lo que impide emitir (vacío = se puede): marcadores del analista, estimaciones no válidas, calidad en rojo."""
    motivos = [f"Pendiente del analista: {p}" for p in c["pendientes"]]
    motivos += [f"Estimaciones: {e}" for e in c["estimaciones"].validar()]
    motivos += [f"Escenarios: {e}" for e in (c["escenarios"].validar() if c["escenarios"] is not None else [])]
    if str(c["calidad"].nivel) == "rojo":
        motivos += [f"Calidad de los datos: {e}" for e in c["calidad"].errores]
    return motivos


def contenido_editable(c: dict) -> dict:
    """Lo que la versión guarda del analista (se hereda en la siguiente)."""
    return {"textos": dict(c["textos"]), "estimaciones": asdict(c["estimaciones"])}
