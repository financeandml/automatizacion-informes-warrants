"""Versiones de un informe: estados, nombre, herencia y comparación.

Ciclo de vida (lo gestiona el SaaS; el analista solo confirma y emite):

    DETECTADA ──confirmar──► BORRADOR ──emitir──► EMITIDA (inmutable)
        │                       │                     │
        └──descartar──► DESCARTADA ◄──descartar──┘     └──nueva_revision──► BORRADOR (v+1)

- DETECTADA: el SaaS ha visto un 10-Q/10-K nuevo y propone la versión; espera confirmación.
- BORRADOR: en edición. EMITIDA: aprobada por el analista; ya no cambia.
- Una corrección de un informe emitido es una revisión nueva (v2, v3…) del mismo periodo.
"""

import difflib
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum

from ..informe.plantillas import pendientes


class Estado(StrEnum):
    DETECTADA = "detectada"
    BORRADOR = "borrador"
    EMITIDA = "emitida"
    DESCARTADA = "descartada"


class TransicionInvalida(RuntimeError):
    pass


# Lo que el analista aporta y se hereda entre versiones. Lo demás (bloques AUTO, PLANTILLA e IA)
# se regenera desde el filing nuevo para que nunca arrastre cifras antiguas.
CLAVES_HEREDABLES = ("textos", "estimaciones", "ajustes", "recomendacion")


def _ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Version:
    ticker: str
    ejercicio: int  # año fiscal de la empresa (dei:DocumentFiscalYearFocus)
    periodo: str  # "FY", "Q1", "Q2" o "Q3" (dei:DocumentFiscalPeriodFocus)
    revision: int
    accession: str
    fecha_filing: str
    estado: Estado = Estado.DETECTADA
    contenido: dict = field(default_factory=dict)
    creada: str = field(default_factory=_ahora)
    emitida: str | None = None

    @property
    def etiqueta(self) -> str:
        periodo = "" if self.periodo == "FY" else f" {self.periodo}"
        return f"{self.ticker} · FY{self.ejercicio}{periodo} · v{self.revision}"

    def pendientes(self) -> list[str]:
        """Marcadores [[ANALISTA: …]] sin completar en los textos."""
        return [p for texto in self.contenido.get("textos", {}).values() for p in pendientes(texto)]

    def avisos(self) -> list[str]:
        """Avisos que el SaaS muestra antes de emitir (p. ej. comparables automáticos): no bloquean la emisión."""
        return list(self.contenido.get("avisos_emision", []))

    def confirmar(self) -> "Version":
        self._exigir(Estado.DETECTADA, "confirmar")
        return replace(self, estado=Estado.BORRADOR)

    def descartar(self) -> "Version":
        if self.estado not in (Estado.DETECTADA, Estado.BORRADOR):
            raise TransicionInvalida(f"No se puede descartar una versión {self.estado.value}.")
        return replace(self, estado=Estado.DESCARTADA)

    def emitir(self) -> "Version":
        self._exigir(Estado.BORRADOR, "emitir")
        faltan = self.pendientes()
        if faltan:
            raise TransicionInvalida(f"Quedan {len(faltan)} apartados del analista sin completar.")
        return replace(self, estado=Estado.EMITIDA, emitida=_ahora())

    def nueva_revision(self) -> "Version":
        self._exigir(Estado.EMITIDA, "revisar")
        return replace(self, revision=self.revision + 1, estado=Estado.BORRADOR,
                       contenido=heredar(self.contenido), creada=_ahora(), emitida=None)

    def _exigir(self, estado: Estado, accion: str) -> None:
        if self.estado != estado:
            raise TransicionInvalida(f"Solo se puede {accion} una versión {estado.value} (está {self.estado.value}).")


def heredar(contenido_anterior: dict) -> dict:
    """Contenido inicial de una versión nueva: solo lo que aportó el analista."""
    import copy

    return {k: copy.deepcopy(contenido_anterior[k]) for k in CLAVES_HEREDABLES if k in contenido_anterior}


def comparar(anterior: Version, actual: Version) -> dict:
    """Diferencias entre dos versiones: textos (diff), estimaciones y métricas clave."""
    a, b = anterior.contenido, actual.contenido
    textos = {}
    for bloque in sorted(set(a.get("textos", {})) | set(b.get("textos", {}))):
        antes, despues = a.get("textos", {}).get(bloque, ""), b.get("textos", {}).get(bloque, "")
        if antes != despues:
            textos[bloque] = "\n".join(difflib.unified_diff(
                antes.splitlines(), despues.splitlines(), anterior.etiqueta, actual.etiqueta, lineterm=""))

    def cambios(clave: str) -> dict:
        x, y = a.get(clave, {}), b.get(clave, {})
        return {k: (x.get(k), y.get(k)) for k in sorted(set(x) | set(y)) if x.get(k) != y.get(k)}

    return {"textos": textos, "estimaciones": cambios("estimaciones"), "metricas": cambios("metricas"),
            "recomendacion": (a.get("recomendacion"), b.get("recomendacion"))}
