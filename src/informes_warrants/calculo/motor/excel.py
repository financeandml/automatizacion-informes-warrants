"""Evaluador determinista de fórmulas de Excel: el segundo cálculo del motor de valoración (B1).

El modelo de valoración es un libro de Excel con fórmulas vivas. Este módulo lo calcula en Python con la misma
semántica que Excel para las funciones que usan las plantillas (`IF`, `ISERROR`, `IFERROR`, `AVERAGE`, `MEDIAN`,
`MIN`, `MAX`, `SUM`, `SUMPRODUCT`, `VLOOKUP`, `CHOOSE`, `YEARFRAC`…), referencias entre hojas, nombres definidos,
vínculos externos con sus valores guardados, tablas de datos (sensibilidades) y referencias circulares con
cálculo iterativo (100 iteraciones, cambio máximo 0,001, como Excel por defecto).

Orden de cálculo: grafo de dependencias de todas las celdas con fórmula y componentes fuertemente conexas (Tarjan,
sin recursión): cada componente se calcula cuando ya lo están sus dependencias; las circulares, por iteración.

Se valida contra Excel: con las plantillas originales, el evaluador reproduce los valores que Excel guardó en cada
celda (`tests/test_motor.py`). Ningún repositorio base trae un evaluador (inventario); openpyxl (MIT) solo aporta el
tokenizador de fórmulas.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from openpyxl.formula import Tokenizer
from openpyxl.formula.tokenizer import Token
from openpyxl.utils import column_index_from_string, get_column_letter

ORIGEN_EXCEL = datetime(1899, 12, 30)
ITERACIONES, CAMBIO_MAXIMO = 100, 0.001  # cálculo iterativo de Excel por defecto


@dataclass(frozen=True)
class Error:
    """Valor de error de Excel (#DIV/0!, #N/A, #VALUE!, #REF!, #NUM!, #NAME?)."""

    codigo: str

    def __repr__(self):
        return self.codigo


DIV0, NA, VALOR, REF, NUM, NOMBRE = (Error(c) for c in ("#DIV/0!", "#N/A", "#VALUE!", "#REF!", "#NUM!", "#NAME?"))
ERRORES = {e.codigo: e for e in (DIV0, NA, VALOR, REF, NUM, NOMBRE, Error("#NULL!"))}


class _Rango:
    """Valores de un rango (filas × columnas) pasados a una función."""

    def __init__(self, filas: list[list]):
        self.filas = filas

    def valores(self):
        return [v for fila in self.filas for v in fila]


def _escalar(v):
    """Una referencia a una sola celda pasada a una función que espera un valor."""
    if isinstance(v, _Rango):
        celdas = v.valores()
        return celdas[0] if len(celdas) == 1 else VALOR
    return v


def serial(v):
    """Fechas como número de serie de Excel."""
    if isinstance(v, datetime):
        return (v - ORIGEN_EXCEL).total_seconds() / 86400
    if isinstance(v, date):
        return float((v - ORIGEN_EXCEL.date()).days)
    return v


# ---------------------------------------------------------------------------------------------------------- referencias

_CELDA = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d+)$")
_HOJA = re.compile(r"^(?:\[(\d+)\])?(.+)$")


def _celda(texto: str) -> tuple[int, int]:
    m = _CELDA.match(texto)
    if not m:
        raise ValueError(texto)
    return int(m.group(2)), column_index_from_string(m.group(1).upper())


def partir_referencia(texto: str, hoja_actual: str):
    """'Hoja'!A1:B2 → (libro_externo | None, hoja, f1, c1, f2, c2)."""
    externo, hoja = None, hoja_actual
    if "!" in texto:
        prefijo, texto = texto.rsplit("!", 1)
        prefijo = prefijo.strip("'")
        m = _HOJA.match(prefijo)
        if prefijo.startswith("[") or (m and m.group(1)):
            m = re.match(r"^'?\[(\d+)\](.+?)'?$", prefijo)
            externo, hoja = int(m.group(1)), m.group(2).strip("'")
        else:
            hoja = prefijo.replace("''", "'")
    partes = texto.split(":")
    f1, c1 = _celda(partes[0])
    f2, c2 = _celda(partes[1]) if len(partes) > 1 else (f1, c1)
    return externo, hoja, min(f1, f2), min(c1, c2), max(f1, f2), max(c1, c2)


# ---------------------------------------------------------------------------------------------------------------- parser

_PRECEDENCIA = {"=": 0, "<>": 0, "<": 0, ">": 0, "<=": 0, ">=": 0, "&": 1, "+": 2, "-": 2, "*": 3, "/": 3, "^": 4}


class _Parser:
    def __init__(self, formula: str, hoja: str):
        self.hoja = hoja
        self.tokens = [t for t in Tokenizer(formula).items if t.type != Token.WSPACE]
        self.i = 0

    def _ver(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _tomar(self):
        t = self.tokens[self.i]
        self.i += 1
        return t

    def arbol(self):
        nodo = self._expresion(0)
        if self._ver() is not None:
            raise ValueError(f"fórmula no reconocida tras {self._ver().value!r}")
        return nodo

    def _expresion(self, minimo: int):
        izquierda = self._unario()
        while True:
            t = self._ver()
            if t is None or t.type != Token.OP_IN or t.value not in _PRECEDENCIA or _PRECEDENCIA[t.value] < minimo:
                return izquierda
            self._tomar()
            derecha = self._expresion(_PRECEDENCIA[t.value] + 1)  # asociatividad por la izquierda (también ^, como Excel)
            izquierda = ("bin", t.value, izquierda, derecha)

    def _unario(self):
        t = self._ver()
        if t is not None and t.type == Token.OP_PRE:
            self._tomar()
            nodo = self._unario()
            return ("neg", nodo) if t.value == "-" else nodo
        nodo = self._primario()
        while self._ver() is not None and self._ver().type == Token.OP_POST:
            self._tomar()
            nodo = ("pct", nodo)
        return nodo

    def _primario(self):
        t = self._tomar()
        if t.type == Token.OPERAND:
            if t.subtype == Token.NUMBER:
                return ("num", float(t.value))
            if t.subtype == Token.TEXT:
                return ("str", t.value[1:-1].replace('""', '"'))
            if t.subtype == Token.LOGICAL:
                return ("bool", t.value.upper() == "TRUE")
            if t.subtype == Token.ERROR:
                return ("err", ERRORES.get(t.value, VALOR))
            texto = t.value
            if _es_referencia(texto):
                return ("ref", *partir_referencia(texto, self.hoja))
            return ("nombre", texto)
        if t.type == Token.FUNC and t.subtype == Token.OPEN:
            nombre = t.value[:-1].upper().replace("_XLFN.", "")
            argumentos = []
            if self._ver().type == Token.FUNC and self._ver().subtype == Token.CLOSE:
                self._tomar()
                return ("func", nombre, argumentos)
            while True:
                if self._ver().type == Token.SEP:
                    argumentos.append(("vacio",))
                else:
                    argumentos.append(self._expresion(0))
                t = self._tomar()
                if t.type == Token.FUNC and t.subtype == Token.CLOSE:
                    return ("func", nombre, argumentos)
                if t.type != Token.SEP:
                    raise ValueError(f"separador esperado en {nombre}")
                if self._ver().type == Token.FUNC and self._ver().subtype == Token.CLOSE:
                    argumentos.append(("vacio",))
        if t.type == Token.PAREN and t.subtype == Token.OPEN:
            nodo = self._expresion(0)
            self._tomar()
            return nodo
        raise ValueError(f"token inesperado {t.value!r}")


def _es_referencia(texto: str) -> bool:
    base = texto.rsplit("!", 1)[-1]
    return all(_CELDA.match(p) for p in base.split(":"))


def referencias(nodo):
    """Todas las referencias de un árbol (las dos ramas de los IF: grafo de dependencias conservador)."""
    if not isinstance(nodo, tuple):
        return
    if nodo[0] in ("ref", "nombre"):
        yield nodo
    for hijo in nodo[1:]:
        if isinstance(hijo, tuple):
            yield from referencias(hijo)
        elif isinstance(hijo, list):
            for h in hijo:
                yield from referencias(h)


# --------------------------------------------------------------------------------------------------------------- libro

@dataclass
class TablaDeDatos:
    """Tabla de datos de Excel (análisis «Y si»): el resultado de cada celda es la fórmula de la esquina con la celda
    de entrada de fila y la de columna sustituidas por la cabecera de su columna y de su fila."""

    hoja: str
    f1: int
    c1: int
    f2: int
    c2: int
    entrada_fila: tuple | None  # (hoja, fila, col) que toma los valores de la fila superior
    entrada_columna: tuple | None  # la que toma los valores de la columna izquierda


@dataclass
class Libro:
    """Contenido de un libro: constantes y fórmulas por celda, nombres definidos y vínculos externos guardados."""

    celdas: dict[tuple[str, int, int], object] = field(default_factory=dict)  # valor o fórmula ("=…")
    nombres: dict[str, str] = field(default_factory=dict)  # nombre (en minúsculas) → referencia ("'Hoja'!$A$1")
    externos: dict[int, dict[tuple[str, int, int], object]] = field(default_factory=dict)
    tablas: list[TablaDeDatos] = field(default_factory=list)
    hojas: list[str] = field(default_factory=list)

    @classmethod
    def desde_openpyxl(cls, wb) -> "Libro":
        from openpyxl.worksheet.formula import ArrayFormula, DataTableFormula

        libro = cls(hojas=[ws.title for ws in wb.worksheets])
        for nombre, definido in wb.defined_names.items():
            libro.nombres[nombre.lower()] = definido.attr_text
        for i, enlace in enumerate(getattr(wb, "_external_links", []) or [], start=1):
            datos = {}
            libro_ext = getattr(enlace, "externalBook", None)
            if libro_ext is not None and libro_ext.sheetDataSet is not None:
                nombres_hojas = ([s if isinstance(s, str) else s.val for s in libro_ext.sheetNames.sheetName]
                                 if libro_ext.sheetNames else [])
                for hoja_datos in libro_ext.sheetDataSet.sheetData:
                    hoja = nombres_hojas[hoja_datos.sheetId] if hoja_datos.sheetId < len(nombres_hojas) else str(hoja_datos.sheetId)
                    for fila in hoja_datos.row or []:
                        for celda in fila.cell or []:
                            f, c = _celda(celda.r)
                            v = celda.v
                            if celda.t == "n" or (celda.t is None and v is not None):
                                try:
                                    v = float(v)
                                except (TypeError, ValueError):
                                    pass
                            datos[(hoja, f, c)] = v
            libro.externos[i] = datos
        for ws in wb.worksheets:
            for fila in ws.iter_rows():
                for c in fila:
                    v = c.value
                    if v is None:
                        continue
                    if isinstance(v, DataTableFormula):
                        _, _, f1, c1, f2, c2 = partir_referencia(v.ref, ws.title)
                        r1 = partir_referencia(v.r1, ws.title)[1:4] if v.r1 else None
                        r2 = partir_referencia(v.r2, ws.title)[1:4] if v.r2 else None
                        dos = str(v.dt2D) in ("1", "True", "true")
                        fila_entrada = r1 if dos or str(v.dtr) in ("1", "True", "true") else None
                        col_entrada = (r2 if dos else (r1 if fila_entrada is None else None))
                        libro.tablas.append(TablaDeDatos(ws.title, f1, c1, f2, c2, fila_entrada, col_entrada))
                        continue
                    if isinstance(v, ArrayFormula):
                        v = v.text
                    libro.celdas[(ws.title, c.row, c.column)] = v
        return libro


# ----------------------------------------------------------------------------------------------------------- evaluación

def _numero(v):
    """Coerción aritmética de Excel."""
    if isinstance(v, Error):
        return v
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (datetime, date)):
        return serial(v)
    if isinstance(v, str):
        try:
            return float(v.strip().rstrip("%")) / (100 if v.strip().endswith("%") else 1)
        except ValueError:
            return VALOR
    return VALOR


def _texto(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    return str(v)


def _comparar(op, a, b):
    if isinstance(a, Error):
        return a
    if isinstance(b, Error):
        return b
    a, b = serial(a), serial(b)
    if a is None:
        a = "" if isinstance(b, str) else (False if isinstance(b, bool) else 0.0)
    if b is None:
        b = "" if isinstance(a, str) else (False if isinstance(a, bool) else 0.0)
    rango = lambda x: 2 if isinstance(x, bool) else 1 if isinstance(x, str) else 0  # noqa: E731  número < texto < lógico
    if rango(a) != rango(b):
        ka, kb = rango(a), rango(b)
    elif isinstance(a, str):
        ka, kb = a.lower(), b.lower()
    else:  # Excel compara los números con 15 cifras significativas
        ka, kb = _quince(float(a)), _quince(float(b))
    return {"=": ka == kb, "<>": ka != kb, "<": ka < kb, ">": ka > kb, "<=": ka <= kb, ">=": ka >= kb}[op]


def _quince(x: float) -> float:
    return float(f"{x:.15g}") if math.isfinite(x) else x


def _numeros(argumentos, *, logicos_directos=True):
    """Números de los argumentos de SUM/AVERAGE/MIN/MAX/MEDIAN: en rangos se ignoran textos, lógicos y vacías."""
    salida = []
    for a in argumentos:
        if isinstance(a, _Rango):
            for v in a.valores():
                if isinstance(v, Error):
                    return v
                if isinstance(v, (datetime, date)):
                    salida.append(serial(v))
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    salida.append(float(v))
        elif a is None:
            continue
        else:
            n = _numero(a) if (logicos_directos or not isinstance(a, bool)) else None
            if isinstance(n, Error):
                return n
            if n is not None:
                salida.append(n)
    return salida


def _yearfrac(inicio, fin, base=0):
    """YEARFRAC de Excel (base 0, US 30/360, y bases 1-4)."""
    d1, d2 = _fecha(inicio), _fecha(fin)
    if isinstance(d1, Error) or isinstance(d2, Error):
        return VALOR
    if d1 > d2:
        d1, d2 = d2, d1
    base = int(_numero(base) or 0)
    if base == 0:
        def ultimo_febrero(d):
            return d.month == 2 and (date(d.year, 3, 1) - d).days == 1
        dia1, dia2 = d1.day, d2.day
        if ultimo_febrero(d1) and ultimo_febrero(d2):
            dia2 = 30
        if dia1 == 31 or ultimo_febrero(d1):
            dia1 = 30
        if dia1 == 30 and dia2 == 31:
            dia2 = 30
        return ((d2.year - d1.year) * 360 + (d2.month - d1.month) * 30 + (dia2 - dia1)) / 360
    dias = (d2 - d1).days
    if base == 2:
        return dias / 360
    if base == 3:
        return dias / 365
    if base == 4:
        dia1, dia2 = min(d1.day, 30), min(d2.day, 30)
        return ((d2.year - d1.year) * 360 + (d2.month - d1.month) * 30 + (dia2 - dia1)) / 360
    if d1.year == d2.year:  # base 1: real / real
        return dias / (366 if _bisiesto(d1.year) else 365)
    anios = range(d1.year, d2.year + 1)
    media = sum(366 if _bisiesto(a) else 365 for a in anios) / len(anios)
    return dias / media


def _bisiesto(a):
    return a % 4 == 0 and (a % 100 != 0 or a % 400 == 0)


def _fecha(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    n = _numero(v)
    if isinstance(n, Error):
        return n
    return (ORIGEN_EXCEL + __import__("datetime").timedelta(days=int(n))).date()


def _redondear(x, d):
    factor = 10 ** d
    return math.floor(abs(x) * factor + 0.5) / factor * (1 if x >= 0 else -1)


class Evaluador:
    """Calcula todas las celdas con fórmula de un `Libro`."""

    def __init__(self, libro: Libro, iterativo: bool = True, iniciales: dict | None = None):
        """`iniciales`: valores de partida de las celdas circulares (Excel itera desde los últimos guardados)."""
        self.libro = libro
        self.iterativo = iterativo
        self.iniciales = iniciales or {}
        self.valores: dict = {}
        self.arboles: dict = {}
        self.circulares: set = set()
        self.errores_formula: dict = {}
        for clave, v in libro.celdas.items():
            if isinstance(v, str) and v.startswith("="):
                try:
                    self.arboles[clave] = _Parser(v, clave[0]).arbol()
                except Exception as e:  # noqa: BLE001  (una fórmula que no se reconoce es #NAME?, como en Excel)
                    self.errores_formula[clave] = str(e)
                    self.arboles[clave] = ("err", NOMBRE)
            else:
                self.valores[clave] = v

    # -- grafo
    def _dependencias(self, clave):
        deps = set()
        for r in referencias(self.arboles[clave]):
            resuelta = self._resolver_nombre(r) if r[0] == "nombre" else r
            if resuelta is None or resuelta[1] is not None:
                continue
            _, _, hoja, f1, c1, f2, c2 = resuelta
            if (f2 - f1 + 1) * (c2 - c1 + 1) <= 64:
                for f in range(f1, f2 + 1):
                    for c in range(c1, c2 + 1):
                        if (hoja, f, c) in self.arboles:
                            deps.add((hoja, f, c))
            else:
                deps.update(k for k in self.arboles if k[0] == hoja and f1 <= k[1] <= f2 and c1 <= k[2] <= c2)
        return deps

    def _resolver_nombre(self, nodo):
        texto = self.libro.nombres.get(nodo[1].lower())
        if texto is None or "#REF!" in texto:
            return None
        try:
            return ("ref", *partir_referencia(texto.replace("$", ""), ""))
        except (ValueError, AttributeError):
            return None

    def _orden(self):
        """Componentes fuertemente conexas en orden de cálculo (Tarjan iterativo)."""
        grafo = {k: self._dependencias(k) for k in self.arboles}
        indice, bajo, en_pila, pila, componentes, contador = {}, {}, set(), [], [], [0]
        for inicio in grafo:
            if inicio in indice:
                continue
            trabajo = [(inicio, iter(grafo[inicio]))]
            indice[inicio] = bajo[inicio] = contador[0]
            contador[0] += 1
            pila.append(inicio)
            en_pila.add(inicio)
            while trabajo:
                nodo, hijos = trabajo[-1]
                avanzado = False
                for hijo in hijos:
                    if hijo not in indice:
                        indice[hijo] = bajo[hijo] = contador[0]
                        contador[0] += 1
                        pila.append(hijo)
                        en_pila.add(hijo)
                        trabajo.append((hijo, iter(grafo[hijo])))
                        avanzado = True
                        break
                    if hijo in en_pila:
                        bajo[nodo] = min(bajo[nodo], indice[hijo])
                if avanzado:
                    continue
                trabajo.pop()
                if trabajo:
                    bajo[trabajo[-1][0]] = min(bajo[trabajo[-1][0]], bajo[nodo])
                if bajo[nodo] == indice[nodo]:
                    comp = []
                    while True:
                        x = pila.pop()
                        en_pila.discard(x)
                        comp.append(x)
                        if x == nodo:
                            break
                    componentes.append((comp, len(comp) > 1 or nodo in grafo[nodo]))
        return componentes

    def calcular(self) -> dict:
        self._componentes = self._orden()
        for comp, circular in self._componentes:
            self._calcular_componente(comp, circular)
        for tabla in self.libro.tablas:
            self._tabla(tabla)
        if self.libro.tablas:  # lo que lee los resultados de las tablas (p. ej. la sensibilidad consolidada)
            celdas = {(t.hoja, f, c) for t in self.libro.tablas for f in range(t.f1, t.f2 + 1) for c in range(t.c1, t.c2 + 1)}
            dependientes = self._aguas_abajo(celdas)
            for comp, circular in self._componentes:
                if any(k in dependientes for k in comp):
                    self._calcular_componente(comp, circular)
        return self.valores

    def _calcular_componente(self, comp, circular):
        if not circular:
            self.valores[comp[0]] = self._evaluar(self.arboles[comp[0]], comp[0][0])
            return
        self.circulares.update(comp)
        if not self.iterativo:
            for k in comp:
                self.valores[k] = Error("#CIRC")
            return
        for k in comp:
            inicial = self.iniciales.get(k, 0.0)
            self.valores.setdefault(k, inicial if isinstance(inicial, (int, float)) and not isinstance(inicial, bool) else 0.0)
        for _ in range(ITERACIONES):
            cambio = 0.0
            for k in reversed(comp):
                anterior = self.valores.get(k)
                nuevo = self._evaluar(self.arboles[k], k[0])
                self.valores[k] = nuevo
                if isinstance(nuevo, float) and isinstance(anterior, float):
                    cambio = max(cambio, abs(nuevo - anterior))
                elif nuevo != anterior:
                    cambio = math.inf
            if cambio < CAMBIO_MAXIMO:
                break

    def _tabla(self, t: TablaDeDatos):
        """Sustituye las celdas de entrada, recalcula lo que depende de ellas y guarda el resultado en la tabla."""
        esquina = (t.hoja, t.f1 - 1, t.c1 - 1)
        entradas = [e for e in (t.entrada_fila, t.entrada_columna) if e]
        originales = {e: self.valores.get(e) for e in entradas}
        dependientes = self._aguas_abajo(set(entradas))
        afectadas = [(comp, circular) for comp, circular in self._componentes if any(k in dependientes for k in comp)]
        resultados = {}
        for f in range(t.f1, t.f2 + 1):
            for c in range(t.c1, t.c2 + 1):
                if t.entrada_fila:
                    self.valores[t.entrada_fila] = self.valores.get((t.hoja, t.f1 - 1, c))
                if t.entrada_columna:
                    self.valores[t.entrada_columna] = self.valores.get((t.hoja, f, t.c1 - 1))
                for comp, circular in afectadas:
                    self._calcular_componente(comp, circular)
                resultados[(t.hoja, f, c)] = self.valores.get(esquina)
        self.valores.update(originales)
        for comp, circular in afectadas:
            self._calcular_componente(comp, circular)
        self.valores.update(resultados)

    def _aguas_abajo(self, origen: set) -> set:
        inversa = {}
        for k in self.arboles:
            for d in self._dependencias(k):
                inversa.setdefault(d, set()).add(k)
        for e in origen:
            hoja, f, c = e
            for k in self.arboles:  # las entradas suelen ser constantes: dependientes directos por referencia
                if any(r[0] == "ref" and r[2] == hoja and r[3] <= f <= r[5] and r[4] <= c <= r[6] for r in referencias(self.arboles[k])):
                    inversa.setdefault(e, set()).add(k)
        salida, pendientes = set(), list(origen)
        while pendientes:
            x = pendientes.pop()
            for y in inversa.get(x, ()):
                if y not in salida:
                    salida.add(y)
                    pendientes.append(y)
        return salida

    # -- evaluación de un árbol
    def _rango(self, nodo):
        _, externo, hoja, f1, c1, f2, c2 = nodo
        if externo is not None:
            datos = self.libro.externos.get(externo, {})
            return [[datos.get((hoja, f, c)) for c in range(c1, c2 + 1)] for f in range(f1, f2 + 1)]
        if hoja not in self.libro.hojas and self.libro.hojas:
            return REF
        return [[self.valores.get((hoja, f, c)) for c in range(c1, c2 + 1)] for f in range(f1, f2 + 1)]

    def _evaluar(self, nodo, hoja, como_rango=False):
        tipo = nodo[0]
        if tipo == "num":
            return nodo[1]
        if tipo in ("str", "bool"):
            return nodo[1]
        if tipo == "err":
            return nodo[1]
        if tipo == "vacio":
            return None
        if tipo == "nombre":
            resuelta = self._resolver_nombre(nodo)
            if resuelta is None:
                return REF if nodo[1].lower() in self.libro.nombres else NOMBRE
            return self._evaluar(resuelta, hoja, como_rango)
        if tipo == "ref":
            filas = self._rango(nodo)
            if isinstance(filas, Error):
                return filas
            if como_rango:
                return _Rango(filas)
            if len(filas) == 1 and len(filas[0]) == 1:
                return filas[0][0]
            return VALOR  # un rango en una operación escalar (Excel haría intersección implícita)
        if tipo == "neg":
            v = _numero(self._evaluar(nodo[1], hoja))
            return v if isinstance(v, Error) else -v
        if tipo == "pct":
            v = _numero(self._evaluar(nodo[1], hoja))
            return v if isinstance(v, Error) else v / 100
        if tipo == "bin":
            return self._binario(nodo[1], self._evaluar(nodo[2], hoja), self._evaluar(nodo[3], hoja))
        if tipo == "func":
            return self._funcion(nodo[1], nodo[2], hoja)
        raise ValueError(tipo)

    def _binario(self, op, a, b):
        if op in ("=", "<>", "<", ">", "<=", ">="):
            return _comparar(op, a, b)
        if op == "&":
            if isinstance(a, Error):
                return a
            if isinstance(b, Error):
                return b
            return _texto(a) + _texto(b)
        x, y = _numero(a), _numero(b)
        if isinstance(x, Error):
            return x
        if isinstance(y, Error):
            return y
        if op == "+":
            return x + y
        if op == "-":
            return x - y
        if op == "*":
            return x * y
        if op == "/":
            return DIV0 if y == 0 else x / y
        if op == "^":
            try:
                r = x ** y
            except (OverflowError, ZeroDivisionError):
                return NUM
            return NUM if isinstance(r, complex) else float(r)
        raise ValueError(op)

    def _funcion(self, nombre, args, hoja):
        ev = lambda n: self._evaluar(n, hoja)  # noqa: E731
        rg = lambda n: self._evaluar(n, hoja, como_rango=n[0] in ("ref", "nombre"))  # noqa: E731
        if nombre == "IF":
            cond = ev(args[0])
            if isinstance(cond, Error):
                return cond
            c = _numero(cond) if not isinstance(cond, bool) else cond
            if isinstance(c, Error):
                return VALOR
            if c:
                return ev(args[1]) if len(args) > 1 else True
            return ev(args[2]) if len(args) > 2 else False
        if nombre in ("IFERROR", "IFNA"):
            v = ev(args[0])
            atrapa = isinstance(v, Error) and (nombre == "IFERROR" or v == NA)
            return ev(args[1]) if atrapa else v
        if nombre == "ISERROR":
            return isinstance(ev(args[0]), Error)
        if nombre == "ISNUMBER":
            v = ev(args[0])
            return isinstance(v, (int, float)) and not isinstance(v, bool)
        if nombre == "CHOOSE":
            i = _numero(ev(args[0]))
            if isinstance(i, Error):
                return i
            i = int(i)
            return ev(args[i]) if 1 <= i < len(args) else VALOR
        if nombre in ("AND", "OR"):
            valores = []
            for a in args:
                v = rg(a)
                if isinstance(v, Error):
                    return v
                valores += [x for x in v.valores() if isinstance(x, (bool, int, float))] if isinstance(v, _Rango) else [v]
            valores = [bool(_numero(v)) if not isinstance(v, bool) else v for v in valores]
            return all(valores) if nombre == "AND" else any(valores)
        if nombre == "NOT":
            v = ev(args[0])
            return v if isinstance(v, Error) else not bool(_numero(v))
        valores = [rg(a) for a in args]
        for v in valores:
            if isinstance(v, Error):
                return v
        if nombre in ("SUM", "AVERAGE", "MIN", "MAX", "MEDIAN", "COUNT"):
            nums = _numeros(valores)
            if isinstance(nums, Error):
                return nums
            if nombre == "SUM":
                return math.fsum(nums)
            if nombre == "COUNT":
                return float(len(nums))
            if not nums:
                return DIV0 if nombre in ("AVERAGE", "MEDIAN") and nombre == "AVERAGE" else (0.0 if nombre in ("MIN", "MAX") else NUM)
            if nombre == "AVERAGE":
                return math.fsum(nums) / len(nums)
            if nombre == "MIN":
                return min(nums)
            if nombre == "MAX":
                return max(nums)
            ordenados = sorted(nums)
            n = len(ordenados)
            return ordenados[n // 2] if n % 2 else (ordenados[n // 2 - 1] + ordenados[n // 2]) / 2
        if nombre == "SUMPRODUCT":
            listas = [v.valores() if isinstance(v, _Rango) else [v] for v in valores]
            if len({len(x) for x in listas}) != 1:
                return VALOR
            total = 0.0
            for fila in zip(*listas, strict=True):
                if any(isinstance(x, Error) for x in fila):
                    return next(x for x in fila if isinstance(x, Error))
                producto = 1.0
                for x in fila:
                    producto *= float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else 0.0
                total += producto
            return total
        if nombre == "VLOOKUP":
            buscado, tabla, columna = _escalar(valores[0]), valores[1], _numero(_escalar(valores[2]))
            modo = _escalar(valores[3]) if len(valores) > 3 else None
            exacta = len(valores) < 4 or not bool(_numero(modo) if modo is not None else 0)
            if not isinstance(tabla, _Rango) or isinstance(columna, Error):
                return VALOR
            columna = int(columna)
            if columna < 1 or columna > len(tabla.filas[0]):
                return REF
            if exacta:
                for fila in tabla.filas:
                    if _comparar("=", fila[0], buscado) is True and fila[0] is not None:
                        return fila[columna - 1]
                return NA
            mejor = None
            for fila in tabla.filas:
                if fila[0] is None or _comparar("<=", fila[0], buscado) is not True:
                    break
                mejor = fila
            return mejor[columna - 1] if mejor else NA
        if nombre == "YEARFRAC":
            return _yearfrac(_escalar(valores[0]), _escalar(valores[1]), _escalar(valores[2]) if len(valores) > 2 else 0)
        if nombre == "ABS":
            v = _numero(_escalar(valores[0]))
            return v if isinstance(v, Error) else abs(v)
        if nombre == "ROUND":
            v, d = _numero(_escalar(valores[0])), _numero(_escalar(valores[1]))
            return v if isinstance(v, Error) else (d if isinstance(d, Error) else _redondear(v, int(d)))
        return NOMBRE


def evaluar(libro: Libro) -> dict:
    return Evaluador(libro).calcular()


def cargar(ruta) -> tuple[Libro, dict]:
    """(libro con fórmulas, valores guardados por Excel) de un .xlsx."""
    import openpyxl

    con_formulas = openpyxl.load_workbook(ruta, data_only=False)
    guardados = openpyxl.load_workbook(ruta, data_only=True)
    valores = {}
    for ws in guardados.worksheets:
        for fila in ws.iter_rows():
            for c in fila:
                if c.value is not None:
                    valores[(ws.title, c.row, c.column)] = c.value
    return Libro.desde_openpyxl(con_formulas), valores


def iguales(a, b, tolerancia=1e-9) -> bool:
    """Igualdad de valores de Excel (relativa en números; fechas como serie; vacío = 0 o texto vacío)."""
    a, b = serial(a), serial(b)
    if isinstance(a, Error) or isinstance(b, Error):
        return str(a) == str(b) or (isinstance(a, Error) and isinstance(b, str) and b == a.codigo) or \
            (isinstance(b, Error) and isinstance(a, str) and a == b.codigo)
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=tolerancia, abs_tol=1e-9)
    if a in (None, "") and b in (None, "", 0, 0.0):
        return True
    if b in (None, "") and a in (None, "", 0, 0.0):
        return True
    return a == b


def diferencias(libro: Libro, calculados: dict, referencia: dict, tolerancia=1e-9) -> list[tuple]:
    """Celdas con fórmula cuyo valor calculado no coincide con el de referencia: [(clave, calculado, referencia)]."""
    salida = []
    claves = [k for k, v in libro.celdas.items() if isinstance(v, str) and v.startswith("=")]
    claves += [(t.hoja, f, c) for t in libro.tablas for f in range(t.f1, t.f2 + 1) for c in range(t.c1, t.c2 + 1)]
    for k in claves:
        if not iguales(calculados.get(k), referencia.get(k), tolerancia):
            salida.append((k, calculados.get(k), referencia.get(k)))
    return salida


def a1(hoja: str, fila: int, col: int) -> str:
    return f"'{hoja}'!{get_column_letter(col)}{fila}"
