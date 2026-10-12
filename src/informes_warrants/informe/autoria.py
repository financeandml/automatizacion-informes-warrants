"""Autoría del informe (R6): datos que introduce cada usuario en el SaaS, nunca en el código ni en git.

Se guardan en la carpeta de datos del usuario (config.directorio_datos, fuera de OneDrive y del repositorio),
en `autoria.json`. Mientras la interfaz no exista (fase A12), se rellenan con `informes-warrants autoria`.
Si están vacíos, la portada no muestra el bloque.
"""

import json
from dataclasses import asdict, dataclass, fields


@dataclass
class Autoria:
    analista: str = ""
    correo: str = ""
    telefono: str = ""
    empresa: str = ""
    contacto_empresa: str = ""  # correo, web o teléfono de la entidad emisora

    @property
    def rellena(self) -> bool:
        return bool(self.analista or self.empresa)


def _ruta():
    from ..config import directorio_datos

    return directorio_datos() / "autoria.json"


def cargar() -> Autoria:
    try:
        datos = json.loads(_ruta().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Autoria()
    return Autoria(**{f.name: str(datos.get(f.name, "")) for f in fields(Autoria)})


def guardar(autoria: Autoria) -> None:
    ruta = _ruta()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(asdict(autoria), ensure_ascii=False, indent=2), encoding="utf-8")
