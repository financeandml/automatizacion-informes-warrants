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
    import json
    from pathlib import Path

    from .almacenamiento.almacen import Almacen
    from .almacenamiento.versiones import Estado
    from .config import directorio_datos
    from .informe import render
    from .informe.cambios import resumen
    from .informe.construir import construir
    from .informe.motor import exportar

    lista = [x.strip().upper() for x in args.comparables.split(",") if x.strip()] if args.comparables else None
    anterior = json.loads(Path(args.comparar_con).read_text(encoding="utf-8")) if args.comparar_con else None
    emitidas = [v.contenido["resumen"] for v in Almacen().historial(args.ticker.upper())
                if v.estado == Estado.EMITIDA and v.contenido.get("resumen")]  # R17: historial de las versiones emitidas
    c = construir(args.ticker, con_ia=not args.sin_ia, comparables=lista, anterior=anterior, historial_resumenes=emitidas)
    carpeta = Path(args.salida) if args.salida else directorio_datos() / "informes"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = render.pdf(c, carpeta / f"{c['ticker']}_FY{c['filing']['ejercicio']}_borrador.pdf")
    modelo_xlsx, avisos_modelo = exportar(c, destino)  # B1: libro del motor junto al PDF, contrastado con LibreOffice
    c["avisos_emision"] += avisos_modelo
    ruta_resumen = destino.with_name(destino.stem + "_resumen.json")  # R16: el siguiente informe se compara con este
    ruta_resumen.write_text(json.dumps(resumen(c), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"Borrador: {destino}")
    if modelo_xlsx:
        print(f"Modelo de valoración (Excel, fórmulas vivas): {modelo_xlsx}")
    print(f"Resumen para comparar con el próximo informe: {ruta_resumen}")
    print(f"Calidad de los datos: {c['calidad'].nivel}" + (f" ({'; '.join(c['calidad'].errores + c['calidad'].avisos)})"
                                                             if c["calidad"].errores or c["calidad"].avisos else ""))
    if c["precio_objetivo"] is None:
        print(f"Propuesta: {c['recomendacion']} (ningún método con valor: valoración pendiente del analista)")
    elif c.get("perfil"):  # plantilla sectorial (B2): sin DCF
        print(f"Propuesta: {c['recomendacion']} · precio objetivo {c['precio_objetivo']:,.2f} USD · potencial {c['potencial']:+.1%} ("
              + "; ".join(f"{m.nombre} {m.valor:,.2f}" for m in c["metodos"] if m.valor is not None) + ")")
    else:
        print(f"Propuesta: {c['recomendacion']} · precio objetivo {c['precio_objetivo']:,.2f} USD · potencial {c['potencial']:+.1%}"
              f" (DCF {c['valor_dcf'] or 0:,.2f} · DCF por escenarios {c['valor_dcf_escenarios'] or 0:,.2f} · múltiplos "
              + (f"{c['valor_multiplos']:,.2f}" if c["valor_multiplos"] is not None else "n.d.") + ")")
    print(f"Comparables: {', '.join(x['ticker'] for x in c['comparables']) or 'ninguno'} ({c['comparables_criterio']})")
    from .informe.construir import AVISO_COMPARABLES

    for aviso in c["avisos_emision"]:  # internos del SaaS: no salen en el informe
        pista = f" (informes-warrants informe {c['ticker']} --comparables A,B,C)" if aviso == AVISO_COMPARABLES else ""
        print(f"Aviso antes de emitir: {aviso}{pista}")
    print(f"Apartados pendientes del analista: {len(c['pendientes'])}")


def _modelo(args) -> None:
    """Solo el libro del motor de valoración (sin PDF ni IA), contrastado con LibreOffice."""
    from pathlib import Path

    from .config import directorio_datos
    from .informe.construir import construir
    from .informe.motor import exportar

    lista = [x.strip().upper() for x in args.comparables.split(",") if x.strip()] if args.comparables else None
    c = construir(args.ticker, con_ia=False, comparables=lista)
    carpeta = Path(args.salida) if args.salida else directorio_datos() / "informes"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta, avisos = exportar(c, carpeta / f"{c['ticker']}_FY{c['filing']['ejercicio']}_modelo.xlsx")
    if ruta is None:
        print(f"Sin modelo de valoración: {(c.get('motor') or {}).get('error', 'faltan las ventas o el EBIT del último ejercicio')}")
        return
    print(f"Modelo de valoración: {ruta}")
    for nombre, v in (c["motor"]["modelo"].salidas or {}).items():
        if isinstance(v, float) and not nombre.startswith("control_"):
            print(f"  {nombre:32} {v:,.4f}")
    for aviso in (c["motor"]["modelo"].avisos or []) + avisos:
        print(f"Aviso: {aviso}")


def _metricas(args) -> None:
    import math

    from edgar import Company

    from .calculo.perfiles import PERFILES_SECTORIALES
    from .calculo.sectoriales import calcular
    from .informe.cobertura import cobertura_de

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
    from .almacenamiento.versiones import TransicionInvalida
    from .informe.versionado import preparar, ultima_abierta

    almacen = Almacen()
    if args.accion == "detectar":
        nueva = detectar(args.ticker, almacen)
        print(f"Nueva versión pendiente de confirmar: {nueva.etiqueta}" if nueva else "No hay filings nuevos.")
    elif args.accion in ("preparar", "confirmar", "emitir"):
        v = ultima_abierta(almacen, args.ticker)
        if v is None:
            raise ValueError(f"{args.ticker.upper()} no tiene ninguna versión abierta: ejecuta antes «versiones detectar».")
        try:
            if args.accion == "preparar":
                v, c = preparar(v, almacen, con_ia=not args.sin_ia)
                print(f"{v.etiqueta}: PDF en {v.contenido['pdf']} · {len(c['pendientes'])} apartados pendientes del analista")
                for aviso in v.avisos():
                    print(f"Aviso antes de emitir: {aviso}")
            else:
                v = v.confirmar() if args.accion == "confirmar" else v.emitir()
                almacen.guardar(v)
                print(f"{v.etiqueta}: {v.estado.value}")
        except TransicionInvalida as e:
            raise ValueError(str(e)) from e
    for v in almacen.historial(args.ticker):
        print(f"{v.etiqueta:28} {v.estado.value:10} {v.accession} ({v.fecha_filing})")
    print(f"Base de datos: {almacen.ruta}")


def _interfaz(args) -> None:
    import subprocess
    from pathlib import Path

    app = Path(__file__).parent / "ui" / "app.py"
    tema = ["--theme.base=light", "--theme.primaryColor=#2B0B02", "--theme.backgroundColor=#FFFFFF",
            "--theme.secondaryBackgroundColor=#FFFFFF", "--theme.textColor=#000000",  # los tres colores de la marca
            "--theme.borderColor=#2B0B02", "--theme.showWidgetBorder=true"]  # con fondo blanco, los campos necesitan borde
    seguridad = ["--server.address=localhost", "--server.enableXsrfProtection=true", "--server.maxUploadSize=20"]  # C5: solo este equipo
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app), "--browser.gatherUsageStats=false", *seguridad, *tema], check=False)


def _regresion(args) -> None:
    from .informe import regresion
    from .informe.construir import construir

    fallos = 0
    for ticker in [t.upper() for t in args.tickers] or regresion.EMPRESAS:
        ahora = regresion.cifras_clave(construir(ticker, con_ia=False))
        antes = regresion.cargar(ticker)
        if antes is None or args.actualizar:
            print(f"{ticker}: instantánea {'actualizada' if antes else 'creada'} en {regresion.guardar(ahora)}")
            continue
        r = regresion.comparar(antes, ahora)
        if not r["diferencias"]:
            print(f"{ticker}: sin cambios")
            continue
        fallos += not r["nuevo_filing"]
        motivo = ("filing nuevo de la SEC: revisar y, si es correcto, --actualizar" if r["nuevo_filing"]
                  else "MISMO filing: revisar el código")
        print(f"{ticker}: {len(r['diferencias'])} diferencias ({motivo})")
        for d in r["diferencias"]:
            print(f"   {d}")
    sys.exit(1 if fallos else 0)


def _autoria(args) -> None:
    from .informe.autoria import Autoria, cargar, guardar

    actual = cargar()
    nuevos = {k: v for k, v in vars(args).items() if k in Autoria.__dataclass_fields__ and v is not None}
    if nuevos:
        guardar(Autoria(**{**vars(actual), **nuevos}))
        actual = cargar()
    for campo, valor in vars(actual).items():
        print(f"{campo:18} {valor or '—'}")


def _ia(args) -> None:
    from .ia.llm import completar

    respuesta, cfg = completar("Responde en una sola palabra.", "Di «listo».")
    print(f"{cfg.proveedor} · {cfg.modelo}: {respuesta}")


def _diagnostico(args) -> None:
    """C8: comprueba la instalación y resume los tiempos de las últimas ejecuciones."""
    from .observabilidad import carpeta, diagnostico, resumen_tiempos

    for nombre, bien, detalle in diagnostico():
        print(f"{'OK ' if bien else 'NO '} {nombre}: {detalle}")
    for etapa, r in resumen_tiempos().items():
        print(f"    {etapa:9} {r['n']:4} veces · mediana {r['mediana']:6.1f} s · máximo {r['maximo']:6.1f} s · errores {r['errores']}")
    print(f"Registro: {carpeta()}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos y «» en cualquier consola de Windows (también en la ayuda)
    logging.basicConfig(level=logging.WARNING, format="Aviso: %(message)s")
    from .observabilidad import configurar_registro

    configurar_registro()  # C8: registro rotativo en la carpeta de datos
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
    p.add_argument("--comparar-con", help="Resumen JSON de un informe anterior: muestra qué cambió y por qué (R16)")
    p.set_defaults(func=_informe, sec=True)

    p = sub.add_parser("modelo", help="Solo el modelo de valoración en Excel (fórmulas vivas), contrastado con LibreOffice")
    p.add_argument("ticker")
    p.add_argument("--salida", help="Carpeta de destino (por defecto, la carpeta de datos del usuario)")
    p.add_argument("--comparables", help="Lista del analista separada por comas (comparables del modelo)")
    p.set_defaults(func=_modelo, sec=True)

    p = sub.add_parser("interfaz", help="Abre la interfaz del analista en el navegador (Streamlit, en local)")
    p.set_defaults(func=_interfaz, sec=False)

    p = sub.add_parser("regresion", help="Batería de regresión: cifras clave de las empresas de prueba frente a su instantánea")
    p.add_argument("tickers", nargs="*", help="Por defecto, las 14 empresas de prueba (10 generales y 4 sectoriales)")
    p.add_argument("--actualizar", action="store_true", help="Guarda las cifras actuales como nueva referencia (tras revisarlas)")
    p.set_defaults(func=_regresion, sec=True)

    p = sub.add_parser("autoria", help="Datos de autoría que salen en la portada (cada usuario los suyos)")
    for campo in ("analista", "correo", "telefono", "empresa", "contacto_empresa"):
        p.add_argument(f"--{campo.replace('_', '-')}", dest=campo)
    p.set_defaults(func=_autoria, sec=False)

    p = sub.add_parser("metricas", help="Métricas del perfil sectorial con su fuente XBRL")
    p.add_argument("ticker")
    p.set_defaults(func=_metricas, sec=True)

    p = sub.add_parser("riesgos", help="Factores de riesgo del 10-K y los 5 principales (IA)")
    p.add_argument("ticker")
    p.add_argument("--sin-ia", action="store_true", help="Solo la lista literal, sin modelo de lenguaje")
    p.set_defaults(func=_riesgos, sec=True)

    p = sub.add_parser("versiones", help="Historial de versiones y detección de 10-Q/10-K nuevos")
    p.add_argument("accion", choices=["lista", "detectar", "preparar", "confirmar", "emitir"])
    p.add_argument("ticker")
    p.add_argument("--sin-ia", action="store_true", help="Al preparar, sin modelo de lenguaje")
    p.set_defaults(func=_versiones, sec=True)

    p = sub.add_parser("diagnostico", help="Comprueba la instalación (PDF, LibreOffice, claves) y resume los tiempos")
    p.set_defaults(func=_diagnostico, sec=False)

    p = sub.add_parser("ia", help="Comprueba la conexión con el modelo de lenguaje")
    p.set_defaults(func=_ia, sec=False)

    args = parser.parse_args()
    if args.sec:
        configurar_identidad()
    try:
        args.func(args)
    except ValueError as e:  # errores de datos o de uso con mensaje claro (p. ej. estimaciones no válidas)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
