"""Cálculo de las métricas de un perfil sectorial con trazabilidad (concepto, año fiscal, accession)."""

import logging
import math
import warnings
from dataclasses import dataclass

from ..informe.perfiles import Perfil


@dataclass(frozen=True)
class Dato:
    valor: float
    concepto: str | None  # None si la entrada es opcional y la empresa no la declara (vale 0)
    ejercicio: int | None
    accession: str | None


@dataclass(frozen=True)
class Resultado:
    ejercicio: int | None
    datos: dict[str, Dato]
    metricas: dict[str, float]
    faltan: list[str]  # entradas obligatorias que la empresa no declara
    esenciales: tuple[str, ...] = ()

    @property
    def completo(self) -> bool:
        """Todas las métricas esenciales calculadas."""
        return all(not math.isnan(self.metricas[m]) for m in self.esenciales)

    @property
    def para_el_analista(self) -> list[str]:
        """Métricas secundarias que la empresa no declara en XBRL estándar (n.d. + marcador)."""
        return [m for m, v in self.metricas.items() if m not in self.esenciales and math.isnan(v)]


def _hecho(facts, conceptos: tuple[str, ...], ejercicio: int | None):
    for concepto in conceptos:
        with warnings.catch_warnings():  # edgartools avisa de cada concepto que la empresa no declara
            warnings.simplefilter("ignore")
            nivel = logging.root.manager.disable
            logging.disable(logging.WARNING)
            try:
                hecho = facts.get_annual_fact(concepto, ejercicio)
            finally:
                logging.disable(nivel)
        if hecho is not None and getattr(hecho, "numeric_value", None) is not None:
            return concepto, hecho
    return None, None


def calcular(perfil: Perfil, facts, ejercicio: int | None = None) -> Resultado:
    """Métricas del perfil para un ejercicio (por defecto, el último con beneficio declarado).

    `facts` es un `EntityFacts` de edgartools (`Company(ticker).get_facts()`).
    """
    if ejercicio is None:
        _, ref = _hecho(facts, perfil.entradas["beneficio"].conceptos, None)
        ejercicio = getattr(ref, "fiscal_year", None)
    datos, faltan = {}, []
    for nombre, entrada in perfil.entradas.items():
        concepto, hecho = _hecho(facts, entrada.conceptos, ejercicio)
        if hecho is not None:
            datos[nombre] = Dato(float(hecho.numeric_value), concepto, getattr(hecho, "fiscal_year", None),
                                 getattr(hecho, "accession", None))
        elif entrada.opcional:
            datos[nombre] = Dato(0.0, None, None, None)
        else:
            faltan.append(nombre)
    valores = {k: d.valor for k, d in datos.items()}
    metricas = {}
    for m in perfil.metricas:
        try:
            metricas[m.id] = float(m.formula(valores))
        except KeyError:
            metricas[m.id] = float("nan")
    return Resultado(ejercicio, datos, metricas, faltan, tuple(m.id for m in perfil.metricas if m.esencial))
