"""Calendario de catalizadores (A4): borrador que prepara el SaaS y que el analista confirma o sustituye.

Todas las fechas son estimaciones deterministas a partir de filings de la SEC y SIEMPRE posteriores a la fecha de
emisión del informe (decisión del usuario: nunca una fecha ya pasada como futura):
- Próximos resultados: la publicación (8-K ítem 2.02) de hace un año + 52 semanas (mismo día de la semana); la
  primera posterior a la emisión. Como contraste, el plazo legal del siguiente 10-Q o 10-K según la categoría de
  presentador (Regulation S-X / Form 10-K y 10-Q: 40 o 45 días tras el trimestre; 60, 75 o 90 tras el ejercicio).
- Junta anual: la última votación de la junta (8-K ítem 5.07) + 52 semanas.
Nada de esto sale de fuentes externas: si no hay historial suficiente, el evento no se propone.
"""

from datetime import date, timedelta

SEMANAS_52 = timedelta(days=364)
TRIMESTRE = timedelta(days=91)
TOLERANCIA_CIERRE = 10  # días: semanas fiscales de 52/53
# Días tras el cierre para presentar (SEC): 10-K y 10-Q por categoría de presentador
PLAZOS = {"Large Accelerated Filer": (60, 40), "Accelerated Filer": (75, 40)}
PLAZOS_RESTO = (90, 45)  # Non-accelerated filer y empresas pequeñas


def proxima_por_aniversario(fechas: list[date], hoy: date) -> date | None:
    """Primera fecha pasada + n × 52 semanas (n = 1…5) posterior a `hoy`; None sin historial."""
    candidatas = sorted(f + SEMANAS_52 * k for f in fechas for k in range(1, 6) if f + SEMANAS_52 * k > hoy)
    return candidatas[0] if candidatas else None


def _mismo_dia(fecha: date, anio: int) -> date:
    """La misma fecha en otro año (el 29 de febrero pasa al 28 si el año no es bisiesto)."""
    try:
        return fecha.replace(year=anio)
    except ValueError:
        return fecha.replace(year=anio, day=28)


def plazo_siguiente_informe(ultimo_cierre: date, cierre_ejercicio: date, categoria: str | None, hoy: date) -> dict | None:
    """Siguiente cierre de periodo (trimestre o ejercicio) y su plazo legal de presentación, si es posterior a hoy."""
    anual, trimestral = PLAZOS.get(categoria or "", PLAZOS_RESTO)
    cierre = ultimo_cierre
    for _ in range(8):
        cierre = cierre + TRIMESTRE
        es_anual = any(abs((cierre - _mismo_dia(cierre_ejercicio, cierre_ejercicio.year + k)).days) <= TOLERANCIA_CIERRE
                       for k in range(0, 4))
        limite = cierre + timedelta(days=anual if es_anual else trimestral)
        if limite > hoy:
            return {"formulario": "10-K" if es_anual else "10-Q", "cierre": cierre, "limite": limite,
                    "dias": anual if es_anual else trimestral}
    return None


def borrador(hoy: date, resultados: list[date], juntas: list[date], ultimo_cierre: date | None, cierre_ejercicio: date | None,
             categoria: str | None, vencimiento_12m: float | None, ejercicio: int) -> list[dict]:
    """Eventos del borrador: {evento, fecha, base}. Solo fechas posteriores a `hoy`."""
    eventos = []
    proximos = proxima_por_aniversario(resultados[-4:], hoy)
    plazo = plazo_siguiente_informe(ultimo_cierre, cierre_ejercicio, categoria, hoy) if ultimo_cierre and cierre_ejercicio else None
    if proximos:
        base = "Publicación de hace un año + 52 semanas (8-K ítem 2.02)"
        if plazo:
            base += f"; plazo legal del {plazo['formulario']}: {plazo['limite'].strftime('%d/%m/%Y')}"
        eventos.append({"evento": "Próximos resultados (estimado)", "fecha": proximos, "base": base})
    elif plazo:
        cierre = plazo["cierre"].strftime("%d/%m/%Y")
        eventos.append({"evento": f"Plazo legal del {plazo['formulario']}", "fecha": plazo["limite"],
                        "base": f"{plazo['dias']} días tras el cierre estimado del {cierre} ({categoria or 'sin categoría'})"})
    junta = proxima_por_aniversario(juntas[-2:], hoy)
    if junta:
        eventos.append({"evento": "Junta anual de accionistas (estimada)", "fecha": junta,
                        "base": "Última votación de la junta + 52 semanas (8-K ítem 5.07)"})
    if vencimiento_12m:
        importe = f"{vencimiento_12m / 1e6:,.0f}".replace(",", ".")
        eventos.append({"evento": f"Vencimientos de deuda de FY{(ejercicio + 1) % 100:02d}: {importe} USD mn", "fecha": None,
                        "base": "Vencimientos de principal del 10-K (próximos 12 meses tras el cierre)"})
    return sorted(eventos, key=lambda e: (e["fecha"] is None, e["fecha"] or date.max))
