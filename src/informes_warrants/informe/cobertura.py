"""Qué plantilla usa cada empresa y si está validada.

- General: empresas operativas, holdings y gestoras (`Operating Company`, `Holding Company`,
  `Investment Manager`).
- Sectorial (informe/perfiles.py): banca, seguros, REIT, BDC y fondos cerrados. Mismos bloques
  de texto; cambian las métricas y la valoración. Validadas contra empresas reales (tests/test_red.py).
- Emisores extranjeros (20-F/40-F): la plantilla de su categoría, con los textos del 20-F
  (`TwentyF`) y las cifras convertidas a USD (ingesta/divisas.py).
- Resto (SPAC, ETF, fondos abiertos, categoría desconocida): «plantilla pendiente de validar».
"""

from dataclasses import dataclass

from .perfiles import perfil_de

PLANTILLA_GENERAL = "general"
PENDIENTE_VALIDAR = "pendiente de validar"

CATEGORIAS_GENERALES = {"Operating Company", "Holding Company", "Investment Manager"}
NOMBRES = {  # BusinessCategory de edgartools → español
    "Operating Company": "Empresa operativa", "Holding Company": "Holding", "Investment Manager": "Gestora de activos",
    "Bank": "Banco", "Credit Agency": "Entidad de crédito", "Insurance Company": "Aseguradora", "REIT": "REIT",
    "BDC": "BDC", "Closed-End Fund": "Fondo cerrado", "Mutual Fund": "Fondo de inversión", "ETF": "ETF", "SPAC": "SPAC",
    "Unknown": "Categoría desconocida",
}


@dataclass(frozen=True)
class Cobertura:
    plantilla: str  # "general", id de un perfil sectorial o PENDIENTE_VALIDAR
    extranjera: bool
    motivo: str

    @property
    def validada(self) -> bool:
        return self.plantilla != PENDIENTE_VALIDAR


def clasificar(categoria: str, es_extranjera: bool) -> Cobertura:
    """Clasifica una empresa a partir de su categoría de negocio de edgartools."""
    extra = " · emisor extranjero: textos del 20-F y cifras en USD" if es_extranjera else ""
    nombre = NOMBRES.get(categoria, categoria)
    if categoria in CATEGORIAS_GENERALES:
        return Cobertura(PLANTILLA_GENERAL, es_extranjera, f"{nombre}: plantilla general{extra}")
    perfil = perfil_de(categoria)
    if perfil:
        return Cobertura(perfil.id, es_extranjera, f"{nombre}: plantilla sectorial «{perfil.nombre}»{extra}")
    return Cobertura(PENDIENTE_VALIDAR, es_extranjera, f"{nombre}: plantilla pendiente de validar{extra}")


def cobertura_de(ticker: str) -> Cobertura:
    """Clasifica un ticker consultando la SEC (requiere EDGAR_IDENTITY)."""
    from edgar import Company

    empresa = Company(ticker)
    return clasificar(str(empresa.business_category), bool(empresa.is_foreign))
