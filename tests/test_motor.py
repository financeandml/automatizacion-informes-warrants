"""Motor de valoración (B1): evaluador de fórmulas de Excel, libro del modelo y contraste con LibreOffice.

El test *golden* reproduce, con el evaluador, cada valor que Excel guardó en las plantillas originales de
`Motor de valoración/` (no se publican: si la carpeta no está, se salta). Los demás tests no necesitan nada externo.
"""

import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from informes_warrants.calculo.motor.excel import DIV0, Error, Evaluador, Libro, TablaDeDatos, cargar, diferencias

PLANTILLAS = Path(__file__).resolve().parents[1] / "Motor de valoración" / "Ejemplos-plantillas"


def _libro(celdas: dict, **extra) -> Libro:
    return Libro(celdas={("H", *k): v for k, v in celdas.items()}, hojas=["H"], **extra)


def _calcular(celdas: dict, **extra) -> dict:
    valores = Evaluador(_libro(celdas, **extra)).calcular()
    return {k[1:]: v for k, v in valores.items()}


def test_funciones_y_semantica_de_excel():
    v = _calcular({
        (1, 1): 10, (1, 2): "--", (1, 3): 30, (1, 4): True,
        (2, 1): "=SUM(A1:D1)", (2, 2): "=AVERAGE(A1:D1)", (2, 3): "=MEDIAN(A1:C1,5)", (2, 4): "=A1/0",
        (3, 1): "=IF(A1>5,\"sí\")", (3, 2): "=IF(A1>50,1)", (3, 3): "=IFERROR(A1/0,-1)", (3, 4): "=ISERROR(B1*2)",
        (4, 1): "=25%", (4, 2): "=-2^2", (4, 3): "=\"a\"&A1", (4, 4): "=CHOOSE(2,\"x\",\"y\")",
        (5, 1): "=SUMPRODUCT(A1:C1,A1:C1)", (5, 2): "=A1=10.000000000000001", (5, 3): "=\"B\">5", (5, 4): "=MAX(A1:C1)-MIN(A1:C1)",
        (6, 1): "aaa", (6, 2): 7, (7, 1): "bbb", (7, 2): 8, (8, 1): "=VLOOKUP(\"BBB\",A6:B7,2,0)", (8, 2): "=VLOOKUP(\"zz\",A6:B7,2,0)",
        (9, 1): datetime(2024, 6, 30), (9, 2): datetime(2024, 12, 31), (9, 3): "=YEARFRAC(A9,B9)", (9, 4): "=YEARFRAC(A9,B9,3)",
    })
    assert (v[(2, 1)], v[(2, 2)], v[(2, 3)], v[(2, 4)]) == (40.0, 20.0, 10.0, DIV0)  # el texto y TRUE de un rango no cuentan
    assert (v[(3, 1)], v[(3, 2)], v[(3, 3)], v[(3, 4)]) == ("sí", False, -1.0, True)
    assert (v[(4, 1)], v[(4, 2)], v[(4, 3)], v[(4, 4)]) == (0.25, 4.0, "a10", "y")  # la negación va antes que ^ en Excel
    assert (v[(5, 1)], v[(5, 2)], v[(5, 3)], v[(5, 4)]) == (1000.0, True, True, 20.0)  # 15 cifras significativas
    assert v[(8, 1)] == 8 and isinstance(v[(8, 2)], Error) and v[(8, 2)].codigo == "#N/A"
    assert v[(9, 3)] == 0.5 and v[(9, 4)] == pytest.approx(184 / 365)  # 30/360: el 31 pasa a 30 si el inicio es 30


def test_referencias_circulares_con_calculo_iterativo():
    v = _calcular({(1, 1): "=0.5*A1+1", (1, 2): "=A1*2"})
    assert v[(1, 1)] == pytest.approx(2.0, abs=0.002) and v[(1, 2)] == pytest.approx(4.0, abs=0.004)


def test_tabla_de_datos_de_dos_entradas():
    """Esquina A3 = B1 × C1; la tabla B4:C5 sustituye B1 por la fila 3 y C1 por la columna A."""
    v = _calcular({(1, 2): 2, (1, 3): 3, (3, 1): "=B1*C1", (3, 2): 10, (3, 3): 20, (4, 1): 1, (5, 1): 5,
                   (6, 1): "=B1+C1"}, tablas=[TablaDeDatos("H", 4, 2, 5, 3, ("H", 1, 2), ("H", 1, 3))])
    assert (v[(4, 2)], v[(4, 3)], v[(5, 2)], v[(5, 3)]) == (10.0, 20.0, 50.0, 100.0)
    assert v[(3, 1)] == 6.0 and v[(6, 1)] == 5.0  # las entradas recuperan su valor


def _libros_originales(destino: Path) -> list[Path]:
    rutas = sorted(PLANTILLAS.glob("*.xlsx"))
    for z in PLANTILLAS.glob("*.zip"):
        with zipfile.ZipFile(z) as f:
            for nombre in f.namelist():
                if nombre.endswith(".xlsx"):
                    rutas.append(Path(f.extract(nombre, destino)))
    return rutas


@pytest.mark.skipif(not PLANTILLAS.exists(), reason="Las plantillas originales no se publican (carpeta local del usuario)")
def test_el_evaluador_reproduce_excel_en_las_plantillas_originales(tmp_path):
    """Las 12 plantillas: cada celda con fórmula (incluidas las tablas de datos) da lo mismo que guardó Excel."""
    rutas = _libros_originales(tmp_path)
    assert len(rutas) == 12
    total = 0
    for ruta in rutas:
        libro, guardados = cargar(ruta)
        calculados = Evaluador(libro, iniciales=guardados).calcular()
        assert not diferencias(libro, calculados, guardados, 1e-6), ruta.name
        total += sum(1 for v in libro.celdas.values() if isinstance(v, str) and v.startswith("="))
    assert total > 7000


def test_segmentos_estandarizados_con_conciliacion():
    """P21: corporativo, eliminaciones y segmentos que ya no existen van al bloque de conciliación; las ventas del modelo
    suman las consolidadas y el resultado no asignado cuadra con el EBIT consolidado (KO desde 2023)."""
    from types import SimpleNamespace

    from informes_warrants.calculo.motor.modelo import segmentos_del_modelo
    from informes_warrants.calculo.normalizador import Desglose, nombre_conciliacion

    assert nombre_conciliacion("CorporateMember") == "Corporativo (fuera de segmentos)"
    assert nombre_conciliacion("IntersegmentEliminationMember") == "Eliminaciones entre segmentos"
    assert nombre_conciliacion("CorporateAndInvestmentBankMember") is None  # un segmento de JPM, no una conciliación
    d = Desglose("negocio", "Revenues", ejercicios=[2024, 2025], conciliacion={"Eliminaciones entre segmentos"},
                 miembros={"Norte": {2024: 60.0, 2025: 70.0}, "Sur": {2024: 40.0, 2025: 45.0}, "Antiguo": {2024: 10.0},
                           "Eliminaciones entre segmentos": {2024: -5.0, 2025: -6.0}},
                 resultado_operativo={"Norte": {2024: 12.0, 2025: 14.0}, "Sur": {2024: 6.0, 2025: 7.0}, "Antiguo": {2024: 1.0}})
    totales = {("ingresos", 2024): 105.0, ("ingresos", 2025): 109.0,
               ("resultado_operativo", 2024): 17.0, ("resultado_operativo", 2025): 19.0}
    estados = SimpleNamespace(valor=lambda p, a: totales.get((p, a)))
    segs, motivo = segmentos_del_modelo(d, estados, 2025, [2024, 2025], "Empresa")
    assert [s.nombre for s in segs] == ["Norte", "Sur", "Otros, corporativo, eliminaciones y costes no asignados"]
    otros = segs[-1]
    assert otros.no_asignado and otros.ingresos == {2024: 5.0, 2025: -6.0}  # «Antiguo» (10) + eliminaciones (−5) en 2024
    assert sum(s.ingresos[2025] for s in segs) == 109.0 and otros.ebit[2025] == 19.0 - 14.0 - 7.0
    assert "resultado operativo" in motivo
