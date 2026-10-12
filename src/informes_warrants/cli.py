"""Línea de comandos: `informes-warrants <comando> ...` (ver `informes-warrants -h`)."""

import argparse
import logging
import sys

from .config import configurar_identidad


def _datos(args) -> None:
    from .ingesta.estados import obtener_datos

    datos = obtener_datos(args.ticker)
    print(f"{datos.nombre} ({datos.ticker}) — CIK {datos.cik}\n")
    for estado in (datos.resultados, datos.balance, datos.flujos_caja):
        print(estado, end="\n\n")


def _cobertura(args) -> None:
    from .informe.cobertura import cobertura_de

    print(cobertura_de(args.ticker).motivo)


def _informe(args) -> None:
    from pathlib import Path

    from .config import directorio_datos
    from .informe import render
    from .informe.construir import construir

    lista = [x.strip().upper() for x in args.comparables.split(",") if x.strip()] if args.comparables else None
    c = construir(args.ticker, con_ia=not args.sin_ia, comparables=lista)
    carpeta = Path(args.salida) if args.salida else directorio_datos() / "informes"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = render.pdf(c, carpeta / f"{c['ticker']}_FY{c['filing']['ejercicio']}_borrador.pdf")
    print(f"Borrador: {destino}")
    print(f"Calidad de los datos: {c['calidad'].nivel}" + (f" ({'; '.join(c['calidad'].errores + c['calidad'].avisos)})"
                                                             if c["calidad"].errores or c["calidad"].avisos else ""))
    if c["precio_objetivo"] is None:
        print(f"Propuesta: {c['recomendacion']} (sin DCF ni comparables: valoración pendiente del analista)")
    else:
        print(f"Propuesta: {c['recomendacion']} · precio objetivo {c['precio_objetivo']:,.2f} USD · potencial {c['potencial']:+.1%}"
              f" (DCF por escenarios {c['valor_dcf'] or 0:,.2f} · múltiplos "
              + (f"{c['valor_multiplos']:,.2f}" if c["valor_multiplos"] is not None else "n.d.") + ")")
    print(f"Comparables: {', '.join(x['ticker'] for x in c['comparables']) or 'ninguno'} ({c['comparables_criterio']})")
    if not c["comparables_del_analista"]:
        print("IMPORTANTE: la lista de comparables es una propuesta automática y no entra en el precio objetivo. "
              "Introduce la tuya para completar la valoración: informes-warrants informe "
              f"{c['ticker']} --comparables A,B,C")
    print(f"Apartados pendientes del analista: {len(c['pendientes'])}")


def _metricas(args) -> None:
    import math

    from edgar import Company

    from .calculo.sectoriales import calcular
    from .informe.cobertura import cobertura_de
    from .informe.perfiles import PERFILES_SECTORIALES

    cobertura = cobertura_de(args.ticker)
    print(cobertura.motivo)
    perfil = next((p for p in PERFILES_SECTORIALES if p.id == cobertura.plantilla), None)
    if not perfil:
        print("Las métricas de la plantilla general llegan con la capa 2 (fase 2 del plan).")
        return
    r = calcular(perfil, Company(args.ticker).get_facts())
    print(f"Ejercicio fiscal {r.ejercicio} · validado: {'sí' if r.completo else 'no'}")
    for m in perfil.metricas:
        v = r.metricas[m.id]
        print(f"  {m.nombre:42} {'n.d. (analista)' if math.isnan(v) else f'{v:,.4f}'}")
    for nombre, d in r.datos.items():
        if d.concepto:
            print(f"    {nombre:26} {d.concepto} · FY{d.ejercicio} · {d.accession}")


def _riesgos(args) -> None:
    from .ia.bloques import riesgos_principales
    from .ingesta.riesgos import riesgos_anuales

    titulos, texto, accession = riesgos_anuales(args.ticker)
    print(f"{len(titulos)} factores de riesgo en el informe anual {accession}.")
    if not titulos:
        print("La empresa remite sus riesgos a un anexo: el bloque queda marcado para el analista.")
        return
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
    logging.basicConfig(level=logging.WARNING, format="Aviso: %(message)s")
    parser = argparse.ArgumentParser(prog="informes-warrants", description="Informes de empresas cotizadas en EEUU")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("datos", help="Estados financieros del último 10-K")
    p.add_argument("ticker")
    p.set_defaults(func=_datos, sec=True)

    p = sub.add_parser("cobertura", help="¿Plantilla general o pendiente de validar?")
    p.add_argument("ticker")
    p.set_defaults(func=_cobertura, sec=True)

    p = sub.add_parser("informe", help="Genera el borrador del informe en PDF (y su vista previa HTML)")
    p.add_argument("ticker")
    p.add_argument("--sin-ia", action="store_true", help="Sin modelo de lenguaje (el bloque de riesgos queda para el analista)")
    p.add_argument("--salida", help="Carpeta de destino (por defecto, la carpeta de datos del usuario)")
    p.add_argument("--comparables", help="Lista del analista separada por comas (p. ej. MSFT,GOOGL,DELL); sin ella, propuesta por SIC")
    p.set_defaults(func=_informe, sec=True)

    p = sub.add_parser("metricas", help="Métricas del perfil sectorial con su fuente XBRL")
    p.add_argument("ticker")
    p.set_defaults(func=_metricas, sec=True)

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
    try:
        args.func(args)
    except ValueError as e:  # errores de datos o de uso con mensaje claro (p. ej. plantilla sectorial sin PDF)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
