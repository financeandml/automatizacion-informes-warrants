"""Qué empresas cubre la plantilla general y cuáles quedan «pendientes de validar».

La plantilla general está pensada para empresas operativas que presentan 10-K. El resto
(bancos, aseguradoras, REIT, fondos, emisores extranjeros…) usa métricas distintas: EBITDA,
EV o deuda neta no aplican igual. Se clasifican con edgartools (`Company.business_category`,
`Company.is_foreign`) y se generan con la plantilla general marcada como pendiente de validar.
"""

from dataclasses import dataclass

PLANTILLA_GENERAL = "general"
PENDIENTE_VALIDAR = "pendiente de validar"

CATEGORIAS_GENERALES = {"Operating Company", "Holding Company"}


@dataclass(frozen=True)
class Cobertura:
    plantilla: str
    motivo: str

    @property
    def validada(self) -> bool:
        return self.plantilla == PLANTILLA_GENERAL


def clasificar(categoria: str, es_extranjera: bool) -> Cobertura:
    """Clasifica una empresa a partir de su categoría de negocio de edgartools."""
    if es_extranjera:
        return Cobertura(PENDIENTE_VALIDAR, "Emisor extranjero (20-F/40-F): plantilla pendiente de validar")
    if categoria in CATEGORIAS_GENERALES:
        return Cobertura(PLANTILLA_GENERAL, f"{categoria}: plantilla general")
    return Cobertura(PENDIENTE_VALIDAR, f"{categoria}: plantilla pendiente de validar")


def cobertura_de(ticker: str) -> Cobertura:
    """Clasifica un ticker consultando la SEC (requiere EDGAR_IDENTITY)."""
    from edgar import Company

    empresa = Company(ticker)
    return clasificar(str(empresa.business_category), bool(empresa.is_foreign))
