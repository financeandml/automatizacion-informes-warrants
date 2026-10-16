"""Tareas en segundo plano de la interfaz (C5): cargar los datos y generar el informe sin bloquear la pantalla.

Cada tarea corre en otro proceso (`concurrent.futures`, biblioteca estándar) y no toca Streamlit: el resultado o el
error se quedan aquí hasta que la sesión los recoge en la siguiente recarga. Así el analista puede ir a «Empresas y
versiones» o a «Configuración» mientras tanto. En otro proceso y no en un hilo: leer el XBRL, normalizar y generar el
PDF es Python puro que acapara el intérprete (GIL) y congelaba la página durante la carga. Los procesos se crean
una vez y quedan listos. Sin Streamlit, para probarlo con pytest (tests/test_render.py, con `EN_PROCESOS = False`).
"""

from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field

EN_PROCESOS = True  # False: hilos (los tests, para poder simular la red con monkeypatch)
_HILOS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="informe")
_procesos: ProcessPoolExecutor | None = None


def _enviar(funcion: Callable, *args, **kwargs) -> Future:
    global _procesos
    if not EN_PROCESOS:
        return _HILOS.submit(funcion, *args, **kwargs)
    for _ in range(2):  # si un proceso murió, el grupo queda roto: se crea otro una vez
        if _procesos is None:
            _procesos = ProcessPoolExecutor(max_workers=2)
        try:
            return _procesos.submit(funcion, *args, **kwargs)
        except BrokenProcessPool:
            _procesos = None
    raise RuntimeError("No se pudo arrancar el proceso de trabajo")


def _con_identidad() -> None:
    """En el proceso de trabajo: identidad de EDGAR del .env (el proceso no hereda la configuración de edgartools)."""
    from ..config import configurar_identidad

    configurar_identidad()


def cargar(version, almacen, con_ia: bool, comparables: list[str] | None) -> dict:
    """Datos de la SEC y del mercado de la versión, sin los borradores de la IA (llegan después)."""
    from ..informe import versionado

    _con_identidad()
    return versionado.datos_de_la_version(version, almacen, con_ia, comparables, borradores=False)


def con_borradores(datos: dict) -> dict:
    """Borradores de la IA de los apartados del analista, con el editor ya abierto (los más lentos)."""
    from ..informe import construir

    _con_identidad()
    return construir.con_borradores_ia(dict(datos), True)  # copia: la sesión sigue con los datos sin borradores


def componer(datos: dict, estimaciones, textos: dict, ajustes: dict) -> tuple[dict, str, bytes | None]:
    """Informe con lo que aportó el analista, su HTML (vista previa) y el libro de Excel: lo más pesado de cada cambio."""
    from ..informe import render, versionado
    from . import logica

    c = versionado.recomponer(datos, estimaciones, textos, ajustes)
    return c, render.html(c), logica.libro_del_motor(c)


def generar(version, almacen, datos: dict, emitir: bool):
    """PDF y libro de Excel del borrador y, si se pide, la emisión (la versión ya no cambia)."""
    from ..informe import versionado

    _con_identidad()
    preparada, _ = versionado.preparar(version, almacen, datos=datos)
    if not emitir:
        return preparada
    emitida = preparada.emitir()
    almacen.guardar(emitida)
    return emitida


@dataclass
class Tarea:
    descripcion: str
    futuro: Future
    datos: dict = field(default_factory=dict)  # lo que la sesión necesita al recogerla (p. ej. la versión)


class Tareas:
    """Las tareas de una sesión, por clave («datos», «informe»): como mucho una en curso por clave."""

    def __init__(self) -> None:
        self._tareas: dict[str, Tarea] = {}

    def lanzar(self, clave: str, descripcion: str, funcion: Callable, *args, datos: dict | None = None, **kwargs) -> bool:
        """Arranca la tarea si no hay otra en curso con la misma clave; devuelve si la ha arrancado."""
        if self.en_curso(clave):
            return False
        self._tareas[clave] = Tarea(descripcion, _enviar(funcion, *args, **kwargs), datos or {})
        return True

    def en_curso(self, clave: str) -> bool:
        tarea = self._tareas.get(clave)
        return tarea is not None and not tarea.futuro.done()

    def descripciones_en_curso(self) -> list[str]:
        return [t.descripcion for t in self._tareas.values() if t.descripcion and not t.futuro.done()]

    def claves(self) -> list[str]:
        return list(self._tareas)

    def hay_terminadas(self) -> bool:
        return any(t.futuro.done() for t in self._tareas.values())

    def recoger(self, clave: str) -> tuple[Tarea, object, BaseException | None] | None:
        """(tarea, resultado, error) de la tarea terminada, que deja de estar aquí; None si no hay o sigue en curso."""
        tarea = self._tareas.get(clave)
        if tarea is None or not tarea.futuro.done():
            return None
        del self._tareas[clave]
        error = tarea.futuro.exception()
        return tarea, (None if error else tarea.futuro.result()), error
