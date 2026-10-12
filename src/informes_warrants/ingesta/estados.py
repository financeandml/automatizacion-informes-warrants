"""Estados financieros tal como los presenta el último 10-K (comando `informes-warrants datos`).

Es una vista de consulta rápida con el renderizado de edgartools (`Company.get_financials()`), sin
normalizar. Las cifras del informe salen siempre del normalizador SEC (calculo/normalizador.py).
"""

from dataclasses import dataclass
from typing import Any

from edgar import Company


@dataclass
class DatosEmpresa:
    ticker: str
    nombre: str
    cik: int
    balance: Any
    resultados: Any
    flujos_caja: Any


def obtener_datos(ticker: str) -> DatosEmpresa:
    """Descarga los estados financieros del último 10-K de la empresa."""
    empresa = Company(ticker)
    financieros = empresa.get_financials()
    if financieros is None:
        raise ValueError(f"No se encontraron estados financieros para {ticker}")

    return DatosEmpresa(
        ticker=ticker.upper(),
        nombre=empresa.name,
        cik=empresa.cik,
        balance=financieros.balance_sheet(),
        resultados=financieros.income_statement(),
        flujos_caja=financieros.cash_flow_statement(),
    )
