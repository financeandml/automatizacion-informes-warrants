"""Parámetros del fondo (B4): los pone el analista bajo su responsabilidad (decisión del usuario, 2026-10-12).

Uso interno del SaaS: se guardan en la carpeta de datos del usuario (`parametros.json`, fuera del repositorio) y se
editan en la pantalla «Configuración» de la interfaz. Un parámetro vacío no se evalúa (nunca se inventa un umbral).
Sin ninguno definido, la gestión de la posición no sale en el informe y el SaaS lo avisa antes de emitir.
"""

import json
from dataclasses import asdict, dataclass, fields


@dataclass
class ParametrosFondo:
    # Criterios de valoración del fondo (apartado 12) y checklist de entrada (23)
    potencial_minimo: float | None = None  # tanto por uno
    per_maximo: float | None = None
    ev_ebitda_maximo: float | None = None
    deuda_neta_ebitda_maxima: float | None = None
    roic_minimo: float | None = None
    crecimiento_minimo: float | None = None
    # Gestión del riesgo (apartado 24)
    capital_cartera: float | None = None  # USD
    riesgo_por_posicion: float | None = None  # pérdida máxima hasta el stop, sobre la cartera (tanto por uno)
    peso_maximo: float | None = None  # peso máximo de una posición en la cartera
    multiplo_volatilidad: float | None = None  # k del stop: k × volatilidad diaria × √horizonte
    horizonte_stop_dias: int | None = None
    perdida_minima_stop: float | None = None  # el stop no se pone más cerca (idea de stock-screener: 3 %)
    perdida_maxima_stop: float | None = None  # ni más lejos (stock-screener: 10 %)
    participacion_maxima_volumen: float | None = None  # parte del volumen medio diario que se puede negociar

    @property
    def definidos(self) -> bool:
        return any(getattr(self, f.name) is not None for f in fields(self))


def _ruta():
    from ..config import directorio_datos

    return directorio_datos() / "parametros.json"


def cargar() -> ParametrosFondo:
    try:
        datos = json.loads(_ruta().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ParametrosFondo()
    validos = {f.name for f in fields(ParametrosFondo)}
    return ParametrosFondo(**{k: v for k, v in datos.items() if k in validos})


def guardar(parametros: ParametrosFondo) -> None:
    ruta = _ruta()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(asdict(parametros), ensure_ascii=False, indent=2), encoding="utf-8")
