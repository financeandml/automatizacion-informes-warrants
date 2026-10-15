"""Tareas en segundo plano de la interfaz (C5): cargar los datos y generar el informe sin bloquear la pantalla.

Cada tarea corre en un hilo (`concurrent.futures`, biblioteca estándar) y no toca Streamlit: el resultado o el error
se quedan aquí hasta que la sesión los recoge en la siguiente recarga. Así el analista puede ir a «Empresas y
versiones» o a «Configuración» mientras tanto. Sin Streamlit, para probarlo con pytest (tests/test_render.py).
"""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field

_EJECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="informe")


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
        self._tareas[clave] = Tarea(descripcion, _EJECUTOR.submit(funcion, *args, **kwargs), datos or {})
        return True

    def en_curso(self, clave: str) -> bool:
        tarea = self._tareas.get(clave)
        return tarea is not None and not tarea.futuro.done()

    def descripciones_en_curso(self) -> list[str]:
        return [t.descripcion for t in self._tareas.values() if not t.futuro.done()]

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
