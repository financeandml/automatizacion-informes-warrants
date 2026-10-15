"""Datos sectoriales de Damodaran (NYU Stern, gratuitos): beta del sector y clasificación de empresas por sector.

Fuente externa de alta calidad aprobada por el usuario (2026-10-15) para la «beta modelo» y los «comparables modelo»
del motor de valoración, como la prima de riesgo (`mercado.prima_riesgo`). No aporta ninguna cifra financiera de las
empresas: esas siguen saliendo de la SEC.

- Beta del sector: «Unlevered beta corrected for cash» de la tabla de EE. UU. (Betas.html, actualizada cada enero).
- Clasificación: «Industry Group» de cada empresa (indname.xlsx, cotizadas de todo el mundo; se guardan las de NYSE
  y Nasdaq). Mejor que el código SIC, que agrupa mal (AAPL → DELL, SMCI).

Caché local en `directorio_datos()`: las betas se comprueban cada 7 días y la clasificación cada 30; sin conexión, el
último dato guardado; sin él, None (el motor usa la beta propia y lo avisa).
"""

import io
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta

log = logging.getLogger(__name__)
URL_BETAS = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html"
URL_INDUSTRIAS = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/indname.xlsx"
DIAS_BETAS, DIAS_INDUSTRIAS = 7, 30
FUENTE = "Damodaran (NYU Stern)"
BOLSAS = re.compile(r"^(NYSE|Nasdaq)")  # NYSE, NYSEAM, NasdaqGS, NasdaqGM, NasdaqCM


@dataclass(frozen=True)
class BetaSectorial:
    industria: str
    desapalancada: float  # corregida por la caja
    empresas: int
    fecha: str  # «January 2026»
    fuente: str = FUENTE

    @property
    def origen(self) -> str:
        return f"{self.fuente}, sector «{self.industria}» ({self.empresas} empresas de EE. UU.; {self.fecha})"


def parsear_betas(html: bytes) -> tuple[dict[str, dict], str]:
    """{sector: {"desapalancada", "empresas"}} y la fecha del dato, de la tabla de Betas.html."""
    import lxml.html

    raiz = lxml.html.parse(io.BytesIO(html)).getroot()
    filas = [[" ".join(td.text_content().split()) for td in tr.xpath("./td|./th")] for tr in raiz.xpath("//table//tr")]
    cabecera = next(f for f in filas if f and f[0] == "Industry Name")
    columna = cabecera.index("Unlevered beta corrected for cash")
    sectores = {}
    for f in filas:
        if len(f) > columna and f[0] and f[0] != "Industry Name" and not f[0].startswith("Total Market"):
            try:
                sectores[f[0]] = {"desapalancada": float(f[columna]), "empresas": int(f[1])}
            except ValueError:
                continue
    fecha = re.search(r"as of ([A-Z][a-z]+ \d{4})", " ".join(raiz.text_content().split()))
    return sectores, fecha.group(1) if fecha else ""


def parsear_industrias(xlsx: bytes) -> dict[str, list[str]]:
    """{ticker: [nombre, sector]} de las cotizadas en NYSE y Nasdaq (hoja «By industry» de indname.xlsx)."""
    import openpyxl

    ws = openpyxl.load_workbook(io.BytesIO(xlsx), read_only=True)["By industry"]
    filas = ws.iter_rows(values_only=True)
    cabecera = list(next(filas))
    i_nombre, i_ticker, i_sector = (cabecera.index(c) for c in ("Company Name", "Exchange:Ticker", "Industry Group"))
    salida = {}
    for f in filas:
        bolsa_ticker = str(f[i_ticker] or "")
        if ":" not in bolsa_ticker or not f[i_sector]:
            continue
        bolsa, ticker = bolsa_ticker.split(":", 1)
        if BOLSAS.match(bolsa):
            nombre = re.sub(r"\s*\([^)]*\)\s*$", "", str(f[i_nombre] or "")).strip()
            salida[ticker.strip().upper().replace(".", "-")] = [nombre, str(f[i_sector])]
    return salida


def _con_cache(nombre: str, dias: int, url: str, parsear):
    """Contenido de `url` parseado, con caché local de `dias` días; sin conexión, el último guardado (o None)."""
    import urllib.request

    from ..config import directorio_datos

    ruta = directorio_datos() / nombre
    guardado = None
    try:
        guardado = json.loads(ruta.read_text(encoding="utf-8"))
        if date.fromisoformat(guardado["consulta"]) >= date.today() - timedelta(days=dias):
            return guardado["datos"]
    except (OSError, ValueError, KeyError):
        pass
    try:
        with urllib.request.urlopen(url, timeout=60) as respuesta:
            datos = parsear(respuesta.read())
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps({"consulta": date.today().isoformat(), "datos": datos}, ensure_ascii=False), encoding="utf-8")
        return datos
    except Exception as e:  # noqa: BLE001  (sin conexión: el último dato guardado)
        log.warning("Damodaran %s no disponible: %s", nombre, e)
    return guardado["datos"] if guardado else None


def betas() -> tuple[dict[str, dict], str] | None:
    datos = _con_cache("damodaran_betas.json", DIAS_BETAS, URL_BETAS, lambda b: list(parsear_betas(b)))
    return (datos[0], datos[1]) if datos else None


def industrias() -> dict[str, list[str]] | None:
    return _con_cache("damodaran_industrias.json", DIAS_INDUSTRIAS, URL_INDUSTRIAS, parsear_industrias)


def sector_de(ticker: str) -> str | None:
    tabla = industrias() or {}
    fila = tabla.get(ticker.upper().replace(".", "-"))
    return fila[1] if fila else None


def beta_sectorial(ticker: str) -> BetaSectorial | None:
    """Beta desapalancada (corregida por la caja) del sector de Damodaran de la empresa; None si no está clasificada."""
    sector, tabla = sector_de(ticker), betas()
    if not sector or not tabla or sector not in tabla[0]:
        return None
    dato = tabla[0][sector]
    return BetaSectorial(sector, dato["desapalancada"], dato["empresas"], tabla[1])


def empresas_del_sector(ticker: str) -> tuple[str | None, list[str]]:
    """(sector, tickers de NYSE y Nasdaq del mismo sector de Damodaran, sin la empresa)."""
    tabla = industrias() or {}
    propio = ticker.upper().replace(".", "-")
    sector = (tabla.get(propio) or [None, None])[1]
    if not sector:
        return None, []
    return sector, [t for t, (_, s) in tabla.items() if s == sector and t != propio]
