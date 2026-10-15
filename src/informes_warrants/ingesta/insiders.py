"""Insiders y accionistas de más del 5 % (A6, apartado 18), desde la SEC.

Reutiliza edgartools:
- `Form4.market_trades`: compras y ventas en mercado (códigos P y S de la SEC).
- `non_derivative_table.non_market_trades`: el resto de códigos (A concesión, M ejercicio de opciones o RSU,
  F acciones entregadas para pagar impuestos, G donación…), que se separan de las compras y ventas: son
  retribución o movimientos sin decisión de inversión.
- `TransactionSummary`: nombre, cargo y si la operación se hizo con un plan 10b5-1 (venta programada).
- `ProxyStatement.beneficial_ownership` (Item 403 del proxy) y `Schedule13D/13G` (porcentaje del declarante).

Sin las enmiendas 4/A (repiten las operaciones del Form 4 original y se contarían dos veces).
Del proxy solo se toman los accionistas de más del 5 %: edgartools pone 0,50 % a consejeros y directivos cuando
el proxy dice «*» (menos del 1 %), un dato que la empresa no declara. Cada dato que falta queda fuera (nunca 0).
"""

import logging
import math
from datetime import date, timedelta

log = logging.getLogger(__name__)

TIPOS_MERCADO = {"P": "Compra", "S": "Venta"}
RETRIBUCION, RETENCIONES = {"A", "M"}, {"F"}
MAXIMO_FORMULARIOS = 300  # Form 4 de 12 meses; AAPL presenta unos 100 al año
FORMULARIOS_13 = ["SC 13G", "SC 13G/A", "SCHEDULE 13G", "SCHEDULE 13G/A", "SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A"]


def _numero(valor) -> float | None:
    try:
        x = float(str(valor).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _texto(valor) -> str:
    return " ".join(str(valor or "").replace("\xa0", " ").split())


def _fecha(valor) -> date | None:
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _fecha_us(valor) -> str:
    """«03/31/2026» (formato de EE. UU. del 13D/G) → «31/03/2026»; si no se reconoce, tal cual."""
    from datetime import datetime

    texto = _texto(valor)
    try:
        return datetime.strptime(texto, "%m/%d/%Y").strftime("%d/%m/%Y")
    except ValueError:
        return texto


def transacciones(empresa, hasta: date, dias: int = 365) -> dict:
    """Form 4 presentados en los `dias` anteriores a `hasta`: operaciones en mercado y resumen del resto."""
    desde = hasta - timedelta(days=dias)
    salida = {"desde": desde, "hasta": hasta, "formularios": 0, "operaciones": [], "personas": {}, "ciks": {},
              "retribucion": {"operaciones": 0, "acciones": 0.0}, "retenciones": {"operaciones": 0, "acciones": 0.0}}
    try:
        filings = empresa.get_filings(form="4", amendments=False)  # sin 4/A: repiten las operaciones del original
    except Exception as e:  # noqa: BLE001
        log.warning("Form 4 no disponibles: %s", e)
        return salida
    for filing in filings.head(MAXIMO_FORMULARIOS):
        presentado = _fecha(filing.filing_date)
        if presentado is None or presentado > hasta:
            continue
        if presentado < desde:
            break  # vienen del más reciente al más antiguo
        try:
            form4 = filing.obj()
            resumen = form4.get_ownership_summary()
            tabla = form4.non_derivative_table
        except Exception as e:  # noqa: BLE001  (un Form 4 ilegible no invalida el resto)
            log.warning("Form 4 %s ilegible: %s", filing.accession_no, e)
            continue
        salida["formularios"] += 1
        nombre = _texto(resumen.insider_name)
        if nombre and nombre not in salida["personas"]:  # el más reciente manda (vienen del más nuevo al más antiguo)
            salida["personas"][nombre] = _texto(resumen.position)
            duenos = getattr(getattr(form4, "reporting_owners", None), "owners", None) or []
            if duenos and getattr(duenos[0], "cik", None):  # P18: su CIK, para buscar su Form 3 aunque sea antiguo
                salida["ciks"][nombre] = str(duenos[0].cik)
        for fila in (form4.market_trades.to_dict("records") if form4.market_trades is not None else []):
            tipo, acciones, precio = TIPOS_MERCADO.get(fila.get("Code")), _numero(fila.get("Shares")), _numero(fila.get("Price"))
            if tipo is None or not acciones:
                continue
            salida["operaciones"].append({
                "fecha": _fecha(fila.get("Date")) or presentado, "nombre": _texto(resumen.insider_name),
                "cargo": _texto(resumen.position), "tipo": tipo, "acciones": acciones, "precio": precio,
                "importe": acciones * precio if precio else None, "plan_10b5_1": bool(resumen.has_10b5_1_plan),
                "accession": filing.accession_no})
        otras = tabla.non_market_trades if tabla is not None else None
        for fila in (otras.to_dict("records") if otras is not None and not otras.empty else []):
            acciones = _numero(fila.get("Shares")) or 0.0
            for codigos, clave in ((RETRIBUCION, "retribucion"), (RETENCIONES, "retenciones")):
                if fila.get("Code") in codigos:
                    salida[clave]["operaciones"] += 1
                    salida[clave]["acciones"] += acciones
    return salida


def accionistas_principales(empresa, hasta: date, dias: int = 365) -> dict:
    """Accionistas de más del 5 % del último proxy (Item 403) y declaraciones 13D/13G presentadas después."""
    salida = {"proxy_fecha": None, "proxy_accession": None, "del_proxy": [], "declaraciones": []}
    try:
        proxy_filing = empresa.get_filings(form="DEF 14A").latest()
    except Exception:  # noqa: BLE001
        proxy_filing = None
    if proxy_filing is not None:
        salida["proxy_fecha"], salida["proxy_accession"] = _fecha(proxy_filing.filing_date), proxy_filing.accession_no
        try:
            tabla = proxy_filing.obj().beneficial_ownership
        except Exception as e:  # noqa: BLE001
            log.warning("Proxy sin tabla de accionistas: %s", e)
            tabla = None
        if tabla is not None and not tabla.empty:
            for fila in tabla[tabla["holder_type"] == "5pct_holder"].to_dict("records"):
                porcentaje = _numero(fila.get("percent_of_class"))
                if porcentaje is not None:
                    salida["del_proxy"].append({"nombre": _texto(fila.get("holder_name")), "acciones": _numero(fila.get("shares")),
                                                "porcentaje": porcentaje / 100})
    desde = max(salida["proxy_fecha"] or hasta - timedelta(days=dias), hasta - timedelta(days=dias))
    try:
        filings = empresa.get_filings(form=FORMULARIOS_13)
    except Exception:  # noqa: BLE001
        filings = []
    for filing in filings:
        presentado = _fecha(filing.filing_date)
        if presentado is None or presentado > hasta:
            continue
        if presentado <= desde:
            break
        try:
            s = filing.obj()
            porcentaje = _numero(s.total_percent)
            personas = getattr(s, "reporting_persons", None) or []
        except Exception as e:  # noqa: BLE001
            log.warning("13D/G %s ilegible: %s", filing.accession_no, e)
            continue
        if porcentaje is None or not personas:
            continue
        emisor = getattr(getattr(s, "issuer_info", None), "cik", None)
        if emisor is not None and int(emisor) != int(empresa.cik):  # la empresa como inversora en otra (JPM, bancos, gestoras)
            continue
        salida["declaraciones"].append({"nombre": _texto(getattr(personas[0], "name", "")), "porcentaje": porcentaje / 100,
                                        "fecha_hecho": _fecha_us(getattr(s, "event_date", "")), "formulario": filing.form,
                                        "presentado": presentado})
    return salida
