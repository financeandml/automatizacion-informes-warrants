"""Almacén de versiones en SQLite, fuera de OneDrive (config.directorio_datos).

SQLite de la biblioteca estándar: sin servidor ni dependencias, suficiente para el uso en
localhost. Un trigger impide modificar o borrar una versión emitida, aunque se acceda a la base
de datos por fuera del SaaS.
"""

import json
import sqlite3
from pathlib import Path

from .versiones import Estado, Version

ESQUEMA = """
CREATE TABLE IF NOT EXISTS versiones (
    ticker TEXT NOT NULL, ejercicio INTEGER NOT NULL, periodo TEXT NOT NULL, revision INTEGER NOT NULL,
    accession TEXT NOT NULL, fecha_filing TEXT NOT NULL, estado TEXT NOT NULL, contenido TEXT NOT NULL,
    creada TEXT NOT NULL, emitida TEXT,
    PRIMARY KEY (ticker, ejercicio, periodo, revision)
);
CREATE INDEX IF NOT EXISTS ix_versiones_accession ON versiones (accession);
CREATE TRIGGER IF NOT EXISTS emitida_inmutable_update BEFORE UPDATE ON versiones
    WHEN OLD.estado = 'emitida' BEGIN SELECT RAISE(ABORT, 'Una versión emitida es inmutable'); END;
CREATE TRIGGER IF NOT EXISTS emitida_inmutable_delete BEFORE DELETE ON versiones
    WHEN OLD.estado = 'emitida' BEGIN SELECT RAISE(ABORT, 'Una versión emitida es inmutable'); END;
"""

_COLUMNAS = ("ticker", "ejercicio", "periodo", "revision", "accession", "fecha_filing", "estado", "contenido",
             "creada", "emitida")


class Almacen:
    def __init__(self, ruta: Path | None = None):
        if ruta is None:
            from ..config import directorio_datos

            ruta = directorio_datos() / "informes.sqlite"
        self.ruta = Path(ruta)
        with self._conexion() as con:
            con.executescript(ESQUEMA)

    def _conexion(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.ruta)
        con.row_factory = sqlite3.Row
        return con

    def guardar(self, v: Version) -> None:
        fila = (v.ticker, v.ejercicio, v.periodo, v.revision, v.accession, v.fecha_filing, v.estado.value,
                json.dumps(v.contenido, ensure_ascii=False), v.creada, v.emitida)
        with self._conexion() as con:
            con.execute(
                f"INSERT INTO versiones ({', '.join(_COLUMNAS)}) VALUES ({', '.join('?' * len(_COLUMNAS))}) "
                "ON CONFLICT (ticker, ejercicio, periodo, revision) DO UPDATE SET "
                + ", ".join(f"{c} = excluded.{c}" for c in _COLUMNAS[4:]),
                fila,
            )

    def historial(self, ticker: str) -> list[Version]:
        with self._conexion() as con:
            filas = con.execute("SELECT * FROM versiones WHERE ticker = ?", (ticker.upper(),)).fetchall()
        orden = {"Q1": 1, "Q2": 2, "Q3": 3, "FY": 4}  # el FY cierra el ejercicio, después del Q3
        return sorted((_a_version(f) for f in filas), key=lambda v: (v.ejercicio, orden.get(v.periodo, 9), v.revision))

    def ultima_emitida(self, ticker: str) -> Version | None:
        emitidas = [v for v in self.historial(ticker) if v.estado == Estado.EMITIDA]
        return max(emitidas, key=lambda v: v.emitida or "", default=None)

    def conoce_accession(self, accession: str) -> bool:
        with self._conexion() as con:
            return con.execute("SELECT 1 FROM versiones WHERE accession = ? LIMIT 1", (accession,)).fetchone() is not None


def _a_version(fila: sqlite3.Row) -> Version:
    datos = dict(fila)
    datos["estado"] = Estado(datos["estado"])
    datos["contenido"] = json.loads(datos["contenido"])
    return Version(**datos)
