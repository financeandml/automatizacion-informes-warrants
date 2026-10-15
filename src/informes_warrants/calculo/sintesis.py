"""Derivación del precio objetivo (R8): media ponderada de los métodos de valoración disponibles.

Patrón de FinRobot `finrobot_desktop/finrobot/engine/compute/operators/valuation_synthesis.py`
(`synthesize_valuations`: media ponderada determinista entre métodos) y `valuation_aggregator.py`
(rangos por método para el gráfico de rangos), AI4Finance Foundation, Apache-2.0. Cambios: pesos fijados
por el analista (no por «confianza»), renormalizados entre los métodos que tienen valor; cada método
lleva su rango y su supuesto clave para la tabla del informe.

  precio = Σ peso_i · valor_i / Σ peso_i   (solo métodos con valor y peso > 0)
"""

from dataclasses import dataclass

METODOS = ("DCF", "DCF por escenarios", "Comparables", "Múltiplos históricos", "Suma de partes", "DDM", "Ingreso residual")


@dataclass(frozen=True)
class Metodo:
    nombre: str
    valor: float | None  # precio por acción
    bajo: float | None  # rango (p. ej. escenario pesimista, cuartil inferior)
    alto: float | None
    supuesto: str  # texto breve del supuesto clave
    peso: float  # peso pedido por el analista
    peso_efectivo: float = 0.0


def sintetizar(metodos: list[Metodo]) -> tuple[float | None, list[Metodo]]:
    """(precio objetivo, métodos con su peso efectivo). None si ningún método con peso tiene valor."""
    usados = [m for m in metodos if m.valor is not None and m.valor > 0 and m.peso > 0]
    total = sum(m.peso for m in usados)
    if not total:
        return None, list(metodos)
    precio = sum(m.valor * m.peso for m in usados) / total
    salida = [Metodo(m.nombre, m.valor, m.bajo, m.alto, m.supuesto, m.peso, m.peso / total if m in usados else 0.0)
              for m in metodos]
    return precio, salida
