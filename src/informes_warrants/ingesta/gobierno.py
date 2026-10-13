"""Gobierno corporativo desde la SEC: auditor (dei del 10-K) y retribución (proxy DEF 14A con XBRL).

Todo sale de edgartools (inventario, edgartools-3-formularios): `company_reports.auditor.extract_auditor_info`
y `ProxyStatement` (`ceo_pay_ratio`, `executive_compensation`, `pay_vs_performance`). La composición del
consejo y su independencia no se publican de forma estructurada: siguen siendo tarea del analista.
Cada dato que falta queda en None (nunca se inventa) y se registra un aviso.
"""

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class Gobierno:
    auditor: str | None = None
    auditor_ubicacion: str | None = None
    auditor_pcaob: int | None = None
    certifica_control_interno: bool | None = None
    proxy_accession: str | None = None
    proxy_fecha: str | None = None
    ejercicio_retribucion: str | None = None
    retribucion_ceo: float | None = None  # retribución total declarada (Summary Compensation Table)
    retribucion_ceo_efectiva: float | None = None  # «compensation actually paid» (tabla pay versus performance)
    retribucion_media_directivos: float | None = None
    pay_ratio: float | None = None
    retribucion_mediana_empleado: float | None = None
    tsr: float | None = None  # valor de 100 USD invertidos al inicio del periodo de la tabla
    tsr_comparables: float | None = None
    # Con varios primeros ejecutivos en el ejercicio (ORCL FY2026: tres), el proxy declara uno por uno (con dimensión)
    # y edgartools devuelve solo el primero: se guardan todos y el informe no atribuye a «el primer ejecutivo» uno solo.
    retribuciones_ceo: list[float] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _ultima_fila(df, columna_fecha="fiscal_year_end"):
    if df is None or getattr(df, "empty", True):
        return None
    return df.sort_values(columna_fecha).iloc[-1]


def _numero(valor):
    try:
        return None if valor is None or valor != valor else float(valor)  # NaN → None
    except (TypeError, ValueError):
        return None


def retribuciones_primeros_ejecutivos(filing, fin_ejercicio: str) -> list[float]:
    """Retribución total de cada primer ejecutivo del ejercicio (ecd:PeoTotalCompAmt con dimensión), de mayor a menor."""
    try:
        df = filing.xbrl().facts.query().by_concept("PeoTotalCompAmt").to_dataframe()
    except Exception:  # noqa: BLE001  (sin XBRL del proxy: se usa la fila de edgartools)
        return []
    if df is None or df.empty or "is_dimensioned" not in df:
        return []
    del_anio = df[(df["period_end"].astype(str).str[:10] == fin_ejercicio[:10]) & df["is_dimensioned"].astype(bool)]
    return sorted((float(v) for v in del_anio["numeric_value"].dropna()), reverse=True)


def gobierno(empresa, xbrl_10k) -> Gobierno:
    from edgar.company_reports.auditor import extract_auditor_info

    g = Gobierno()
    try:
        a = extract_auditor_info(xbrl_10k)
        if a:
            g.auditor, g.auditor_ubicacion, g.auditor_pcaob, g.certifica_control_interno = a.name, a.location, a.firm_id, a.icfr_attestation
    except Exception as e:  # noqa: BLE001  (un dato de gobierno que falta no rompe el informe)
        g.avisos.append(f"Auditor no disponible en el XBRL del 10-K: {e}")
    try:
        filing = empresa.get_filings(form="DEF 14A").latest()
    except Exception as e:  # noqa: BLE001
        filing = None
        g.avisos.append(f"Sin proxy DEF 14A: {e}")
    if filing is None:
        return g
    g.proxy_accession, g.proxy_fecha = filing.accession_no, str(filing.filing_date)
    try:
        proxy = filing.obj()
        ratio = proxy.ceo_pay_ratio
        if ratio:
            g.pay_ratio, g.retribucion_mediana_empleado = _numero(ratio.ratio), _numero(ratio.median_employee_compensation)
        fila = _ultima_fila(proxy.executive_compensation)
        if fila is not None:
            g.ejercicio_retribucion = str(fila["fiscal_year_end"])
            g.retribucion_ceo = _numero(fila.get("peo_total_comp"))
            g.retribucion_ceo_efectiva = _numero(fila.get("peo_actually_paid_comp"))
            g.retribucion_media_directivos = _numero(fila.get("neo_avg_total_comp"))
            g.retribuciones_ceo = retribuciones_primeros_ejecutivos(filing, g.ejercicio_retribucion)
        pvp = _ultima_fila(proxy.pay_vs_performance)
        if pvp is not None:
            g.tsr, g.tsr_comparables = _numero(pvp.get("total_shareholder_return")), _numero(pvp.get("peer_group_tsr"))
    except Exception as e:  # noqa: BLE001
        g.avisos.append(f"Proxy {filing.accession_no} sin datos de retribución estructurados: {e}")
    for aviso in g.avisos:
        log.warning(aviso)
    return g
