"""Detección de 10-Q/10-K nuevos: crea la versión DETECTADA, que el analista debe confirmar.

Se ejecuta al abrir la app y bajo demanda. Para comprobarlo periódicamente se puede seguir el
patrón de stock-screener `src/notifications/scheduler.py` (`ScreeningScheduler.run_once`).
"""

from .almacen import Almacen
from .versiones import Estado, Version, heredar

FORMULARIOS = ["10-K", "10-Q"]


def version_para_filing(ticker: str, accession: str, fecha_filing: str, ejercicio: int, periodo: str,
                        almacen: Almacen) -> Version | None:
    """Propone la versión de un filing; None si ese filing ya tiene versión."""
    if almacen.conoce_accession(accession):
        return None
    ticker = ticker.upper()
    anterior = almacen.ultima_emitida(ticker)
    mismas = [v for v in almacen.historial(ticker) if (v.ejercicio, v.periodo) == (ejercicio, periodo)]
    version = Version(
        ticker=ticker, ejercicio=ejercicio, periodo=periodo,
        revision=max((v.revision for v in mismas), default=0) + 1,
        accession=accession, fecha_filing=fecha_filing, estado=Estado.DETECTADA,
        contenido=heredar(anterior.contenido) if anterior else {},
    )
    almacen.guardar(version)
    return version


def detectar(ticker: str, almacen: Almacen | None = None) -> Version | None:
    """Consulta la SEC y crea la versión DETECTADA si hay un 10-Q/10-K sin versión."""
    from edgar import Company

    almacen = almacen or Almacen()
    filing = Company(ticker).get_filings(form=FORMULARIOS, amendments=False).latest()  # las enmiendas no abren versión
    info = filing.xbrl().entity_info
    return version_para_filing(ticker, filing.accession_no, str(filing.filing_date),
                               int(info["fiscal_year"]), str(info["fiscal_period"]), almacen)
