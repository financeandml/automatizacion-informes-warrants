"""Modelo de valoración de Warrants & Co. (B1): las plantillas de `Motor de valoración/` en un único libro propio.

Estructura y fórmulas de las plantillas (docs/motor-valoracion.md, §1): el DCF avanzado de rareliquid (modelo
operativo por segmentos, un DCF por segmento con valor terminal 80 % perpetuidad + 20 % múltiplo de salida,
consolidado con sensibilidades, WACC con beta desapalancada de los comparables y acciones diluidas por el método
del autocartera con convertibles), los comparables (base de datos, estadísticas y precio implícito por mínimo,
media, mediana y máximo) y los datos de la SEC en lugar de FactSet. Sin la marca ni los datos de las plantillas
(decisión D1 del usuario, 2026-10-14).

Correcciones respecto de las plantillas (decisiones del usuario del 2026-10-14; registradas en la hoja Controles):
  E1  Cifras dentro de fórmulas: se teclean dentro de la fórmula, como en la plantilla, con los valores de la SEC y
      un comentario con el concepto XBRL y el filing de cada uno.
  E2  Nombres rotos y vínculos a otros libros: nombres internos del libro, sin vínculos externos.
  E3  Consenso de FactSet: las proyecciones son entradas del analista (por defecto, la historia de la SEC).
  E4  Convención de descuento elegida por el analista (mitad de año o fin de año); el valor terminal por múltiplo se
      descuenta al final del último año.
  E5  Puente del EV completo (PDF de la plantilla: + preferentes + minoritarios; y R13: pensiones, patrimonio temporal
      y arrendamientos financieros si la deuda no los incluye).
  E6  Beta: desapalancada y reapalancada con la deuda bruta, la misma de los pesos del WACC.
  E7  Coste de la deuda: intereses de los últimos doce meses / deuda media.
  E8  Sensibilidades centradas en el WACC y el crecimiento del modelo (no tecleados).
  E9  Comparables: múltiplos negativos o no significativos fuera de las estadísticas («n.s.»).
  E17 Signo del capital circulante: la plantilla restaba la variación del flujo de caja (positiva = cobro); aquí la
      inversión en circulante (aumento = pago) sale del balance, como en las plantillas de LBO.
  E18 Precio de conversión de los convertibles = 1.000 / ratio (la plantilla dividía el principal entre el ratio).
  E19 Si los convertibles se convierten, su principal sale de la deuda (la plantilla lo calculaba y no lo usaba).
  E20 Periodo parcial: 0 si la fecha de valoración ya pasó el cierre del ejercicio en curso (YEARFRAC daba positivo).
"""

import math
from dataclasses import dataclass, field
from datetime import date

from .excel import TablaDeDatos
from .libro import Hoja, LibroModelo, col, ref

HIST, ACTUAL, PROY = (3, 4, 5, 6, 7), 8, (9, 10, 11, 12, 13)  # columnas del modelo operativo: 5 FY, ejercicio en curso, 5 años
ANIOS_PROY = 6  # ejercicio en curso + 5 (como la plantilla: 2024 con periodo parcial + 2025-2029)
DESPLAZAMIENTO_DCF = 2  # columna del DCF = columna del modelo operativo − 2 (C..K ↔ E..M)
PCT_PERPETUIDAD, TGR_PLANTILLA = 0.8, 0.025
LIMITES = {"ev_ventas": 30.0, "ev_ebitda": 50.0, "per": 75.0}  # múltiplos no significativos (los del informe)
MITAD, FIN = 1, 2
CORRECCIONES = (
    ("E1", "Cifras dentro de fórmulas: tecleadas dentro de la fórmula con los valores de la SEC y su origen en el comentario"),
    ("E2", "Nombres rotos y vínculos a otros libros: nombres internos, sin vínculos externos"),
    ("E3", "Proyecciones: entradas del analista en lugar del consenso de FactSet (por defecto, la historia de la SEC)"),
    ("E4", "Convención de descuento elegida por el analista; el valor terminal por múltiplo, al final del último año"),
    ("E5", "Puente del EV completo: preferentes, minoritarios, pensiones, patrimonio temporal y arrendamientos financieros"),
    ("E6", "Beta desapalancada y reapalancada con la deuda bruta, la misma de los pesos del WACC"),
    ("E7", "Coste de la deuda: intereses de los últimos doce meses / deuda media"),
    ("E8", "Sensibilidades centradas en el WACC y el crecimiento del modelo operativo (sin depender de las celdas de entrada)"),
    ("E9", "Comparables: múltiplos negativos o no significativos fuera de las estadísticas («n.s.»)"),
    ("E17", "Capital circulante: la inversión (aumento = pago) sale del balance; la plantilla restaba un cobro"),
    ("E18", "Precio de conversión de los convertibles = 1.000 / ratio de conversión"),
    ("E19", "Si los convertibles convierten, su principal sale de la deuda"),
    ("E20", "Periodo parcial nulo si la fecha de valoración ya pasó el cierre del ejercicio en curso"),
)


@dataclass
class Segmento:
    nombre: str
    ingresos: dict[int, float]
    ebit: dict[int, float]
    no_asignado: bool = False  # costes corporativos no asignados (EBIT consolidado − suma de segmentos)


@dataclass
class Comparable:
    ticker: str
    nombre: str
    precio: float
    acciones: float  # millones
    beta: float | None
    tipo_impositivo: float | None
    maximo_52s: float | None
    minimo_52s: float | None
    variaciones: dict[str, float | None]  # "1m", "3m", "6m"
    ltm: dict[str, float | None]  # ingresos, beneficio_bruto, ebit, ebitda, beneficio_neto, bpa (millones; BPA en USD)
    ltm_previo: dict[str, float | None]
    deuda: dict[str, float | None]  # deuda, caja, preferentes, minoritarios (millones)
    tacc_ventas_3a: float | None = None
    origen: str = ""


@dataclass
class DatosMotor:
    """Todo lo que el modelo toma de la SEC y del mercado (importes en USD; se pasan a millones al escribir)."""

    ticker: str
    empresa: str
    fecha_valoracion: date
    cierre_ejercicio: date  # cierre del último ejercicio presentado (FY0)
    ejercicio: int  # FY0
    estados: object  # EstadosNormalizados anual (FY0-5 … FY0)
    estados_ltm: object  # EstadosNormalizados con LTM y LTM_PREVIO
    etiqueta_ltm: str
    segmentos: list[Segmento]
    precio: float
    maximo_52s: float | None
    minimo_52s: float | None
    acciones_basicas: float
    origen_acciones: str
    beta_propia: float
    rf: float
    origen_rf: str
    erp: float
    origen_erp: str
    componentes_ev: dict[str, float]  # nombre → importe (calculo.metricas.componentes_ev del LTM)
    comparables: list[Comparable] = field(default_factory=list)
    mediana_historica: dict[str, float] = field(default_factory=dict)  # ev_ebitda, per (5 años, R11)


@dataclass
class EntradasMotor:
    """Lo que introduce el analista (por defecto, marcado «Revisar»)."""

    crecimientos: dict[str, list[float]]  # segmento → 6 años
    margenes: dict[str, list[float]]  # segmento → 6 años (margen EBIT; en costes no asignados, % de las ventas totales)
    tgr: float = TGR_PLANTILLA
    pct_perpetuidad: float = PCT_PERPETUIDAD
    convencion: int = MITAD
    rf: float | None = None
    erp: float | None = None
    lbo: bool = True  # hoja LBO (si el EBITDA del último ejercicio es positivo)
    ad: object = None  # lbo.EntradasAD: acreción-dilución (solo si el analista indica la operación)
    por_defecto: set = field(default_factory=set)  # entradas que el analista no ha tocado


@dataclass
class Modelo:
    libro: LibroModelo
    valores: dict
    celdas: dict[str, tuple]  # salida → (hoja, fila, col)
    avisos: list[str]
    salidas: dict


# ----------------------------------------------------------------------------------------------- valores por defecto

def _tacc(serie: dict[int, float], ultimos: int = 3) -> float | None:
    anios = sorted(a for a, v in serie.items() if v)
    if len(anios) < 2:
        return None
    a0 = anios[max(0, len(anios) - 1 - ultimos)]
    a1 = anios[-1]
    v0, v1 = serie[a0], serie[a1]
    if v0 <= 0 or v1 <= 0 or a1 == a0:
        return None
    return (v1 / v0) ** (1 / (a1 - a0)) - 1


def entradas_por_defecto(datos: DatosMotor, crecimiento_consolidado: list[float] | None = None, tgr: float | None = None,
                         rf: float | None = None, erp: float | None = None) -> EntradasMotor:
    """Crecimiento: la tasa compuesta de los 3 últimos ejercicios de cada segmento, acotada entre −10 % y 25 % (las
    plantillas usaban el consenso de FactSet, prohibido); sin segmentos, las estimaciones del informe. Margen: el último
    margen EBIT constante (regla de la plantilla). Crecimiento a perpetuidad, Rf y prima: los del informe."""
    crec, marg = {}, {}
    total_fy0 = sum(s.ingresos.get(datos.ejercicio, 0.0) for s in datos.segmentos if not s.no_asignado)
    for s in datos.segmentos:
        if s.no_asignado:
            crec[s.nombre] = [0.0] * ANIOS_PROY
            marg[s.nombre] = [round(s.ebit.get(datos.ejercicio, 0.0) / total_fy0, 4) if total_fy0 else 0.0] * ANIOS_PROY
            continue
        if len([x for x in datos.segmentos if not x.no_asignado]) == 1 and crecimiento_consolidado:
            g = list(crecimiento_consolidado)[:ANIOS_PROY]
            g += [g[-1]] * (ANIOS_PROY - len(g))
        else:
            t = _tacc(s.ingresos)
            g = [round(max(-0.10, min(0.25, t if t is not None else 0.05)), 4)] * ANIOS_PROY
        crec[s.nombre] = g
        ventas, ebit = s.ingresos.get(datos.ejercicio), s.ebit.get(datos.ejercicio)
        marg[s.nombre] = [round(ebit / ventas, 4) if ventas and ebit is not None else 0.0] * ANIOS_PROY
    e = EntradasMotor(crec, marg, tgr if tgr is not None else TGR_PLANTILLA, rf=rf, erp=erp)
    e.por_defecto = {"crecimientos", "margenes", "pct_perpetuidad", "convencion"}
    return e


UMBRAL_NO_ASIGNADO = 0.005  # por debajo del 0,5 % del EBIT consolidado, sin fila de costes no asignados


def segmentos_del_modelo(desglose, estados, ejercicio: int, anios: list[int], nombre_empresa: str) -> tuple[list[Segmento], str]:
    """Segmentos del modelo y por qué: los de negocio validados (suman las ventas consolidadas) con su resultado
    operativo en el último ejercicio, más los costes no asignados (EBIT consolidado − suma de segmentos); si no, un
    único bloque con la empresa entera (DCF consolidado de la plantilla, parte 1)."""
    usar = (desglose is not None and len(desglose.miembros) >= 2 and ejercicio in desglose.ejercicios and desglose.resultado_operativo
            and all(ejercicio in desglose.resultado_operativo.get(n, {}) for n in desglose.miembros))
    if not usar:
        ventas = {a: estados.valor("ingresos", a) for a in anios if estados.valor("ingresos", a) is not None}
        ebit = {a: estados.valor("resultado_operativo", a) for a in anios if estados.valor("resultado_operativo", a) is not None}
        motivo = "sin segmentos de negocio validados con su resultado operativo: un único bloque (DCF consolidado)"
        return [Segmento(nombre_empresa, ventas, ebit)], motivo
    validos = [a for a in desglose.ejercicios if all(a in desglose.resultado_operativo.get(n, {}) for n in desglose.miembros)]
    segmentos = [Segmento(n, {a: v for a, v in s.items() if a in desglose.ejercicios},
                          {a: v for a, v in desglose.resultado_operativo[n].items() if a in validos}) for n, s in desglose.miembros.items()]
    no_asignado = {}
    for a in validos:
        consolidado = estados.valor("resultado_operativo", a)
        if consolidado is not None:
            no_asignado[a] = consolidado - sum(desglose.resultado_operativo[n][a] for n in desglose.miembros)
    referencia = abs(estados.valor("resultado_operativo", ejercicio) or 0.0)
    if no_asignado and abs(no_asignado.get(ejercicio, 0.0)) > UMBRAL_NO_ASIGNADO * referencia:
        segmentos.append(Segmento("Costes no asignados", {}, no_asignado, no_asignado=True))
    return segmentos, f"{len(desglose.miembros)} segmentos de negocio validados ({desglose.origen})"


# ------------------------------------------------------------------------------------------------------- construcción

class _Constructor:
    def __init__(self, datos: DatosMotor, entradas: EntradasMotor):
        self.d, self.e = datos, entradas
        self.libro = LibroModelo()
        self.celdas: dict[str, tuple] = {}
        self.anios = [datos.ejercicio - 4 + i for i in range(5)]  # FY-4 … FY0 (columnas C..G)
        self.base = datos.ejercicio - 5  # columna B de las hojas de datos
        self.trazas: list[tuple] = []
        self.controles_extra: list[tuple] = []
        self.con_lbo = self.con_ad = False

    # -- utilidades
    def _mn(self, v):
        return None if v is None else v / 1e6

    def _dato(self, hoja: Hoja, fila: int, columna: int, partida: str, clave, estados, escala: float = 1e6, signo: int = 1,
              formato: str = "mn"):
        dato = estados.datos.get(partida, {}).get(clave)
        if dato is None:
            return None
        valor = signo * dato.valor / escala
        nota = f"{dato.concepto} · {dato.origen}"
        hoja.poner(fila, columna, valor, "entrada", formato, nota)
        self.trazas.append((hoja.nombre, ref(fila, columna), partida, dato.concepto, str(clave), dato.origen, valor))
        return valor

    def _teclear(self, hoja: Hoja, fila: int, columna: int, partes: list[tuple], formato="mn", signo_total=1, periodo="LTM"):
        """E1: las cifras van tecleadas dentro de la fórmula, como en la plantilla (=71178+17914), cada una con su origen.

        `partes`: (nombre, partida, dato) o (nombre, partida, dato, signo) con signo +1 o −1."""
        presentes = [(p[0], p[1], p[2], p[3] if len(p) > 3 else 1) for p in partes if p[2] is not None]
        if not presentes:
            hoja.poner(fila, columna, 0, "entrada", formato, "Sin dato declarado: 0")
            return
        terminos = ""
        for i, (_, _, dato, signo) in enumerate(presentes):
            numero = f"{dato.valor / 1e6:.6f}".rstrip("0").rstrip(".")
            terminos += ("-" if signo < 0 else ("+" if i else "")) + numero
        formula = f"={'-(' if signo_total < 0 else ''}{terminos}{')' if signo_total < 0 else ''}"
        nota = "; ".join(f"{'−' if signo < 0 else ''}{nombre}: {dato.concepto} · {dato.origen}" for nombre, _, dato, signo in presentes)
        hoja.poner(fila, columna, formula, "entrada", formato, nota)
        for _nombre, partida, dato, _signo in presentes:
            self.trazas.append((hoja.nombre, ref(fila, columna), partida, dato.concepto, periodo, dato.origen, dato.valor / 1e6))

    # -- hojas
    def construir(self) -> LibroModelo:
        self._portada()
        self._entradas()
        self._datos()
        self._segmentos()
        self._modelo_operativo()
        for i, s in enumerate(self.d.segmentos):
            self._dcf_segmento(i, s)
        self._consolidado()
        self._wacc()
        self._acciones()
        self._comparables()
        from .lbo import hoja_acrecion, hojas_lbo
        valor = lambda p: self.d.estados.valor(p, self.d.ejercicio) or 0  # noqa: E731
        ebitda = valor("resultado_operativo") + valor("amortizacion")
        if self.e.lbo and ebitda > 0:
            hojas_lbo(self)
            self.con_lbo = True
        if self.e.ad is not None:
            hoja_acrecion(self, self.e.ad)
            self.con_ad = True
        self._sintesis()
        self._controles()
        self._trazabilidad()
        orden = ["Portada", "Entradas", "Operating Model"] + [self._nombre_dcf(s) for s in self.d.segmentos] + \
            ["Consolidated", "WACC", "Shares", "Comps", "LBO", "LBO Shares", "Acreción-dilución", "Síntesis", "Controles",
             "IS", "BS", "CFS", "Segments", "Trazabilidad"]
        self.libro.hojas.sort(key=lambda h: orden.index(h.nombre))
        return self.libro

    def _nombre_dcf(self, s: Segmento) -> str:
        limpio = "".join(ch for ch in s.nombre if ch not in "[]:*?/\\'")[:24]
        return f"DCF {limpio}"

    def _portada(self):
        h = self.libro.hoja("Portada")
        h.poner(2, 2, "Modelo de valoración · Warrants & Co.", "titulo")
        h.poner(4, 2, "Empresa", "etiqueta")
        h.poner(4, 4, f"{self.d.empresa} ({self.d.ticker})")
        h.poner(5, 2, "Fecha de valoración", "etiqueta")
        h.poner(5, 4, self.d.fecha_valoracion, "", "fecha")
        h.poner(7, 2, "Hojas", "seccion")
        hojas = [("Entradas", "Supuestos del analista (en azul). Lo demás se calcula."),
                 ("Operating Model", "Modelo operativo por segmento: ventas, EBIT, impuestos, D&A, capex y capital circulante"),
                 ("DCF de cada segmento", "DCF con valor terminal por perpetuidad y por múltiplo de salida"),
                 ("Consolidated", "Suma de los segmentos, puente del EV al precio por acción y sensibilidad"),
                 ("WACC", "Coste del capital con beta desapalancada de los comparables"),
                 ("Shares", "Acciones totalmente diluidas (método del autocartera y convertibles)"),
                 ("Comps", "Comparables: base de datos, estadísticas y precio implícito"),
                 ("Síntesis", "Valor por acción de cada método"), ("Controles", "Controles de coherencia y correcciones"),
                 ("IS, BS, CFS, Segments", "Datos de la SEC (concepto XBRL y filing en el comentario de cada celda)"),
                 ("Trazabilidad", "Origen de cada dato")]
        for i, (n, t) in enumerate(hojas):
            h.poner(8 + i, 2, n, "etiqueta")
            h.poner(8 + i, 4, t)
        h.poner(21, 2, "Convenciones: entradas en azul; importes en millones de USD; acciones en millones; precio por acción en USD.")
        h.poner(22, 2, "Todas las cifras proceden de la SEC (EDGAR) y del mercado; ninguna la genera la IA.")

    def _entradas(self):
        h = self.libro.hoja("Entradas")
        e, d = self.e, self.d
        h.poner(2, 2, "Entradas del analista", "titulo")
        h.poner(3, 2, "Valores por defecto marcados «Revisar» en el comentario: el analista los confirma o los cambia.")
        filas = [(4, "Ticker", d.ticker, None, None), (5, "Fecha de valoración", d.fecha_valoracion, "fecha", None),
                 (6, "Cierre del ejercicio en curso", _mas_un_anio(d.cierre_ejercicio), "fecha", "Cierre del último 10-K + 1 año"),
                 (7, "Cotización (USD)", d.precio, "usd", "yfinance"),
                 (10, "Tipo libre de riesgo", e.rf if e.rf is not None else d.rf, "pct", d.origen_rf),
                 (11, "Prima de riesgo de mercado", e.erp if e.erp is not None else d.erp, "pct", d.origen_erp + " · Revisar"),
                 (12, "Crecimiento a perpetuidad (TGR)", e.tgr, "pct", "Plantilla: 2,5 % · Revisar"),
                 (13, "% del valor terminal por perpetuidad", e.pct_perpetuidad, "pct", "Plantilla: 80 % · Revisar"),
                 (14, "Convención de descuento (1 = mitad de año, 2 = fin de año)", e.convencion, None, "Revisar"),
                 (15, "Beta propia (5 años, semanal, frente a SPY)", d.beta_propia, "num", "Se usa si no hay comparables")]
        h.poner(9, 2, "Valoración", "seccion")
        for f, etiqueta, valor, formato, nota in filas:
            h.poner(f, 2, etiqueta, "etiqueta")
            h.poner(f, 3, valor, "entrada", formato, nota)
        self.libro.validaciones.append(("Entradas", "C14", "1,2"))
        self.celdas.update(rf=("Entradas", 10, 3), erp=("Entradas", 11, 3), tgr=("Entradas", 12, 3),
                           pct_perpetuidad=("Entradas", 13, 3), convencion=("Entradas", 14, 3))
        anios = [f"FY{d.ejercicio + k}e" for k in range(1, ANIOS_PROY + 1)]
        h.poner(17, 2, "Crecimiento de ventas por segmento", "seccion")
        h.fila(18, 3, anios, "cabecera")
        self.fila_crec = {}
        for i, s in enumerate(d.segmentos):
            f = 19 + i
            h.poner(f, 2, s.nombre, "etiqueta")
            for k in range(ANIOS_PROY):
                h.poner(f, 3 + k, e.crecimientos[s.nombre][k], "entrada", "pct",
                        "Revisar: por defecto, tasa compuesta de los 3 últimos ejercicios" if "crecimientos" in e.por_defecto else None)
            self.fila_crec[s.nombre] = f
        inicio = 19 + len(d.segmentos) + 1
        h.poner(inicio, 2, "Margen EBIT por segmento (costes no asignados: % de las ventas totales)", "seccion")
        h.fila(inicio + 1, 3, anios, "cabecera")
        self.fila_marg = {}
        for i, s in enumerate(d.segmentos):
            f = inicio + 2 + i
            h.poner(f, 2, s.nombre, "etiqueta")
            for k in range(ANIOS_PROY):
                h.poner(f, 3 + k, e.margenes[s.nombre][k], "entrada", "pct",
                        "Revisar: por defecto, el último margen constante (regla de la plantilla)" if "margenes" in e.por_defecto else None)
            self.fila_marg[s.nombre] = f

    def _datos(self):
        est, ltm = self.d.estados, self.d.estados_ltm
        from ..normalizador import LTM, LTM_PREVIO
        claves = [self.base] + self.anios
        etiquetas = [f"FY{a}" for a in claves] + [self.d.etiqueta_ltm]

        def hoja_datos(nombre, titulo, filas):
            h = self.libro.hoja(nombre)
            h.poner(1, 1, f"{self.d.empresa} ({self.d.ticker})", "titulo")
            h.poner(2, 1, titulo)
            h.fila(3, 2, etiquetas, "cabecera")
            for f, etiqueta, partida, signo, formato in filas:
                h.poner(f, 1, etiqueta, "etiqueta")
                if partida is None:
                    continue
                for j, clave in enumerate(claves):
                    self._dato(h, f, 2 + j, partida, clave, est, signo=signo, formato=formato,
                               escala=1 if formato == "usd" else 1e6)
                self._dato(h, f, 8, partida, LTM, ltm, signo=signo, formato=formato, escala=1 if formato == "usd" else 1e6)
            h.poner(40, 1, "Millones de USD salvo el BPA. Fuente: SEC EDGAR (companyfacts y XBRL); concepto y filing en cada comentario.")
            return h

        self.IS = {"ingresos": 5, "coste_ventas": 6, "beneficio_bruto": 7, "id": 8, "gastos_generales": 9, "resultado_operativo": 10,
                   "amortizacion": 11, "ebitda": 12, "gasto_intereses": 13, "ingresos_intereses": 14, "bai": 15, "impuestos": 16,
                   "beneficio_neto": 17, "bpa_diluido": 18, "acciones_diluidas": 19}
        nombres_is = {"ingresos": "Sales", "coste_ventas": "Cost of Goods Sold", "beneficio_bruto": "Gross Income",
                      "id": "Research & Development",
                      "gastos_generales": "SG&A Expense", "resultado_operativo": "EBIT (Operating Income)",
                      "amortizacion": "Depreciation & Amortization", "ebitda": "EBITDA", "gasto_intereses": "Interest Expense",
                      "ingresos_intereses": "Interest Income", "bai": "Pretax Income", "impuestos": "Income Taxes",
                      "beneficio_neto": "Net Income", "bpa_diluido": "EPS (diluted, USD)",
                      "acciones_diluidas": "Diluted Shares Outstanding"}
        is_ = hoja_datos("IS", "Income Statement (USD mn)", [
            (f, nombres_is[p], None if p in ("ebitda", "beneficio_bruto") else p, 1, "usd" if p == "bpa_diluido" else "mn")
            for p, f in self.IS.items()])
        for c in range(2, 9):  # beneficio bruto y EBITDA, calculados en la hoja
            is_.poner(7, c, f"={ref(5, c)}-{ref(6, c)}", "", "mn")
            is_.poner(12, c, f"={ref(10, c)}+{ref(11, c)}", "", "mn")
        self.BS = {"caja": 5, "inversiones_cp": 6, "clientes": 7, "existencias": 8, "activo_corriente": 9, "inmovilizado": 10,
                   "fondo_comercio": 11, "intangibles": 12, "activos": 13, "proveedores": 14, "pasivo_corriente": 15, "deuda_cp": 16,
                   "deuda_lp": 17, "pasivos": 18, "preferentes": 19, "patrimonio": 20, "minoritarios": 21, "patrimonio_temporal": 22,
                   "pensiones": 23, "arrendamientos_financieros": 24}
        nombres_bs = {"caja": "Cash & Equivalents", "inversiones_cp": "Short-Term Investments", "clientes": "Accounts Receivable",
                      "existencias": "Inventories", "activo_corriente": "Total Current Assets", "inmovilizado": "Net PP&E",
                      "fondo_comercio": "Goodwill", "intangibles": "Other Intangible Assets", "activos": "Total Assets",
                      "proveedores": "Accounts Payable", "pasivo_corriente": "Total Current Liabilities", "deuda_cp": "Short-Term Debt",
                      "deuda_lp": "Long-Term Debt", "pasivos": "Total Liabilities", "preferentes": "Preferred Stock",
                      "patrimonio": "Shareholders' Equity", "minoritarios": "Minority Interest", "patrimonio_temporal": "Temporary Equity",
                      "pensiones": "Net Pension Liability", "arrendamientos_financieros": "Finance Lease Liabilities"}
        bs = hoja_datos("BS", "Balance Sheet (USD mn)", [(f, nombres_bs[p], p, 1, "mn") for p, f in self.BS.items()])
        bs.poner(3, 9, f"{self.d.etiqueta_ltm} − 1 año", "cabecera")
        for p, f in self.BS.items():  # saldos de un año antes del LTM: variación del circulante del LTM
            self._dato(bs, f, 9, p, LTM_PREVIO, ltm)
        bs.poner(26, 1, "Operating Working Capital", "total")
        bs.poner(27, 1, "Check: Assets − (Liabilities + Equity + Minority + Temporary)", "etiqueta")
        for c in range(2, 10):
            bs.poner(26, c, f"=({ref(9, c)}-{ref(5, c)}-{ref(6, c)})-({ref(15, c)}-{ref(16, c)})", "total", "mn")
            bs.poner(27, c, f"={ref(13, c)}-({ref(18, c)}+{ref(20, c)}+{ref(21, c)}+{ref(22, c)})", "", "mn")
        self.CFS = {"flujo_operativo": 5, "amortizacion": 6, "pagos_basados_acciones": 7, "variacion_circulante": 8, "capex": 9,
                    "fcf": 10, "dividendos": 11, "recompras": 12}
        cfs = hoja_datos("CFS", "Cash Flow Statement (USD mn)", [
            (5, "Net Operating Cash Flow", "flujo_operativo", 1, "mn"),
            (6, "Depreciation, Depletion & Amortization", "amortizacion", 1, "mn"),
            (7, "Stock-Based Compensation", "pagos_basados_acciones", 1, "mn"),
            (8, "Changes in Working Capital (cash flow sign; from the balance sheet)", None, 1, "mn"),
            (9, "Capital Expenditures", "capex", -1, "mn"), (10, "Free Cash Flow", None, 1, "mn"),
            (11, "Dividends Paid", "dividendos", -1, "mn"), (12, "Repurchase of Common Stock", "recompras", -1, "mn")])
        for c in range(3, 8):  # E17: variación del circulante = −(circulante t − circulante t−1), del balance
            cfs.poner(8, c, f"=-(BS!{ref(26, c)}-BS!{ref(26, c - 1)})", "", "mn")
        cfs.poner(8, 8, "=-(BS!H26-BS!I26)", "", "mn")
        for c in range(2, 9):
            cfs.poner(10, c, f"={ref(5, c)}+{ref(9, c)}", "", "mn")

    def _segmentos(self):
        h = self.libro.hoja("Segments")
        d = self.d
        h.poner(1, 1, f"{d.ticker} · Segments (USD mn)", "titulo")
        etiquetas = [f"FY{a}" for a in [self.base] + self.anios] + [f"FY{d.ejercicio + k}e" for k in range(1, ANIOS_PROY + 1)]
        h.fila(3, 2, etiquetas, "cabecera")
        n = len(d.segmentos)
        self.seg_ventas, self.seg_ebit = {}, {}
        h.poner(5, 1, "Sales", "total")
        h.poner(7 + n, 1, "Operating Income", "total")
        for i, s in enumerate(d.segmentos):
            fv, fe = 6 + i, 8 + n + i
            self.seg_ventas[s.nombre], self.seg_ebit[s.nombre] = fv, fe
            h.poner(fv, 1, s.nombre, "etiqueta")
            h.poner(fe, 1, s.nombre, "etiqueta")
            for j, a in enumerate([self.base] + self.anios):
                if a in s.ingresos and not s.no_asignado:
                    h.poner(fv, 2 + j, s.ingresos[a] / 1e6, "entrada", "mn", "Segmentos ASC 280 del XBRL de los 10-K")
                if a in s.ebit:
                    h.poner(fe, 2 + j, s.ebit[a] / 1e6, "entrada", "mn",
                            "EBIT consolidado − suma de segmentos" if s.no_asignado else "Resultado operativo del segmento (ASC 280)")
            fc, fm = self.fila_crec[s.nombre], self.fila_marg[s.nombre]
            for k in range(ANIOS_PROY):
                c = 8 + k
                if not s.no_asignado:
                    h.poner(fv, c, f"={ref(fv, c - 1)}*(1+Entradas!{ref(fc, 3 + k)})", "", "mn")
                    h.poner(fe, c, f"={ref(fv, c)}*Entradas!{ref(fm, 3 + k)}", "", "mn")
                else:  # costes no asignados: % de las ventas totales
                    h.poner(fe, c, f"={ref(5, c)}*Entradas!{ref(fm, 3 + k)}", "", "mn")
        for c in range(2, 14):
            h.poner(5, c, f"=SUM({ref(6, c)}:{ref(5 + n, c)})", "total", "mn")
            h.poner(7 + n, c, f"=SUM({ref(8 + n, c)}:{ref(7 + 2 * n, c)})", "total", "mn")

    def _modelo_operativo(self):
        h = self.libro.hoja("Operating Model")
        d = self.d
        h.poner(2, 2, "Operating Model", "titulo")
        h.poner(4, 2, "Ticker", "etiqueta")
        h.poner(4, 8, "=Entradas!C4")
        h.poner(5, 2, "Date", "etiqueta")
        h.poner(5, 8, "=Entradas!C5", "", "fecha")
        h.poner(6, 2, "End of Year", "etiqueta")
        h.poner(6, 8, "=Entradas!C6", "", "fecha")
        h.poner(8, 2, "Assumptions", "seccion")
        h.poner(10, 2, "WACC", "etiqueta")
        h.poner(10, 8, "=WACC!F22", "", "pct")
        h.poner(11, 2, "TGR", "etiqueta")
        h.poner(11, 8, "=Entradas!C12", "", "pct")
        self.libro.nombres.update(wacc="'Operating Model'!$H$10", tgr="'Operating Model'!$H$11")
        h.poner(13, 2, "Financials", "seccion")
        todas = list(HIST) + [ACTUAL] + list(PROY)
        self.om = {}

        def anios(f):
            h.poner(f, 3, self.anios[0], "cabecera", "anio")
            for c in todas[1:]:
                h.poner(f, c, f"={ref(f, c - 1)}+1", "cabecera", "anio")

        def crecimiento(f, base):
            for c in todas:
                h.poner(f, c, f'=IF(ISERROR({ref(base, c)}/{ref(base, c - 1)}-1),"--",{ref(base, c)}/{ref(base, c - 1)}-1)', "", "pct")

        segs = d.segmentos
        f = 15
        h.poner(f, 2, "Revenue", "seccion")
        anios(f)
        f += 2
        filas_ventas = {}
        for s in segs:
            filas_ventas[s.nombre] = f
            h.poner(f, 2, s.nombre, "etiqueta")
            h.poner(f + 1, 2, "% growth")
            h.poner(f + 2, 2, "% of total sales")
            f += 4
        total_ventas = f
        for s in segs:
            fv = filas_ventas[s.nombre]
            for c in todas:
                if s.no_asignado:
                    h.poner(fv, c, 0, "", "mn")
                else:
                    h.poner(fv, c, f"=Segments!{ref(self.seg_ventas[s.nombre], c)}", "", "mn")
                h.poner(fv + 2, c, f"={ref(fv, c)}/{ref(total_ventas, c)}", "", "pct")
            crecimiento(fv + 1, fv)
        h.poner(total_ventas, 2, "Total", "total")
        h.poner(total_ventas + 1, 2, "% growth")
        for c in todas:
            h.poner(total_ventas, c, "=" + "+".join(ref(filas_ventas[s.nombre], c) for s in segs), "total", "mn")
        crecimiento(total_ventas + 1, total_ventas)
        self.om["ventas"] = total_ventas
        # EBIT
        f = total_ventas + 3
        h.poner(f, 2, "EBIT", "seccion")
        anios(f)
        f += 2
        filas_ebit = {}
        for s in segs:
            filas_ebit[s.nombre] = f
            h.poner(f, 2, s.nombre, "etiqueta")
            h.poner(f + 1, 2, "% of sales")
            h.poner(f + 2, 2, "% of total EBIT")
            f += 4
        total_ebit = f
        for s in segs:
            fe, fv = filas_ebit[s.nombre], filas_ventas[s.nombre]
            for c in todas:
                h.poner(fe, c, f"=Segments!{ref(self.seg_ebit[s.nombre], c)}", "", "mn")
                h.poner(fe + 1, c, f'=IF(ISERROR({ref(fe, c)}/{ref(fv, c)}),"--",{ref(fe, c)}/{ref(fv, c)})', "", "pct")
                h.poner(fe + 2, c, f"={ref(fe, c)}/{ref(total_ebit, c)}", "", "pct")
        h.poner(total_ebit, 2, "Total", "total")
        h.poner(total_ebit + 1, 2, "% of sales")
        for c in todas:
            h.poner(total_ebit, c, "=" + "+".join(ref(filas_ebit[s.nombre], c) for s in segs), "total", "mn")
            h.poner(total_ebit + 1, c, f"={ref(total_ebit, c)}/{ref(total_ventas, c)}", "", "pct")
        self.om["ebit"] = total_ebit
        # Impuestos: media de 5 años (plantilla)
        f = total_ebit + 3
        h.poner(f, 2, "Tax Rate", "seccion")
        anios(f)
        ft = f + 2
        h.poner(ft, 2, "Taxes", "etiqueta")
        h.poner(ft + 1, 2, "% tax rate", "etiqueta")
        for c in list(HIST) + [ACTUAL]:
            h.poner(ft, c, f"=IS!{ref(self.IS['impuestos'], c)}", "", "mn")
            h.poner(ft + 1, c, f'=IF({ref(ft, c)}<0,"--",IS!{ref(self.IS["impuestos"], c)}/IS!{ref(self.IS["bai"], c)})', "", "pct")
        for c in PROY:
            h.poner(ft + 1, c, f"=AVERAGE({ref(ft + 1, c - 5)}:{ref(ft + 1, c - 1)})", "", "pct")
        self.om["tasa"] = ft + 1
        # D&A, capex y capital circulante: por segmento con su % de ventas (media de 3 años); total de referencia: 5 años
        f = ft + 3
        self.om["da_seg"], self.om["capex_seg"], self.om["nwc_seg"] = {}, {}, {}
        f = self._bloque_partida(h, f, "D&A", "da", filas_ventas, total_ventas, f"CFS!{{c}}{self.CFS['amortizacion']}", 1)
        f = self._bloque_partida(h, f + 2, "CapEx", "capex", filas_ventas, total_ventas, f"CFS!{{c}}{self.CFS['capex']}", -1)
        f = self._bloque_partida(h, f + 2, "Net Working Capital", "nwc", filas_ventas, total_ventas,
                                 f"CFS!{{c}}{self.CFS['variacion_circulante']}", -1)
        self.filas_ventas, self.filas_ebit = filas_ventas, filas_ebit

    def _bloque_partida(self, h: Hoja, f: int, titulo: str, clave: str, filas_ventas, total_ventas, origen: str, signo: int) -> int:
        """Bloque de D&A, capex o variación del capital circulante del modelo operativo (plantilla avanzada, filas 54-122).

        Por segmento: asignación del total por su peso en las ventas en la historia (la SEC no siempre da el dato por
        segmento) y, en la proyección, la media de 3 años de su % de ventas × sus ventas. Total de referencia: el dato de
        la SEC (CFS) y, en la proyección, la media de 5 años sobre ventas."""
        todas = list(HIST) + [ACTUAL] + list(PROY)
        segs = [s for s in self.d.segmentos if not s.no_asignado]
        h.poner(f, 2, titulo, "seccion")
        h.poner(f, 3, self.anios[0], "cabecera", "anio")
        for c in todas[1:]:
            h.poner(f, c, f"={ref(f, c - 1)}+1", "cabecera", "anio")
        fila = f + 2
        filas = {}
        for s in segs:
            filas[s.nombre] = fila
            fila += 4
        total = fila
        referencia = total + 2
        for s in segs:
            fs, fv = filas[s.nombre], filas_ventas[s.nombre]
            h.poner(fs, 2, s.nombre, "etiqueta")
            h.poner(fs + 1, 2, f"% of {s.nombre} sales")
            h.poner(fs + 2, 2, "% of total sales (allocation)")
            for c in list(HIST) + [ACTUAL]:
                h.poner(fs + 2, c, f"={ref(fv + 2, c)}", "", "pct")
                h.poner(fs, c, f"={ref(fs + 2, c)}*{ref(referencia, c)}", "", "mn")
                h.poner(fs + 1, c, f'=IF(ISERROR({ref(fs, c)}/{ref(fv, c)}),"--",{ref(fs, c)}/{ref(fv, c)})', "", "pct")
            for c in PROY:
                h.poner(fs + 1, c, f"=AVERAGE({ref(fs + 1, c - 3)}:{ref(fs + 1, c - 1)})", "", "pct")
                h.poner(fs, c, f"={ref(fs + 1, c)}*{ref(fv, c)}", "", "mn")
            self.om[f"{clave}_seg"][s.nombre] = (fs, fs + 1)
        h.poner(total, 2, f"Total {titulo}", "total")
        h.poner(total + 1, 2, "% of total sales")
        for c in todas:
            h.poner(total, c, "=" + "+".join(ref(filas[s.nombre], c) for s in segs), "total", "mn")
            h.poner(total + 1, c, f"={ref(total, c)}/{ref(total_ventas, c)}", "", "pct")
        h.poner(referencia, 2, f"{titulo} (for reference, SEC)", "etiqueta")
        h.poner(referencia + 1, 2, "% of sales")
        for c in list(HIST) + [ACTUAL]:
            fuente = origen.format(c=col(c))
            h.poner(referencia, c, f"={'-' if signo < 0 else ''}{fuente}", "", "mn")
            h.poner(referencia + 1, c, f"={ref(referencia, c)}/{ref(total_ventas, c)}", "", "pct")
        for c in PROY:
            h.poner(referencia + 1, c, f"=AVERAGE({ref(referencia + 1, c - 5)}:{ref(referencia + 1, c - 1)})", "", "pct")
            h.poner(referencia, c, f"={ref(referencia + 1, c)}*{ref(total_ventas, c)}", "", "mn")
        self.om[clave] = total
        return referencia + 1

    def _dcf_segmento(self, i: int, s: Segmento):
        """Hoja DCF de un segmento: la de la plantilla avanzada (parte 3), filas 2-63."""
        nombre = self._nombre_dcf(s)
        h = self.libro.hoja(nombre)
        om = "'Operating Model'!"
        h.poner(2, 2, f"{s.nombre} DCF", "titulo")
        h.poner(4, 2, "Assumptions", "seccion")
        h.poner(5, 2, "WACC", "etiqueta")
        h.poner(5, 4, f"={om}$H$10", "", "pct")
        h.poner(6, 2, "TGR", "etiqueta")
        h.poner(6, 4, f"={om}$H$11", "", "pct")
        h.poner(8, 2, f"{s.nombre} DCF", "seccion")
        h.poner(10, 2, "FYE", "cabecera")
        h.poner(10, 3, self.anios[2], "cabecera", "anio")
        for c in range(4, 12):
            h.poner(10, c, f"={ref(10, c - 1)}+1", "cabecera", "anio")
        fv, fe = self.filas_ventas[s.nombre], self.filas_ebit[s.nombre]
        etiquetas = {12: "Revenue", 13: "% growth", 15: "EBIT", 16: "% of sales", 18: "Taxes", 19: "% tax rate", 21: "EBIAT",
                     23: "D&A", 24: "% of sales", 26: "CapEx", 27: "% of sales", 29: "Change in NWC", 30: "% of sales",
                     32: "Unlevered FCF", 33: "PV of UFCF", 35: "Stub", 36: "Discount Period", 38: "Terminal Value",
                     39: "PV of Terminal Value", 41: "Enterprise Value"}
        for f, t in etiquetas.items():
            h.poner(f, 2, t, "total" if f in (32, 41) else "etiqueta")
        for c in range(3, 12):
            co = c + DESPLAZAMIENTO_DCF
            h.poner(12, c, f"={om}{ref(fv, co)}", "", "mn")
            h.poner(13, c, f"={om}{ref(fv + 1, co)}", "", "pct")
            h.poner(15, c, f"={om}{ref(fe, co)}", "", "mn")
            h.poner(16, c, f"={om}{ref(fe + 1, co)}", "", "pct")
            if s.no_asignado:
                for f in (23, 26, 29):
                    h.poner(f, c, 0, "", "mn")
                for f in (24, 27, 30):
                    h.poner(f, c, 0, "", "pct")
            else:
                for f, clave in ((23, "da"), (26, "capex"), (29, "nwc")):
                    fs, fp = self.om[f"{clave}_seg"][s.nombre]
                    h.poner(f, c, f"={om}{ref(fs, co)}", "", "mn")
                    h.poner(f + 1, c, f"={om}{ref(fp, co)}", "", "pct")
        for c in range(6, 12):
            co = c + DESPLAZAMIENTO_DCF
            h.poner(19, c, f"={om}{ref(self.om['tasa'], co)}", "", "pct")
            h.poner(18, c, f"={ref(19, c)}*{ref(15, c)}", "", "mn")
            h.poner(21, c, f"={ref(15, c)}-{ref(18, c)}", "", "mn")
            h.poner(32, c, f"={ref(21, c)}+{ref(23, c)}-{ref(26, c)}-{ref(29, c)}", "total", "mn")
            h.poner(36, c, f"=Consolidated!{ref(36, c)}", "", "num")
        h.poner(33, 6, "=(F32*F35)/(1+$D$5)^F36", "", "mn")
        for c in range(7, 12):
            h.poner(33, c, f"={ref(32, c)}/(1+$D$5)^{ref(36, c)}", "", "mn")
        h.poner(35, 6, "=Consolidated!F35", "", "num")
        h.poner(38, 11, "=C49", "", "mn")
        h.poner(39, 11, "=C50", "", "mn")
        h.poner(41, 11, "=SUM(F33:K33,K39)", "total", "mn")
        # Valor terminal (perpetuidad y múltiplo de salida)
        h.poner(43, 2, "Terminal Value", "seccion")
        h.poner(45, 5, "Perpetuity Growth", "cabecera")
        h.poner(45, 9, "Exit Multiple", "cabecera")
        h.poner(46, 2, "% Perpetuity", "etiqueta")
        h.poner(46, 3, "=IF(ISNUMBER(K47),Entradas!$C$13,1)", "", "pct")
        h.poner(47, 2, "% Exit Multiple", "etiqueta")
        h.poner(47, 3, "=1-C46", "", "pct")
        h.poner(49, 2, "Total Terminal Value", "total")
        h.poner(49, 3, "=C46*G47+C47*K48", "total", "mn")
        h.poner(50, 2, "PV of Terminal Value", "etiqueta")
        h.poner(50, 3, "=C46*G48+C47*K49", "", "mn")
        filas_tv = [(46, "Terminal Growth Rate", "=D6", "pct"), (47, "Terminal Value", "=(K32*(1+G46))/(D5-G46)", "mn"),
                    (48, "PV of Terminal Value", "=G47/(1+D5)^K36", "mn"), (49, "Total Enterprise Value (TEV)", "=SUM(F33:K33)+G48", "mn"),
                    (52, "Terminal Value as % of TEV", "=G48/G49", "pct"),
                    (53, "Implied TV Exit EBITDA Multiple", "=G47/(K15+K23)", "x")]
        for f, t, formula, formato in filas_tv:
            h.poner(f, 5, t, "etiqueta")
            h.poner(f, 7, formula, "", formato)
        filas_salida = [(46, "Terminal Year EBITDA", "=K15+K23", "mn"), (47, "EBITDA multiple", "=Comps!$AD$" + "{mediana}", "x"),
                        (48, "Terminal Value", "=K46*K47", "mn"),
                        (49, "PV of Terminal Value", "=K48/(1+$D$5)^(K36+IF(Entradas!$C$14=1,0.5,0))", "mn"),  # E4
                        (50, "Total Enterprise Value (TEV)", "=SUM(F33:K33)+K49", "mn"),
                        (52, "Terminal Value as % of TEV", "=K49/K50", "pct"),
                        (53, "Implied terminal growth rate", "=(($D$5-(K32/K48))/((1+(K32/K48))))", "pct")]
        for f, t, formula, formato in filas_salida:
            h.poner(f, 9, t, "etiqueta")
            h.poner(f, 11, formula, "", formato)
        h.celdas[(53, 11)].comentario = "Implied TGR = [WACC − FCF(t)/TV] / (1 + FCF(t)/TV)"
        # Sensibilidad (tabla de datos de Excel, como la plantilla), centrada en el WACC y el TGR del modelo (E8)
        h.poner(55, 13, "Sensitivity Table", "cabecera")
        h.poner(57, 15, "WACC", "cabecera")
        h.poner(61, 13, "TGR", "cabecera")
        h.poner(58, 14, "=K41", "", "mn")
        # E8: cabeceras enlazadas al WACC y al TGR del modelo operativo (la plantilla los tecleaba): no pueden depender
        # de las celdas de entrada de la tabla (D5 y D6), que la tabla de datos sustituye
        h.poner(58, 17, f"={om}$H$10", "", "pct")
        h.poner(58, 16, "=Q58+0.25%", "", "pct")
        h.poner(58, 15, "=P58+0.25%", "", "pct")
        h.poner(58, 18, "=Q58-0.25%", "", "pct")
        h.poner(58, 19, "=R58-0.25%", "", "pct")
        h.poner(61, 14, f"={om}$H$11", "", "pct")
        h.poner(60, 14, "=N61-0.25%", "", "pct")
        h.poner(59, 14, "=N60-0.25%", "", "pct")
        h.poner(62, 14, "=N61+0.25%", "", "pct")
        h.poner(63, 14, "=N62+0.25%", "", "pct")
        # Tabla de datos de Excel: fila de entrada = WACC (D5), columna de entrada = TGR (D6), como la plantilla
        self.libro.tablas.append(TablaDeDatos(nombre, 59, 15, 63, 19, (nombre, 5, 4), (nombre, 6, 4)))
        self.celdas[f"ev_{s.nombre}"] = (nombre, 41, 11)
        self.celdas.setdefault("pct_perpetuidad_efectivo", (nombre, 46, 3))  # 100 % si no hay múltiplo de salida
        self.celdas[f"ev_perpetuidad_{s.nombre}"] = (nombre, 49, 7)
        self.celdas[f"ev_multiplo_{s.nombre}"] = (nombre, 50, 11)
        self.celdas[f"tv_pct_{s.nombre}"] = (nombre, 52, 7)
        self.celdas[f"multiplo_implicito_{s.nombre}"] = (nombre, 53, 7)
        self.celdas[f"tgr_implicito_{s.nombre}"] = (nombre, 53, 11)

    def _consolidado(self):
        h = self.libro.hoja("Consolidated")
        d = self.d
        hojas = [self._nombre_dcf(s) for s in d.segmentos]
        suma = lambda celda: "=" + "+".join(f"'{n}'!{celda}" for n in hojas)  # noqa: E731
        h.poner(2, 2, "Consolidated DCF", "titulo")
        h.poner(4, 2, "Assumptions", "seccion")
        h.poner(5, 2, "WACC", "etiqueta")
        h.poner(5, 4, "='Operating Model'!H10", "", "pct")
        h.poner(6, 2, "TGR", "etiqueta")
        h.poner(6, 4, "='Operating Model'!H11", "", "pct")
        h.poner(8, 2, "Consolidated DCF", "seccion")
        h.poner(10, 2, "FYE", "cabecera")
        h.poner(10, 3, self.anios[2], "cabecera", "anio")
        for c in range(4, 12):
            h.poner(10, c, f"={ref(10, c - 1)}+1", "cabecera", "anio")
        filas = {12: ("Revenue", range(3, 12)), 15: ("EBIT", range(3, 12)), 18: ("Taxes", range(6, 12)), 21: ("EBIAT", range(6, 12)),
                 23: ("D&A", range(6, 12)), 26: ("CapEx", range(6, 12)), 29: ("Change in NWC", range(6, 12)),
                 32: ("Unlevered FCF", range(6, 12)), 33: ("PV of UFCF", range(6, 12))}
        for f, (t, columnas) in filas.items():
            h.poner(f, 2, t, "total" if f == 32 else "etiqueta")
            for c in columnas:
                h.poner(f, c, suma(ref(f, c)), "total" if f == 32 else "", "mn")
        h.poner(13, 2, "% growth")
        h.poner(16, 2, "% of sales")
        for c in range(4, 12):
            h.poner(13, c, f"={ref(12, c)}/{ref(12, c - 1)}-1", "", "pct")
        for c in range(3, 12):
            h.poner(16, c, f"={ref(15, c)}/{ref(12, c)}", "", "pct")
        h.poner(19, 2, "% tax rate")
        for c in range(6, 12):
            h.poner(19, c, f"='Operating Model'!{ref(self.om['tasa'], c + DESPLAZAMIENTO_DCF)}", "", "pct")
            for f in (24, 27, 30):
                h.poner(f, c, f"={ref(f - 1, c)}/{ref(12, c)}", "", "pct")
        for f, t in ((24, "% of sales"), (27, "% of sales"), (30, "% of sales"), (35, "Stub"), (36, "Discount Period"),
                     (38, "Terminal Value"), (39, "PV of Terminal Value"), (41, "Enterprise Value")):
            h.poner(f, 2, t, "total" if f == 41 else "etiqueta")
        h.poner(35, 6, "=IF('Operating Model'!H5>='Operating Model'!H6,0,YEARFRAC('Operating Model'!H5,'Operating Model'!H6))",
                "", "num")  # E20
        h.poner(36, 6, "=IF(Entradas!$C$14=1,F35/2,F35)", "", "num")  # E4: mitad de año o fin de año
        h.poner(36, 7, "=F35+IF(Entradas!$C$14=1,0.5,1)", "", "num")
        for c in range(8, 12):
            h.poner(36, c, f"={ref(36, c - 1)}+1", "", "num")
        for f in (38, 39, 41):
            h.poner(f, 11, suma(ref(f, 11)), "total" if f == 41 else "", "mn")
        # Puente del EV al valor del patrimonio (E5: definición del PDF de la plantilla + R13), cifras del LTM tecleadas (E1)
        ltm = d.estados_ltm
        from ..normalizador import LTM
        dato = lambda p: ltm.datos.get(p, {}).get(LTM)  # noqa: E731
        puente = [(42, "(+) Cash & Short-Term Investments", [("Caja", "caja", dato("caja")),
                                                              ("Inversiones a c/p", "inversiones_cp", dato("inversiones_cp"))], 1),
                  (43, "(−) Debt", [("Deuda a c/p", "deuda_cp", dato("deuda_cp")), ("Deuda a l/p", "deuda_lp", dato("deuda_lp"))], 1),
                  (44, "(−) Preferred Stock", [("Preferentes", "preferentes", dato("preferentes"))], 1),
                  (45, "(−) Minority Interest", [("Minoritarios", "minoritarios", dato("minoritarios"))], 1),
                  (46, "(−) Net Pension Liability", [("Pensiones", "pensiones", dato("pensiones"))], 1),
                  (47, "(−) Temporary Equity", [("Patrimonio temporal", "patrimonio_temporal", dato("patrimonio_temporal"))], 1),
                  (48, "(−) Finance Leases (not in debt)", [("Arrendamientos financieros", "arrendamientos_financieros",
                                                             dato("arrendamientos_financieros") if d.componentes_ev.get(
                                                                 "Arrendamientos financieros") else None)], 1)]
        for f, t, partes, _signo in puente:
            h.poner(f, 2, t, "etiqueta")
            self._teclear(h, f, 11, partes)
        h.celdas[(43, 11)].valor = (h.celdas[(43, 11)].valor if isinstance(h.celdas[(43, 11)].valor, str) else "=0") + "+Shares!E40"  # E19
        h.celdas[(43, 11)].comentario = ((h.celdas[(43, 11)].comentario or "")
                                         + "; − principal de los convertibles si convierten (Shares!E40)")
        h.poner(49, 2, "Equity Value", "total")
        h.poner(49, 11, "=K41+K42-SUM(K43:K48)", "total", "mn")
        h.poner(51, 2, "FDSO", "etiqueta")
        h.poner(51, 11, "=Shares!E14", "", "acc")
        h.poner(52, 2, "Implied Share Price", "total")
        h.poner(52, 11, "=K49/K51", "total", "usd")
        h.poner(53, 2, "Current Share Price", "etiqueta")
        h.poner(53, 11, "=Entradas!C7", "", "usd")
        h.poner(54, 2, "Upside (Downside)", "etiqueta")
        h.poner(54, 11, "=K52/K53-1", "", "pct")
        # Sensibilidad del precio por acción: suma de las tablas de cada segmento (plantilla)
        h.poner(56, 13, "Sensitivity Table (USD per share)", "cabecera")
        h.poner(58, 15, "WACC", "cabecera")
        h.poner(60, 13, "TGR", "cabecera")
        h.poner(59, 14, "=K52", "", "usd")
        h.poner(59, 17, "=$D$5", "", "pct")
        h.poner(59, 16, "=Q59+0.25%", "", "pct")
        h.poner(59, 15, "=P59+0.25%", "", "pct")
        h.poner(59, 18, "=Q59-0.25%", "", "pct")
        h.poner(59, 19, "=R59-0.25%", "", "pct")
        h.poner(62, 14, "=$D$6", "", "pct")
        h.poner(61, 14, "=N62-0.25%", "", "pct")
        h.poner(60, 14, "=N61-0.25%", "", "pct")
        h.poner(63, 14, "=N62+0.25%", "", "pct")
        h.poner(64, 14, "=N63+0.25%", "", "pct")
        for k, f in enumerate(range(60, 65)):
            for c in range(15, 20):
                partes = "+".join(f"'{n}'!{ref(59 + k, c)}" for n in hojas)
                h.poner(f, c, f"=({partes}+$K$42-SUM($K$43:$K$48))/$K$51", "", "usd")
        self.celdas.update(ev=("Consolidated", 41, 11), patrimonio=("Consolidated", 49, 11), precio_dcf=("Consolidated", 52, 11),
                           potencial_dcf=("Consolidated", 54, 11), acciones_diluidas=("Consolidated", 51, 11),
                           caja=("Consolidated", 42, 11), deuda=("Consolidated", 43, 11), stub=("Consolidated", 35, 6))
        self.sensibilidad = ("Consolidated", 60, 15, 64, 19)

    def _wacc(self):
        h = self.libro.hoja("WACC")
        d = self.d
        h.poner(2, 2, "WACC", "titulo")
        h.poner(4, 2, "WACC = % of equity x cost of equity + % of debt x cost of debt x (1 − tax rate)")
        h.poner(5, 2, "Cost of equity = Risk free rate + Beta x Market Risk Premium")
        h.poner(7, 2, "WACC", "seccion")
        filas = [(8, "Market Cap", "=Comps!F12*Shares!E14", "mn"), (9, "% of Equity", "=F8/$F$20", "pct"),
                 (10, "Cost of Equity", "=F11+F12*F13", "pct"), (11, "Risk Free Rate", "=Entradas!C10", "pct"),
                 (12, "Beta", "=IF(COUNT(I28:I37)=0,Entradas!C15,E40)", "num"), (13, "Market Risk Premium", "=Entradas!C11", "pct"),
                 (15, "Debt", "=Consolidated!K43", "mn"), (16, "% of Debt", "=F15/$F$20", "pct"), (18, "Tax Rate",
                  f"=AVERAGE('Operating Model'!{ref(self.om['tasa'], 3)}:{ref(self.om['tasa'], 8)})", "pct"),
                 (20, "Total", "=F8+F15", "mn"), (22, "WACC", "=F9*F10+(F16*F17*(1-F18))", "pct")]
        for f, t, formula, formato in filas:
            h.poner(f, 2, t, "total" if f == 22 else "etiqueta")
            h.poner(f, 6, formula, "total" if f == 22 else "", formato)
        # E7: coste de la deuda = intereses LTM / deuda media (tecleado dentro de la fórmula, con su origen)
        from ..normalizador import LTM, LTM_PREVIO
        ltm = d.estados_ltm
        intereses = ltm.datos.get("gasto_intereses", {}).get(LTM)
        deudas = [sum((ltm.datos.get(p, {}).get(k).valor if ltm.datos.get(p, {}).get(k) else 0.0) for p in ("deuda_cp", "deuda_lp"))
                  for k in (LTM, LTM_PREVIO)]
        h.poner(17, 2, "Cost of Debt", "etiqueta")
        if intereses and sum(deudas) > 0:
            h.poner(17, 6, f"={intereses.valor / 1e6:.6f}/(({deudas[0] / 1e6:.6f}+{deudas[1] / 1e6:.6f})/2)", "entrada", "pct",
                    f"Intereses LTM ({intereses.concepto} · {intereses.origen}) / deuda media (LTM y un año antes)")
        else:
            h.poner(17, 6, 0.05, "entrada", "pct", "Sin intereses o deuda declarados: 5 % por defecto (Revisar)")
        h.poner(25, 2, "Beta", "seccion")
        for c, t in ((4, "Levered Beta"), (5, "Market Cap"), (6, "Debt"), (7, "Tax rate"), (9, "Unlevered Beta")):
            h.poner(27, c, t, "cabecera")
        h.poner(27, 11, "Levered beta / (1 + (1 − tax rate) × (Debt / Equity))")
        for i, cp in enumerate(d.comparables[:10]):
            f = 28 + i
            fila_comp = 14 + i
            h.poner(f, 2, cp.ticker, "etiqueta")
            if cp.beta is not None:
                h.poner(f, 4, cp.beta, "entrada", "num", "Regresión semanal de 5 años frente a SPY (yfinance)")
            h.poner(f, 5, f"=Comps!D{fila_comp}", "", "mn")
            h.poner(f, 6, f"={(cp.deuda.get('deuda') or 0):.6f}", "entrada", "mn", f"Deuda financiera bruta LTM (SEC) · {cp.origen}")
            h.poner(f, 7, cp.tipo_impositivo if cp.tipo_impositivo is not None else 0.21, "entrada", "pct",
                    "Tipo efectivo LTM (SEC)" if cp.tipo_impositivo is not None else "Sin dato: 21 % (Revisar)")
            if cp.beta is not None:
                h.poner(f, 9, f"=(D{f}/(1+(1-G{f})*(F{f}/E{f})))", "", "num")  # E6: deuda bruta
        h.poner(39, 2, "Industry Average Unlevered Beta", "etiqueta")
        h.poner(39, 5, '=IF(COUNT(I28:I37)=0,"--",AVERAGE(I28:I37))', "", "num")
        h.poner(40, 2, f"{d.empresa} ({d.ticker}) Levered Beta", "total")
        h.poner(40, 5, '=IF(COUNT(I28:I37)=0,"--",E39*(1+(1-F18)*(F15/F8)))', "total", "num")  # E6
        self.celdas.update(wacc=("WACC", 22, 6), ke=("WACC", 10, 6), beta=("WACC", 12, 6), kd=("WACC", 17, 6))

    def _acciones(self):
        h = self.libro.hoja("Shares")
        d = self.d
        est = d.estados
        dato = lambda p: est.datos.get(p, {}).get(d.ejercicio)  # noqa: E731
        h.poner(2, 2, "Diluted Share Count Calculation", "titulo")
        h.poner(4, 2, "Fully Diluted Shares", "seccion")
        h.poner(6, 2, "Current Stock Price", "etiqueta")
        h.poner(6, 5, "=Comps!F12", "", "usd")
        h.poner(7, 2, "Basic shares outstanding (latest filing)", "etiqueta")
        h.poner(7, 5, d.acciones_basicas / 1e6, "entrada", "acc", d.origen_acciones)
        etiquetas = [(8, "In-the-money exercisable options", "=E30"), (9, "Total proceeds ($mm)", "=SUMPRODUCT(D19:D28,E19:E28)"),
                     (10, "Total shares repurchased (mm)", "=E9/E6"), (11, "Net dilutive options", "=E8-E10")]
        for f, t, formula in etiquetas:
            h.poner(f, 2, t, "etiqueta")
            h.poner(f, 5, formula, "", "acc")
        rsu = dato("rsu_pendientes")
        h.poner(12, 2, "Dilutive impact of shares from other securities (RSU + convertibles)", "etiqueta")
        h.poner(12, 5, f"={(rsu.valor / 1e6 if rsu else 0):.6f}+E39", "entrada", "acc",
                f"RSU pendientes: {rsu.concepto} · {rsu.origen}" if rsu else "Sin RSU declaradas")
        h.poner(14, 2, "Net diluted shares outstanding", "total")
        h.poner(14, 5, "=E7+E11+E12", "total", "acc")
        h.poner(16, 2, "Options outstanding", "seccion")
        for c, t in ((3, "Outstanding"), (4, "Exercise price"), (5, "Dilutive Shares")):
            h.poner(18, c, t, "cabecera")
        h.poner(19, 2, 1)
        opciones, precio = dato("opciones_ejercitables"), dato("precio_ejercicio_opciones")
        for f in range(19, 29):
            if f > 19:
                h.poner(f, 2, f"=B{f - 1}+1")
            h.poner(f, 5, f"=IF(D{f}<$E$6,C{f})", "", "acc")
        if opciones and precio:
            h.poner(19, 3, opciones.valor / 1e6, "entrada", "acc", f"{opciones.concepto} · {opciones.origen}")
            h.poner(19, 4, precio.valor, "entrada", "usd", f"{precio.concepto} · {precio.origen}")
        h.poner(30, 2, "Total", "total")
        h.poner(30, 5, "=SUM(E19:E28)", "total", "acc")
        h.poner(32, 2, "Convertible Bonds", "seccion")
        conv, ratio = dato("convertibles"), dato("ratio_conversion")
        h.poner(34, 2, "Principal Outstanding ($mm)", "etiqueta")
        h.poner(34, 5, conv.valor / 1e6 if conv else 0, "entrada", "mn",
                f"{conv.concepto} · {conv.origen}" if conv else "Sin convertibles declarados")
        h.poner(35, 2, "Conversion Ratio (shares per $1,000)", "etiqueta")
        h.poner(35, 5, ratio.valor if ratio else 0, "entrada", "num", f"{ratio.concepto} · {ratio.origen}" if ratio else "Sin dato")
        h.poner(36, 2, "Conversion Price", "etiqueta")
        h.poner(36, 5, "=IFERROR(1000/E35,0)", "", "usd")  # E18
        h.poner(37, 2, "Convertible Common Shares", "etiqueta")
        h.poner(37, 5, "=E34*E35/1000", "", "acc")
        h.poner(39, 2, "Dilutive impact of convertible securities", "etiqueta")
        h.poner(39, 5, "=IF(AND(E36>0,E6>E36),E37,0)", "", "acc")
        h.poner(40, 2, "Elimination of liability from net debt", "etiqueta")
        h.poner(40, 5, "=IF(E39>0,-E34,0)", "", "mn")
        self.celdas.update(acciones_basicas=("Shares", 7, 5))

    def _comparables(self):
        """Comparables: tabla de la parte 3 (márgenes, crecimiento, múltiplos) + base de datos y precio implícito de
        Trading Comps, con los datos LTM de la SEC (sin estimaciones de consenso: LTM − 1 y LTM)."""
        h = self.libro.hoja("Comps")
        d = self.d
        h.poner(2, 2, "Comps Tables", "titulo")
        h.poner(4, 2, "Date", "etiqueta")
        h.poner(4, 3, d.fecha_valoracion, "", "fecha")
        h.poner(5, 2, "Currency", "etiqueta")
        h.poner(5, 3, "USD (mn)")
        cab = {4: "Market Cap", 5: "Enterprise Value", 6: "Current Price", 7: "52-Wk Low", 8: "52-Wk High", 9: "% of 52-Wk High",
               10: "1-Month Change", 11: "3-Month Change", 12: "6-Month Change", 14: "Revenue CAGR 3y", 15: "Revenue Growth LTM",
               16: "Gross Margin LTM−1", 17: "Gross Margin LTM", 18: "EBIT Margin LTM−1", 19: "EBIT Margin LTM", 20: "EBITDA Margin LTM−1",
               21: "EBITDA Margin LTM", 22: "Profit Margin LTM−1", 23: "Profit Margin LTM",
               25: "EV / Revenue LTM−1", 26: "EV / Revenue LTM",
               27: "EV / Gross Profit LTM−1", 28: "EV / Gross Profit LTM", 29: "EV / EBITDA LTM−1", 30: "EV / EBITDA LTM",
               31: "P / E LTM−1", 32: "P / E LTM", 34: "EV/EBITDA vs 5y median", 35: "P/E vs 5y median"}
        h.poner(10, 2, "Ticker", "cabecera")
        h.poner(10, 3, "Company Name", "cabecera")
        for c, t in cab.items():
            h.poner(10, c, t, "cabecera")
        filas = [("objetivo", 12, d.ticker, d.empresa, None)] + [(cp.ticker, 14 + i, cp.ticker, cp.nombre, cp)
                                                                   for i, cp in enumerate(d.comparables)]
        ultima = 13 + len(d.comparables)
        base = ultima + 12  # base de datos (Trading Comps: DATABASE)
        self._base_datos(h, base, filas)
        for _clave, f, tk, nombre, cp in filas:
            fb = self.fila_base[tk]
            h.poner(f, 2, tk, "total" if cp is None else "etiqueta")
            h.poner(f, 3, nombre)
            h.poner(f, 4, f"=F{fb}*G{fb}", "", "mn")  # capitalización = precio × acciones
            h.poner(f, 5, f"=D{f}+H{fb}+I{fb}+J{fb}-K{fb}", "", "mn")  # E5: EV = cap. + deuda + preferentes + minoritarios − caja
            h.poner(f, 6, f"=F{fb}", "", "usd")
            if cp is None:
                h.poner(f, 7, d.minimo_52s, "entrada", "usd")
                h.poner(f, 8, d.maximo_52s, "entrada", "usd")
            else:
                h.poner(f, 7, cp.minimo_52s, "entrada", "usd")
                h.poner(f, 8, cp.maximo_52s, "entrada", "usd")
                for c, k in ((10, "1m"), (11, "3m"), (12, "6m")):
                    if cp.variaciones.get(k) is not None:
                        h.poner(f, c, cp.variaciones[k], "entrada", "pct", "Cotizaciones semanales (yfinance)")
            h.poner(f, 9, f'=IF(ISERROR(F{f}/H{f}),"--",F{f}/H{f})', "", "pct")
            if cp is not None and cp.tacc_ventas_3a is not None:
                h.poner(f, 14, cp.tacc_ventas_3a, "entrada", "pct", "Normalizador SEC (3 años)")
            h.poner(f, 15, f'=IF(ISERROR(M{fb}/L{fb}-1),"--",M{fb}/L{fb}-1)', "", "pct")
            margenes = ((16, "N", "L"), (17, "O", "M"), (18, "P", "L"), (19, "Q", "M"), (20, "R", "L"), (21, "S", "M"),
                        (22, "T", "L"), (23, "U", "M"))
            for c, num, den in margenes:
                h.poner(f, c, f'=IF(ISERROR({num}{fb}/{den}{fb}),"--",{num}{fb}/{den}{fb})', "", "pct")
            multiplos = ((25, f"E{f}", "L", "ev_ventas"), (26, f"E{f}", "M", "ev_ventas"), (27, f"E{f}", "N", "ev_ventas"),
                         (28, f"E{f}", "O", "ev_ventas"), (29, f"E{f}", "R", "ev_ebitda"), (30, f"E{f}", "S", "ev_ebitda"),
                         (31, f"D{f}", "T", "per"), (32, f"D{f}", "U", "per"))
            for c, numerador, den, tipo in multiplos:  # E9: negativos y no significativos, «n.s.» (fuera de las estadísticas)
                x = f"{numerador}/{den}{fb}"
                h.poner(f, c, f'=IF(ISERROR({x}),"n.s.",IF(AND({x}>0,{x}<={LIMITES[tipo]}),{x},"n.s."))', "", "x")
        for c in (9, 10, 11, 12, 14, 15) + tuple(range(16, 24)) + tuple(range(25, 33)):
            formato = "x" if c >= 25 else "pct"
            if d.comparables:
                h.poner(ultima + 2, c, f'=IF(COUNT({col(c)}14:{col(c)}{ultima})=0,"--",AVERAGE({col(c)}14:{col(c)}{ultima}))', "", formato)
                h.poner(ultima + 3, c, f'=IF(COUNT({col(c)}14:{col(c)}{ultima})=0,"--",MEDIAN({col(c)}14:{col(c)}{ultima}))',
                        "total", formato)
        h.poner(ultima + 2, 2, "Mean", "etiqueta")
        h.poner(ultima + 3, 2, "Median", "total")
        self.fila_mediana = ultima + 3
        # Prima frente a los múltiplos medianos de 5 años de la propia empresa (columnas «Premium to historical» de la plantilla)
        for c, clave, fuente in ((34, "ev_ebitda", "AD12"), (35, "per", "AF12")):
            mediana = d.mediana_historica.get(clave)
            if mediana:
                h.poner(12, c, f'=IF(ISNUMBER({fuente}),{fuente}/{mediana:.6f}-1,"--")', "entrada", "pct",
                        "Mediana de 5 años sobre el precio semanal y las cifras de cada 10-K (R11)")
        self._precio_implicito(h, ultima + 5)
        # Corrige la referencia del múltiplo de salida de los DCF a la fila de la mediana
        for hoja in self.libro.hojas:
            if hoja.nombre.startswith("DCF "):
                hoja.celdas[(47, 11)].valor = f'=IF(ISNUMBER(Comps!$AD${self.fila_mediana}),Comps!$AD${self.fila_mediana},"--")'
                hoja.celdas[(47, 11)].comentario = ("Mediana EV/EBITDA LTM de los comparables; sin comparables, «--» y el valor terminal "
                                                    "es 100 % por perpetuidad (C46)")
                for f, formula in ((48, '=IF(ISNUMBER(K47),K46*K47,0)'),
                                   (49, '=IF(ISNUMBER(K47),K48/(1+$D$5)^(K36+IF(Entradas!$C$14=1,0.5,0)),0)'),
                                   (52, '=IF(ISNUMBER(K47),K49/K50,"--")'),
                                   (53, '=IF(ISNUMBER(K47),(($D$5-(K32/K48))/((1+(K32/K48)))),"--")')):
                    hoja.celdas[(f, 11)].valor = formula
        self.celdas.update(mediana_ev_ebitda=("Comps", self.fila_mediana, 30))

    def _base_datos(self, h: Hoja, f0: int, filas):
        """DATABASE de Trading Comps: precio, acciones, deuda y métricas de cada empresa (SEC, LTM − 1 y LTM)."""
        from ..normalizador import LTM, LTM_PREVIO
        h.poner(f0 - 2, 2, "DATABASE (SEC: LTM − 1 and LTM; market data: yfinance)", "seccion")
        cab = {2: "Ticker", 3: "Company Name", 6: "Price", 7: "Shares (mn)", 8: "Debt", 9: "Preferred", 10: "Minority",
               11: "Cash & ST Inv.",
               12: "Revenue LTM−1", 13: "Revenue LTM", 14: "Gross Profit LTM−1", 15: "Gross Profit LTM", 16: "EBIT LTM−1", 17: "EBIT LTM",
               18: "EBITDA LTM−1", 19: "EBITDA LTM", 20: "Net Income LTM−1", 21: "Net Income LTM", 22: "EPS LTM"}
        for c, t in cab.items():
            h.poner(f0 - 1, c, t, "cabecera")
        self.fila_base = {}
        d = self.d
        ltm = d.estados_ltm

        def v(p, k):
            dato = ltm.datos.get(p, {}).get(k)
            return None if dato is None else dato.valor / 1e6

        for i, (_, _, tk, nombre, cp) in enumerate(filas):
            f = f0 + i
            self.fila_base[tk] = f
            h.poner(f, 2, tk)
            h.poner(f, 3, nombre)
            if cp is None:
                caja = (v("caja", LTM) or 0) + (v("inversiones_cp", LTM) or 0)
                valores = {6: d.precio, 7: "=Shares!E14", 8: "=Consolidated!K43", 9: "=Consolidated!K44", 10: "=Consolidated!K45",
                           11: caja, 12: v("ingresos", LTM_PREVIO), 13: v("ingresos", LTM),
                           14: _resta(v("ingresos", LTM_PREVIO), v("coste_ventas", LTM_PREVIO)),
                           15: _resta(v("ingresos", LTM), v("coste_ventas", LTM)), 16: v("resultado_operativo", LTM_PREVIO),
                           17: v("resultado_operativo", LTM),
                           18: _suma(v("resultado_operativo", LTM_PREVIO), v("amortizacion", LTM_PREVIO)),
                           19: _suma(v("resultado_operativo", LTM), v("amortizacion", LTM)), 20: v("beneficio_neto", LTM_PREVIO),
                           21: v("beneficio_neto", LTM), 22: ltm.valor("bpa_diluido", LTM)}
                nota = "SEC (normalizador, LTM)"
            else:
                valores = {6: cp.precio, 7: cp.acciones, 8: cp.deuda.get("deuda"), 9: cp.deuda.get("preferentes"),
                           10: cp.deuda.get("minoritarios"), 11: cp.deuda.get("caja"), 12: cp.ltm_previo.get("ingresos"),
                           13: cp.ltm.get("ingresos"), 14: cp.ltm_previo.get("beneficio_bruto"), 15: cp.ltm.get("beneficio_bruto"),
                           16: cp.ltm_previo.get("ebit"), 17: cp.ltm.get("ebit"), 18: cp.ltm_previo.get("ebitda"), 19: cp.ltm.get("ebitda"),
                           20: cp.ltm_previo.get("beneficio_neto"), 21: cp.ltm.get("beneficio_neto"), 22: cp.ltm.get("bpa")}
                nota = f"SEC (normalizador, LTM) · {cp.origen}"
            for c, x in valores.items():
                if x is None:
                    continue
                h.poner(f, c, x, "entrada" if not (isinstance(x, str) and x.startswith("=")) else "",
                        "usd" if c in (6, 22) else ("acc" if c == 7 else "mn"), nota if c != 6 else "yfinance")

    def _precio_implicito(self, h: Hoja, f0: int):
        """«Calculating Implied Share Price» de Trading Comps: mínimo, media, mediana y máximo × la métrica de la empresa."""
        u = 13 + len(self.d.comparables)
        fb = self.fila_base[self.d.ticker]
        h.poner(f0, 2, "Calculating Implied Share Price", "seccion")
        for c, t in ((4, "EV / Revenue LTM"), (5, "EV / EBITDA LTM"), (6, "P / E LTM"), (8, "Revenue LTM"),
                     (9, "EBITDA LTM"), (10, "EPS LTM"),
                     (12, "EV (Revenue)"), (13, "EV (EBITDA)"), (15, "Equity (Revenue)"), (16, "Equity (EBITDA)"),
                     (18, "Price (Revenue)"), (19, "Price (EBITDA)"), (20, "Price (P/E)")):
            h.poner(f0 + 1, c, t, "cabecera")
        estadisticas = (("Minimum", "MIN"), ("Mean", "AVERAGE"), ("Median", "MEDIAN"), ("Maximum", "MAX"))
        self.filas_implicito = {}
        for k, (nombre, funcion) in enumerate(estadisticas):
            f = f0 + 2 + k
            self.filas_implicito[nombre] = f
            h.poner(f, 2, nombre, "etiqueta")
            for c, fuente in ((4, "Z"), (5, "AD"), (6, "AF")):
                rango = f"{fuente}14:{fuente}{u}"
                h.poner(f, c, f'=IF(COUNT({rango})=0,"--",{funcion}({rango}))' if self.d.comparables else '="--"', "", "x")
            h.poner(f, 8, f"=M{fb}", "", "mn")
            h.poner(f, 9, f"=S{fb}", "", "mn")
            h.poner(f, 10, f"=V{fb}", "", "usd")
            h.poner(f, 12, f'=IF(ISNUMBER(D{f}),D{f}*H{f},"--")', "", "mn")
            h.poner(f, 13, f'=IF(ISNUMBER(E{f}),E{f}*I{f},"--")', "", "mn")
            h.poner(f, 15, f'=IF(ISNUMBER(L{f}),L{f}+Consolidated!$K$42-SUM(Consolidated!$K$43:$K$48),"--")', "", "mn")
            h.poner(f, 16, f'=IF(ISNUMBER(M{f}),M{f}+Consolidated!$K$42-SUM(Consolidated!$K$43:$K$48),"--")', "", "mn")
            h.poner(f, 18, f'=IF(ISNUMBER(O{f}),O{f}/Shares!$E$14,"--")', "", "usd")
            h.poner(f, 19, f'=IF(ISNUMBER(P{f}),P{f}/Shares!$E$14,"--")', "", "usd")
            h.poner(f, 20, f'=IF(AND(ISNUMBER(F{f}),J{f}>0),F{f}*J{f},"--")', "", "usd")
        self.celdas.update({f"comps_{n}_{m}": ("Comps", f, c) for n, f in self.filas_implicito.items()
                            for m, c in (("ventas", 18), ("ebitda", 19), ("per", 20))})

    def _sintesis(self):
        h = self.libro.hoja("Síntesis")
        h.poner(2, 2, "Síntesis de la valoración (USD por acción)", "titulo")
        for c, t in ((3, "Bajo"), (4, "Central"), (5, "Alto"), (6, "Potencial (central)")):
            h.poner(4, c, t, "cabecera")
        mi, me, ma = (self.filas_implicito[n] for n in ("Minimum", "Median", "Maximum"))
        segs = [self._nombre_dcf(s) for s in self.d.segmentos]
        perpetuo = "+".join(f"'{n}'!G49" for n in segs)
        multiplo = "+".join(f"'{n}'!K50" for n in segs)
        puente = "+Consolidated!$K$42-SUM(Consolidated!$K$43:$K$48)"
        filas = [(5, "DCF (perpetuidad y múltiplo de salida)", "=MIN(Consolidated!O60:S64)", "=Consolidated!K52",
                  "=MAX(Consolidated!O60:S64)"),
                 (6, "DCF solo perpetuidad", None, f"=({perpetuo}{puente})/Shares!$E$14", None),
                 (7, "DCF solo múltiplo de salida", None,
                  f"=IF(ISNUMBER('{segs[0]}'!K47),({multiplo}{puente})/Shares!$E$14,\"--\")", None),
                 (8, "Comparables EV / EBITDA", f"=Comps!S{mi}", f"=Comps!S{me}", f"=Comps!S{ma}"),
                 (9, "Comparables EV / Ventas", f"=Comps!R{mi}", f"=Comps!R{me}", f"=Comps!R{ma}"),
                 (10, "Comparables PER", f"=Comps!T{mi}", f"=Comps!T{me}", f"=Comps!T{ma}"),
                 (11, "Cotización (52 semanas)", "=Comps!G12", "=Comps!F12", "=Comps!H12")]
        for f, t, bajo, central, alto in filas:
            h.poner(f, 2, t, "etiqueta")
            for c, x in ((3, bajo), (4, central), (5, alto)):
                if x:
                    h.poner(f, c, x, "", "usd")
            h.poner(f, 6, f'=IF(ISNUMBER(D{f}),D{f}/Entradas!$C$7-1,"--")', "", "pct")
        self.celdas.update(sintesis_dcf=("Síntesis", 5, 4), sintesis_dcf_bajo=("Síntesis", 5, 3), sintesis_dcf_alto=("Síntesis", 5, 5),
                           dcf_perpetuidad=("Síntesis", 6, 4), dcf_multiplo=("Síntesis", 7, 4),
                           comps_ebitda=("Síntesis", 8, 4), comps_ebitda_bajo=("Síntesis", 8, 3), comps_ebitda_alto=("Síntesis", 8, 5),
                           comps_ventas=("Síntesis", 9, 4), comps_per=("Síntesis", 10, 4), comps_per_bajo=("Síntesis", 10, 3),
                           comps_per_alto=("Síntesis", 10, 5))

    def _controles(self):
        h = self.libro.hoja("Controles")
        segs = [self._nombre_dcf(s) for s in self.d.segmentos]
        h.poner(2, 2, "Controles de coherencia", "titulo")
        h.poner(4, 2, "Control", "cabecera")
        h.poner(4, 3, "Resultado", "cabecera")
        h.poner(4, 4, "Detalle", "cabecera")
        controles = [
            ("Ventas por segmento = ventas consolidadas (FY0)", "=ABS(Segments!G5-IS!G5)<=0.005*ABS(IS!G5)", "Segments!G5 frente a IS!G5"),
            ("EBIT por segmento = EBIT consolidado (FY0)", f"=ABS(Segments!G{7 + len(self.d.segmentos)}-IS!G10)<=0.005*ABS(IS!G10)",
             "Con la fila de costes no asignados"),
            ("Balance cuadrado (FY0)", "=ABS(BS!G27)<=0.01*BS!G13", "Activo − (pasivo + patrimonio + minoritarios + temporal)"),
            ("Balance cuadrado (LTM)", "=ABS(BS!H27)<=0.01*BS!H13", ""),
            ("WACC mayor que el crecimiento a perpetuidad", "=WACC!F22>Entradas!C12", ""),
            ("Valor terminal < 85 % del EV (perpetuidad)", "=AND(" + ",".join(f"'{n}'!G52<0.85" for n in segs) + ")", "Por segmento"),
            ("Acciones diluidas ≥ básicas", "=Shares!E14>=Shares!E7", ""),
            ("Precio del DCF = Síntesis", "=Consolidated!K52=Síntesis!D5", ""),
            ("Convención de descuento", '=IF(Entradas!C14=1,"Mitad de año","Fin de año")', "La elige el analista (Entradas!C14)"),
        ]
        for t, formula in self.controles_extra:
            controles.append((t, formula, "Hoja LBO"))
        for i, (t, formula, detalle) in enumerate(controles):
            h.poner(5 + i, 2, t, "etiqueta")
            h.poner(5 + i, 3, formula)
            h.poner(5 + i, 4, detalle)
        h.poner(17, 2, "Correcciones respecto de las plantillas de origen", "seccion")
        correcciones = list(CORRECCIONES) + [
            ("E10", "TIR del LBO con los años del modelo (la plantilla tecleaba 5)"),
            ("E11", "Proveedores del LBO sobre ventas, como la plantilla: su nota (coste de ventas) no aplica en el caso de la dirección"),
            ("E13", "Acreción-dilución: el BPA recurrente no resta las comisiones únicas de la operación"),
            ("E21", "LBO: EBIT conservador calculado (la plantilla se referenciaba a sí misma)"),
            ("E22", "LBO: intangibles sin circularidad (compras proyectadas 0)"),
            ("E23", "LBO: signo de otros activos y pasivos a largo plazo en el flujo de caja"),
            ("E24", "LBO: amortización total de la deuda con los pagos obligatorios y el PIK"),
            ("E25", "LBO: tipo PIK en todos los años"),
            ("E26", "LBO: acciones diluidas con opciones y RSU"),
            ("E27", "LBO: la depreciación del inmovilizado es la del caso elegido (la plantilla mezclaba los casos)"),
            ("E28", "LBO: la amortización de las comisiones de financiación es gasto financiero no monetario"),
            ("E29", "LBO: «otros usos» como coste de la operación; con E27-E29 el balance pro forma cuadra (el de la plantilla no)"),
            ("E30", "LBO: la comprobación de la deuda, con tolerancia relativa (la igualdad exacta fallaba por el residuo iterativo)")]
        for i, (codigo, texto) in enumerate(correcciones):
            h.poner(18 + i, 2, codigo, "etiqueta")
            h.poner(18 + i, 3, texto)
        self.celdas.update({"control_" + str(i): ("Controles", 5 + i, 3) for i in range(len(controles))})
        self.controles = [(t, ("Controles", 5 + i, 3)) for i, (t, _, _) in enumerate(controles)]

    def _trazabilidad(self):
        h = self.libro.hoja("Trazabilidad")
        h.poner(2, 2, "Origen de cada dato de la SEC", "titulo")
        for c, t in ((2, "Celda"), (3, "Partida"), (4, "Concepto XBRL"), (5, "Periodo"), (6, "Filing (accession)"), (7, "Valor")):
            h.poner(4, c, t, "cabecera")
        for i, (hoja, celda, partida, concepto, periodo, origen, valor) in enumerate(self.trazas):
            f = 5 + i
            h.fila(f, 2, [f"{hoja}!{celda}", partida, concepto, periodo, origen])
            h.poner(f, 7, valor, "", "mn")


def _mas_un_anio(d: date) -> date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:  # 29 de febrero
        return d.replace(year=d.year + 1, day=28)


def _resta(a, b):
    return None if a is None or b is None else a - b


def _suma(a, b):
    return None if a is None or b is None else a + b


def _numero(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def avisos_de_calculo(marcadas: list[tuple], errores: list[tuple]) -> list[str]:
    """Avisos del cálculo del libro: celdas marcadas «--» por falta de datos y celdas que siguen en error."""
    from collections import Counter

    def por_hoja(celdas):
        return ", ".join(f"{h} ({n})" for h, n in Counter(k[0] for k in celdas).items())

    avisos = []
    if marcadas:
        avisos.append(f"Motor de valoración: {len(marcadas)} fórmulas sin datos de la SEC para algún ejercicio, marcadas «--» "
                      f"en el libro: {por_hoja(marcadas)}")
    if errores:
        avisos.append(f"Motor de valoración: {len(errores)} celdas en error en el libro: {por_hoja(errores)}; primeras: "
                      + ", ".join(f"{h}!{ref(f, c)}" for h, f, c in errores[:5]))
    return avisos


def construir(datos: DatosMotor, entradas: EntradasMotor) -> Modelo:
    """Libro del modelo, calculado en Python (mismas fórmulas que el .xlsx que se descarga) y sus salidas."""
    c = _Constructor(datos, entradas)
    libro = c.construir()
    valores, marcadas, errores = libro.calcular()
    leer = lambda clave: _numero(valores.get(c.celdas[clave])) if clave in c.celdas else None  # noqa: E731
    salidas = {k: valores.get(c.celdas[k]) if k.startswith("control_") else leer(k) for k in c.celdas}  # controles: True/False
    avisos = avisos_de_calculo(marcadas, errores)
    for nombre, celda in c.controles:
        v = valores.get(celda)
        if v is False:
            avisos.append(f"Motor de valoración: falla el control «{nombre}»")
    if not datos.comparables:
        avisos.append("Motor de valoración: sin comparables del analista, beta propia y valor terminal 100 % por perpetuidad")
    salidas["sensibilidad"] = [[_numero(valores.get(("Consolidated", f, k))) for k in range(15, 20)] for f in range(60, 65)]
    salidas["sensibilidad_wacc"] = [_numero(valores.get(("Consolidated", 59, k))) for k in range(15, 20)]
    salidas["sensibilidad_tgr"] = [_numero(valores.get(("Consolidated", f, 14))) for f in range(60, 65)]
    return Modelo(libro, valores, c.celdas, avisos, salidas)
