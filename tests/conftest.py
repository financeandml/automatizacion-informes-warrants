import pytest


@pytest.fixture(autouse=True)
def tareas_en_hilos(monkeypatch):
    """Las tareas de la interfaz van en otro proceso; en los tests, en hilos, para poder simular la red."""
    from informes_warrants.ui import tareas

    monkeypatch.setattr(tareas, "EN_PROCESOS", False)
