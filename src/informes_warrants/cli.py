"""Línea de comandos: `informes-warrants <comando> ...` (ver `informes-warrants -h`)."""

import argparse
import sys

from .config import configurar_identidad


def _datos(args) -> None:
    from .datos import obtener_datos

    datos = obtener_datos(args.ticker)
    print(f"{datos.nombre} ({datos.ticker}) — CIK {datos.cik}\n")
    for estado in (datos.resultados, datos.balance, datos.flujos_caja):
        print(estado, end="\n\n")


def _cobertura(args) -> None:
    from .informe.cobertura import cobertura_de

    print(cobertura_de(args.ticker).motivo)


def _riesgos(args) -> None:
    from .ia.bloques import riesgos_principales
    from .ingesta.riesgos import riesgos_del_10k

    titulos, texto, accession = riesgos_del_10k(args.ticker)
    print(f"{len(titulos)} factores de riesgo en el 10-K {accession}.")
    if args.sin_ia:
        print("\n".join(f"- {t}" for t in titulos))
        return
    elegidos, cfg = riesgos_principales(titulos, texto)
    print(f"Riesgos principales (IA: {cfg.proveedor} · {cfg.modelo}):")
    for s in elegidos:
        print(f"- {s.resumen}\n  «{s.cita}»")


def _versiones(args) -> None:
    from .almacenamiento.almacen import Almacen
    from .almacenamiento.deteccion import detectar

    almacen = Almacen()
    if args.accion == "detectar":
        nueva = detectar(args.ticker, almacen)
        print(f"Nueva versión pendiente de confirmar: {nueva.etiqueta}" if nueva else "No hay filings nuevos.")
    for v in almacen.historial(args.ticker):
        print(f"{v.etiqueta:28} {v.estado.value:10} {v.accession} ({v.fecha_filing})")
    print(f"Base de datos: {almacen.ruta}")


def _ia(args) -> None:
    from .ia.llm import completar

    respuesta, cfg = completar("Responde en una sola palabra.", "Di «listo».")
    print(f"{cfg.proveedor} · {cfg.modelo}: {respuesta}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos y «» en cualquier consola de Windows (también en la ayuda)
    parser = argparse.ArgumentParser(prog="informes-warrants", description="Informes de empresas cotizadas en EEUU")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("datos", help="Estados financieros del último 10-K")
    p.add_argument("ticker")
    p.set_defaults(func=_datos, sec=True)

    p = sub.add_parser("cobertura", help="¿Plantilla general o pendiente de validar?")
    p.add_argument("ticker")
    p.set_defaults(func=_cobertura, sec=True)

    p = sub.add_parser("riesgos", help="Factores de riesgo del 10-K y los 5 principales (IA)")
    p.add_argument("ticker")
    p.add_argument("--sin-ia", action="store_true", help="Solo la lista literal, sin modelo de lenguaje")
    p.set_defaults(func=_riesgos, sec=True)

    p = sub.add_parser("versiones", help="Historial de versiones y detección de 10-Q/10-K nuevos")
    p.add_argument("accion", choices=["lista", "detectar"])
    p.add_argument("ticker")
    p.set_defaults(func=_versiones, sec=True)

    p = sub.add_parser("ia", help="Comprueba la conexión con el modelo de lenguaje")
    p.set_defaults(func=_ia, sec=False)

    args = parser.parse_args()
    if args.sec:
        configurar_identidad()
    args.func(args)


if __name__ == "__main__":
    main()
