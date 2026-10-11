"""Control de calidad de los datos: semáforo que bloquea la emisión si la SEC no cuadra.

Ideas reutilizadas: identidad activo = pasivo + patrimonio con tolerancia (edgartools
`xbrl/validation.validate_balance_sheet` y edgar_analytics `_validate_accounting_identity`, 1 %),
y la clasificación de problemas en errores y avisos de stock-screener `DataQualityChecker`.
Las comprobaciones son deterministas y se registran en la versión del informe.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from .normalizador import EstadosNormalizados

TOLERANCIA = 0.01  # 1 %


class Nivel(StrEnum):
    VERDE = "verde"  # todo cuadra
    AMBAR = "ámbar"  # avisos: se puede emitir, el analista los ve
    ROJO = "rojo"  # errores: bloquea la emisión


@dataclass
class Informe:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def nivel(self) -> Nivel:
        return Nivel.ROJO if self.errores else Nivel.AMBAR if self.avisos else Nivel.VERDE


def _cuadra(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCIA * max(abs(a), abs(b), 1.0)


def revisar(e: EstadosNormalizados) -> Informe:
    r = Informe()
    for ejercicio, faltan in sorted(e.faltan.items()):
        r.errores.append(f"FY{ejercicio}: faltan partidas obligatorias: {', '.join(faltan)}")
    for ej in e.ejercicios:
        v = lambda p, ej=ej: e.valor(p, ej)  # noqa: E731
        activos, pasivos, patrimonio = v("activos"), v("pasivos"), v("patrimonio")
        if None not in (activos, pasivos, patrimonio):
            total = pasivos + patrimonio + (v("minoritarios") or 0.0)
            if not _cuadra(activos, total):
                r.errores.append(f"FY{ej}: activo ({activos:,.0f}) ≠ pasivo + patrimonio ({total:,.0f})")
        ingresos, coste, bruto = v("ingresos"), v("coste_ventas"), v("beneficio_bruto")
        if None not in (ingresos, coste, bruto) and not _cuadra(ingresos - coste, bruto):
            r.errores.append(f"FY{ej}: ingresos − coste de ventas ≠ beneficio bruto declarado")
        bai, impuestos, bn = v("bai"), v("impuestos"), v("beneficio_neto")
        if None not in (bai, impuestos, bn) and not _cuadra(bai - impuestos, bn):
            r.avisos.append(f"FY{ej}: BAI − impuestos ≠ beneficio neto (resultados de participadas, minoritarios u operaciones "
                            "interrumpidas)")
        if ingresos is not None and ingresos <= 0:
            r.errores.append(f"FY{ej}: ingresos no positivos")
        if v("activo_corriente") is not None and activos is not None and v("activo_corriente") > activos:
            r.errores.append(f"FY{ej}: activo corriente mayor que el activo total")
        if patrimonio is not None and patrimonio < 0:
            r.avisos.append(f"FY{ej}: patrimonio negativo: ROE y P/BV no son interpretables")
        if v("amortizacion") is None:
            r.avisos.append(f"FY{ej}: sin amortizaciones declaradas: EBITDA no disponible")
    return r
