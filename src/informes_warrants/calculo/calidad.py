"""Control de calidad de los datos: semáforo que bloquea la emisión si la SEC no cuadra.

Ideas reutilizadas: identidad activo = pasivo + patrimonio con tolerancia (edgartools
`xbrl/validation.validate_balance_sheet` y edgar_analytics `_validate_accounting_identity`, 1 %),
y la clasificación de problemas en errores y avisos de stock-screener `DataQualityChecker`.
Las comprobaciones son deterministas y se registran en la versión del informe.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from .normalizador import POR_ID, EstadosNormalizados

TOLERANCIA = 0.01  # 1 %
# Intereses / deuda declarada al cierre por encima de este tipo: casi seguro falta deuda por capturar (ORCL antes de
# LongTermNotesAndLoans: 3.500 M de intereses sobre 7.200 M de deuda = 48 %). Aviso, no error: una amortización
# grande a final de año también lo dispara.
TIPO_IMPLICITO_MAX = 0.20


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


def revisar(e: EstadosNormalizados, ejercicios: list[int] | None = None, etiqueta=lambda ej: f"FY{ej}") -> Informe:
    """Comprobaciones de los ejercicios pedidos (por defecto, todos); `etiqueta` da el nombre del periodo (p. ej. «LTM»)."""
    r = Informe()
    ejercicios = e.ejercicios if ejercicios is None else ejercicios
    for ejercicio, faltan in sorted(e.faltan.items()):
        if ejercicio in ejercicios:
            r.errores.append(f"{etiqueta(ejercicio)}: faltan partidas obligatorias: {', '.join(faltan)}")
    for ej in ejercicios:
        v = lambda p, ej=ej: e.valor(p, ej)  # noqa: E731
        FY = etiqueta(ej)  # noqa: N806
        activos, pasivos, patrimonio = v("activos"), v("pasivos"), v("patrimonio")
        for pid in (p for p, partida in POR_ID.items() if partida.derivadas):  # partidas calculadas: el analista debe saberlo
            dato = e.datos.get(pid, {}).get(ej)
            if dato is not None and any(dato.concepto == d.base or dato.concepto.startswith(d.base + " ")
                                       for d in POR_ID[pid].derivadas):  # concepto completo, no prefijo
                r.avisos.append(f"{FY}: {POR_ID[pid].nombre.lower()}, valor calculado (no declarado): {dato.concepto}")
        if None not in (activos, pasivos, patrimonio):
            total = pasivos + patrimonio + (v("minoritarios") or 0.0) + (v("patrimonio_temporal") or 0.0)
            if not _cuadra(activos, total):
                r.errores.append(f"{FY}: activo ({activos:,.0f}) ≠ pasivo + patrimonio ({total:,.0f})")
        ingresos, coste, bruto = v("ingresos"), v("coste_ventas"), v("beneficio_bruto")
        if None not in (ingresos, coste, bruto) and not _cuadra(ingresos - coste, bruto):
            r.errores.append(f"{FY}: ingresos − coste de ventas ≠ beneficio bruto declarado")
        bai, impuestos, bn = v("bai"), v("impuestos"), v("beneficio_neto")
        if None not in (bai, impuestos, bn) and not _cuadra(bai - impuestos, bn):
            r.avisos.append(f"{FY}: BAI − impuestos ≠ beneficio neto (resultados de participadas, minoritarios u operaciones "
                            "interrumpidas)")
        if ingresos is not None and ingresos <= 0:
            r.errores.append(f"{FY}: ingresos no positivos")
        if v("activo_corriente") is not None and activos is not None and v("activo_corriente") > activos:
            r.errores.append(f"{FY}: activo corriente mayor que el activo total")
        if patrimonio is not None and patrimonio < 0:
            r.avisos.append(f"{FY}: patrimonio negativo: ROE y P/BV no son interpretables")
        dato_cp = e.datos.get("deuda_cp", {}).get(ej)
        if dato_cp is not None and "CommercialPaper" in dato_cp.concepto and "ShortTermBorrowings" in dato_cp.concepto:
            r.avisos.append(f"{FY}: la deuda a corto suma papel comercial y préstamos a corto: comprobar en el balance que los "
                            "préstamos no incluyen ya el papel comercial")
        intereses, deuda = v("gasto_intereses"), (v("deuda_cp") or 0.0) + (v("deuda_lp") or 0.0)
        if intereses and intereses > 0 and (deuda <= 0 or intereses / deuda > TIPO_IMPLICITO_MAX):
            r.avisos.append(f"{FY}: gasto por intereses ({intereses / 1e6:,.0f} M) alto para la deuda declarada "
                            f"({deuda / 1e6:,.0f} M): revisar si falta deuda en el balance")
        if v("amortizacion") is None:
            r.avisos.append(f"{FY}: sin amortizaciones declaradas: EBITDA no disponible")
    return r
