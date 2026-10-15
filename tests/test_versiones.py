import sqlite3

import pytest

from informes_warrants.almacenamiento.almacen import Almacen
from informes_warrants.almacenamiento.deteccion import version_para_filing
from informes_warrants.almacenamiento.versiones import Estado, TransicionInvalida, Version, comparar


def _version(**kw):
    base = dict(ticker="AAPL", ejercicio=2026, periodo="Q3", revision=1, accession="0000320193-26-000020",
                fecha_filing="2026-07-31", contenido={"textos": {"tesis": "Tesis completa."}})
    return Version(**{**base, **kw})


def test_etiqueta_por_ejercicio_fiscal():
    assert _version().etiqueta == "AAPL · FY2026 Q3 · v1"
    assert _version(periodo="FY", revision=2).etiqueta == "AAPL · FY2026 · v2"


def test_ciclo_de_vida():
    v = _version().confirmar()
    assert v.estado == Estado.BORRADOR
    emitida = v.emitir()
    assert emitida.estado == Estado.EMITIDA and emitida.emitida
    with pytest.raises(TransicionInvalida):
        emitida.descartar()
    revision = emitida.nueva_revision()
    assert (revision.revision, revision.estado) == (2, Estado.BORRADOR)


def test_se_emite_con_apartados_pendientes_y_se_avisa():
    """Decisión del usuario (2026-10-14): los pendientes avisan, no bloquean; se completan en una revisión nueva."""
    v = _version(contenido={"textos": {"tesis": "[[ANALISTA: escribe la tesis]]"}}).confirmar()
    assert any("1 apartados" in a for a in v.avisos())
    emitida = v.emitir()
    assert emitida.estado == Estado.EMITIDA and emitida.nueva_revision().contenido["textos"]["tesis"].startswith("[[ANALISTA")


def test_no_se_confirma_dos_veces():
    with pytest.raises(TransicionInvalida):
        _version().confirmar().confirmar()


def test_comparar_versiones():
    a = _version(contenido={"textos": {"tesis": "Comprar."}, "estimaciones": {"g": 0.02}, "recomendacion": "Comprar"})
    b = _version(revision=2, contenido={"textos": {"tesis": "Mantener."}, "estimaciones": {"g": 0.025}, "recomendacion": "Mantener"})
    dif = comparar(a, b)
    assert "-Comprar." in dif["textos"]["tesis"] and "+Mantener." in dif["textos"]["tesis"]
    assert dif["estimaciones"] == {"g": (0.02, 0.025)}
    assert dif["recomendacion"] == ("Comprar", "Mantener")


def test_almacen_y_inmutabilidad(tmp_path):
    almacen = Almacen(tmp_path / "t.sqlite")
    emitida = _version().confirmar().emitir()
    almacen.guardar(emitida)
    assert almacen.ultima_emitida("aapl").etiqueta == emitida.etiqueta
    with pytest.raises(sqlite3.IntegrityError, match="inmutable"):
        almacen.guardar(emitida)
    with sqlite3.connect(almacen.ruta) as con, pytest.raises(sqlite3.IntegrityError):
        con.execute("DELETE FROM versiones")


def test_deteccion_hereda_lo_del_analista(tmp_path):
    almacen = Almacen(tmp_path / "t.sqlite")
    anterior = _version(contenido={"textos": {"tesis": "Tesis"}, "estimaciones": {"g": 0.02}, "metricas": {"roe": 1.5}})
    almacen.guardar(anterior.confirmar().emitir())
    nueva = version_para_filing("aapl", "0000320193-26-000099", "2026-10-30", 2026, "FY", almacen)
    assert nueva.estado == Estado.DETECTADA and nueva.etiqueta == "AAPL · FY2026 · v1"
    assert nueva.contenido == {"textos": {"tesis": "Tesis"}, "estimaciones": {"g": 0.02}}  # sin métricas antiguas
    assert version_para_filing("AAPL", "0000320193-26-000099", "2026-10-30", 2026, "FY", almacen) is None
    assert [v.periodo for v in almacen.historial("AAPL")] == ["Q3", "FY"]


def test_guardar_conexiones_en_el_env(tmp_path, monkeypatch):
    """C3: la interfaz guarda la identidad de EDGAR y las claves en el .env local sin tocar el resto de líneas."""
    from informes_warrants import config

    env = tmp_path / ".env"
    env.write_text("# comentario\nGROQ_API_KEY=antigua\nOTRA=1\n", encoding="utf-8")
    monkeypatch.setattr(config, "ruta_env", lambda: env)
    monkeypatch.delenv("EDGAR_IDENTITY", raising=False)
    config.guardar_conexiones({"EDGAR_IDENTITY": "Ana Pérez ana@ejemplo.com", "GROQ_API_KEY": "nueva", "GEMINI_API_KEY": "",
                               "NO_PERMITIDA": "x"})
    assert env.read_text(encoding="utf-8").splitlines() == ["# comentario", "GROQ_API_KEY=nueva", "OTRA=1",
                                                           'EDGAR_IDENTITY="Ana Pérez ana@ejemplo.com"']
    assert config.configurar_identidad() == "Ana Pérez ana@ejemplo.com"
