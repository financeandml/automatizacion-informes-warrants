"""Únicos ajustes que el analista puede hacer sobre el bloque fijo.

El bloque fijo (tablas, múltiplos y gráficos) lo genera el código y no se edita. Solo hay dos
decisiones que el SaaS no puede tomar con datos de la SEC; ambas exigen justificación y quedan
visibles en el informe. Lo descartado y por qué está en docs/editor-y-versiones.md.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AjusteComparable:
    """Quitar o añadir un comparable a la lista propuesta por SIC y tamaño."""

    ticker: str
    accion: str  # "quitar" | "añadir"
    motivo: str


@dataclass(frozen=True)
class PartidaNoRecurrente:
    """Partida del P&L que el analista excluye del EBITDA recurrente."""

    concepto_xbrl: str
    ejercicio: str
    importe: float  # USD Mn, con su signo en el P&L
    motivo: str


@dataclass
class AjustesBloqueFijo:
    comparables: list[AjusteComparable] = field(default_factory=list)
    no_recurrentes: list[PartidaNoRecurrente] = field(default_factory=list)

    def validar(self) -> list[str]:
        errores = []
        for a in self.comparables:
            if a.accion not in ("quitar", "añadir"):
                errores.append(f"Acción no válida para {a.ticker}: {a.accion}")
            if not a.motivo.strip():
                errores.append(f"Falta el motivo del ajuste del comparable {a.ticker}.")
        for p in self.no_recurrentes:
            if not p.motivo.strip():
                errores.append(f"Falta el motivo de la partida no recurrente {p.concepto_xbrl} ({p.ejercicio}).")
        return errores


def aplicar_comparables(propuestos: list[str], ajustes: list[AjusteComparable]) -> list[str]:
    """Lista final de comparables: la propuesta automática con los ajustes del analista."""
    resultado = [t for t in propuestos if t not in {a.ticker for a in ajustes if a.accion == "quitar"}]
    resultado += [a.ticker for a in ajustes if a.accion == "añadir" and a.ticker not in resultado]
    return resultado
