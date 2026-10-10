"""Punto de entrada de línea de comandos."""

import argparse

from .config import configurar_identidad
from .datos import obtener_datos


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera informes de empresas cotizadas en EEUU")
    parser.add_argument("ticker", help="Ticker de la empresa, p. ej. AAPL")
    args = parser.parse_args()

    configurar_identidad()
    datos = obtener_datos(args.ticker)

    print(f"{datos.nombre} ({datos.ticker}) — CIK {datos.cik}\n")
    for estado in (datos.resultados, datos.balance, datos.flujos_caja):
        print(estado)
        print()


if __name__ == "__main__":
    main()
