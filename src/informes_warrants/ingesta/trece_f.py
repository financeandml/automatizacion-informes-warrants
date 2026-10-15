"""Tenedores institucionales de una empresa desde los 13F de la SEC (P11, apartado 18).

El 13F es la cartera de cada gestora (edgartools `ThirteenF` lo lee por gestora); para verlo por emisora se usan los
**conjuntos de datos del 13F** que publica la SEC cada trimestre (todas las gestoras, por CUSIP):
https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets

El conjunto más reciente se descarga una vez (unos 100 MB) y se indexa en SQLite fuera de OneDrive
(`directorio_datos()/13f/`) con lo necesario: CUSIP, filing, acciones y valor de las posiciones en acciones (sin
opciones ni bonos) y el nombre de la gestora. Se cuentan los 13F-HR originales del trimestre más frecuente del
conjunto (las enmiendas no se suman, para no duplicar). El CUSIP de la empresa sale de la tabla CUSIP → ticker de
edgartools. Control de coherencia: se descartan las posiciones cuyo precio implícito (valor / acciones) se aleja más
del doble de la mediana de todas las gestoras (errores de declaración, p. ej. acciones con valor casi nulo), salvo
las que declaran el valor en miles (precio implícito mil veces menor), que se corrigen; se cuentan y se avisa.
Sin conexión ni índice, None: el apartado 18 sigue con el proxy, los 13D/G y yfinance como contraste.
"""

import csv
import io
import json
import logging
import re
import sqlite3
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)
URL_PAGINA = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
URL_SEC = "https://www.sec.gov"
DIAS_LISTA = 7
csv.field_size_limit(10_000_000)


def _carpeta():
    from ..config import directorio_datos

    carpeta = directorio_datos() / "13f"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def conjunto_mas_reciente() -> str | None:
    """Ruta del conjunto de datos más reciente (la lista se consulta cada semana)."""
    from edgar.httprequests import download_file

    cache = _carpeta() / "lista.json"
    try:
        guardada = json.loads(cache.read_text(encoding="utf-8"))
        if date.fromisoformat(guardada["consulta"]) >= date.today() - timedelta(days=DIAS_LISTA):
            return guardada["ruta"]
    except (OSError, ValueError, KeyError):
        guardada = None
    try:
        html = download_file(URL_PAGINA, as_text=True)
        rutas = re.findall(r'href="([^"]+form13f\.zip)"', html, re.I)
        if rutas:
            cache.write_text(json.dumps({"consulta": date.today().isoformat(), "ruta": rutas[0]}), encoding="utf-8")
            return rutas[0]
    except Exception as e:  # noqa: BLE001
        log.warning("Lista de conjuntos del 13F no disponible: %s", e)
    return guardada["ruta"] if guardada else None


def _indexar(ruta: str):
    """SQLite del conjunto: posiciones en acciones por CUSIP y gestoras de los 13F-HR del trimestre más frecuente."""
    from edgar.httprequests import download_file

    nombre = ruta.rsplit("/", 1)[-1].replace(".zip", "")
    destino = _carpeta() / f"{nombre}.sqlite"
    if destino.exists():
        return destino
    log.info("Indexando el conjunto del 13F %s (una vez por trimestre)", nombre)
    contenido = download_file(URL_SEC + ruta)
    z = zipfile.ZipFile(io.BytesIO(contenido if isinstance(contenido, bytes) else contenido.encode()))

    def filas(archivo):
        return csv.DictReader(io.TextIOWrapper(z.open(archivo), encoding="utf-8", errors="replace"), delimiter="\t")

    envios = {f["ACCESSION_NUMBER"]: f for f in filas("SUBMISSION.tsv") if f["SUBMISSIONTYPE"] == "13F-HR"}
    periodo = Counter(f["PERIODOFREPORT"] for f in envios.values()).most_common(1)[0][0]
    validos = {a for a, f in envios.items() if f["PERIODOFREPORT"] == periodo}
    temporal = destino.with_suffix(".tmp")
    con = sqlite3.connect(temporal)
    con.execute("CREATE TABLE gestoras (accession TEXT PRIMARY KEY, nombre TEXT, presentado TEXT)")
    con.execute("CREATE TABLE posiciones (cusip TEXT, accession TEXT, acciones REAL, valor REAL)")
    con.execute("CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT)")
    con.executemany("INSERT INTO gestoras VALUES (?, ?, ?)", ((f["ACCESSION_NUMBER"], f["FILINGMANAGER_NAME"],
                                                                envios[f["ACCESSION_NUMBER"]]["FILING_DATE"])
                                                               for f in filas("COVERPAGE.tsv") if f["ACCESSION_NUMBER"] in validos))
    con.executemany("INSERT INTO posiciones VALUES (?, ?, ?, ?)", (
        (f["CUSIP"].upper(), f["ACCESSION_NUMBER"], float(f["SSHPRNAMT"] or 0), float(f["VALUE"] or 0))
        for f in filas("INFOTABLE.tsv")
        if f["ACCESSION_NUMBER"] in validos and f["SSHPRNAMTTYPE"] == "SH" and not f["PUTCALL"]))
    con.execute("CREATE INDEX i_cusip ON posiciones (cusip)")
    con.executemany("INSERT INTO meta VALUES (?, ?)", [("periodo", periodo), ("conjunto", nombre), ("gestoras", str(len(validos)))])
    con.commit()
    con.close()
    temporal.replace(destino)
    return destino


def cusips(ticker: str) -> list[str]:
    from edgar.reference.tickers import cusip_ticker_mapping

    tabla = cusip_ticker_mapping()
    columna = "Ticker" if "Ticker" in tabla.columns else tabla.columns[0]
    return [str(c).upper() for c in tabla.index[tabla[columna].astype(str).str.upper() == ticker.upper()]]


def tenedores(ticker: str, n: int = 10) -> dict | None:
    """Mayores tenedores institucionales (acciones, valor y 13F) del trimestre del conjunto más reciente."""
    try:
        ruta = conjunto_mas_reciente()
        codigos = cusips(ticker)
        if not ruta or not codigos:
            return None
        con = sqlite3.connect(_indexar(ruta))
        meta = dict(con.execute("SELECT clave, valor FROM meta"))
        marcas = ",".join("?" * len(codigos))
        filas = con.execute(
            f"SELECT g.nombre, SUM(p.acciones), SUM(p.valor), p.accession, g.presentado FROM posiciones p "
            f"JOIN gestoras g ON g.accession = p.accession WHERE p.cusip IN ({marcas}) GROUP BY p.accession "
            f"ORDER BY SUM(p.acciones) DESC", codigos).fetchall()
        con.close()
    except Exception as e:  # noqa: BLE001  (sin 13F el apartado sigue con el proxy y los 13D/G)
        log.warning("13F de %s no disponible: %s", ticker, e)
        return None
    if not filas:
        return None
    import statistics

    precios = [f[2] / f[1] for f in filas if f[1] and f[2]]
    mediana = statistics.median(precios) if precios else None
    validas, descartadas, en_miles = [], [], 0
    for f in filas:
        ratio = (f[2] / f[1]) / mediana if mediana and f[1] else 0
        if 0.5 <= ratio <= 2:
            validas.append(f)
        elif 0.0005 <= ratio <= 0.002:  # valor declarado en miles (ambigüedad conocida del 13F): las acciones valen
            validas.append((f[0], f[1], f[2] * 1000, f[3], f[4]))
            en_miles += 1
        else:
            descartadas.append(f)
    filas = sorted(validas, key=lambda f: f[1], reverse=True)
    periodo = datetime.strptime(meta["periodo"], "%d-%b-%Y").date()
    return {"periodo": periodo, "conjunto": meta["conjunto"], "cusips": codigos, "gestoras": len(filas),
            "descartadas": [{"gestora": f[0], "acciones": f[1], "valor": f[2], "accession": f[3]} for f in descartadas],
            "precio_implicito": mediana, "valor_en_miles": en_miles,
            "acciones_totales": sum(f[1] for f in filas),
            "filas": [{"gestora": f[0], "acciones": f[1], "valor": f[2], "accession": f[3], "presentado": f[4]} for f in filas[:n]]}
