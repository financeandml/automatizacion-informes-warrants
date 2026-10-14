"""Versiones conectadas al informe (A11): reutiliza `almacenamiento/` tal cual (Version, Almacen, detectar, heredar).

Flujo (lo gestiona el SaaS; el analista solo confirma y emite):
    detectar (10-Q/10-K nuevo) → preparar (construye el informe, guarda contenido, instantánea y PDF) →
    confirmar → [el analista edita textos y estimaciones] → preparar de nuevo → emitir (inmutable)

Qué guarda cada versión en `contenido`:
- `textos`: los de todos los bloques; los del analista (bloques ANALISTA) se heredan y prevalecen sobre la plantilla.
- `estimaciones`: las del analista (se heredan); sin ellas, las del SaaS por defecto.
- `resumen` (R16, para comparar con la siguiente versión), `instantanea` (cifras de la SEC, como la regresión),
  `avisos_emision` (no bloquean), `calidad` (en rojo bloquea la emisión), `pdf` (ruta del PDF de la versión).
"""

from dataclasses import asdict, replace
from pathlib import Path

from ..almacenamiento.almacen import Almacen
from ..almacenamiento.versiones import Estado, Version
from .cambios import estimaciones_desde_dict, resumen
from .plantillas import pendientes
from .regresion import cifras_clave
from .secciones import BLOQUES, Tipo

BLOQUES_ANALISTA = {b.id for b in BLOQUES if b.tipo == Tipo.ANALISTA}


def _carpeta(ticker: str) -> Path:
    from ..config import directorio_datos

    return directorio_datos() / "informes" / ticker.upper()


def aplicar_textos(c: dict, textos: dict[str, str]) -> dict:
    """Lo escrito por el analista prevalece: bloques ANALISTA y cualquier bloque que el SaaS dejó con un marcador
    (p. ej. la competencia sin traducción verificada). Recalcula los apartados pendientes."""
    for bloque, texto in (textos or {}).items():
        if texto and (bloque in BLOQUES_ANALISTA or pendientes(c["textos"].get(bloque, ""))):
            c["textos"][bloque] = texto
    c["pendientes"] = [p for t in c["textos"].values() for p in pendientes(t)]
    return c


def recomponer(datos: dict, estimaciones, textos: dict[str, str] | None, ajustes_escenarios: dict | None = None) -> dict:
    """Informe con los datos ya reunidos y lo que aportó el analista (sin red): estimaciones, textos y ajustes de los
    escenarios ({"probabilidades", "desencadenantes"}) aplicados sobre los escenarios por defecto del propio informe,
    para que el escenario base nunca quede desfasado respecto de las estimaciones."""
    from dataclasses import replace as reemplazar

    from .construir import componer

    c = componer(**{**datos, "estimaciones": estimaciones})
    ajustes = {k: (tuple(v) if k == "probabilidades" else v) for k, v in (ajustes_escenarios or {}).items() if v}
    if ajustes and c["escenarios"] is not None:
        c = componer(**{**datos, "estimaciones": estimaciones, "escenarios": reemplazar(c["escenarios"], **ajustes)})
    return aplicar_textos(c, textos)


def datos_de_la_version(version: Version, almacen: Almacen, con_ia: bool = True, comparables: list[str] | None = None) -> dict:
    """Argumentos de `componer` para la versión (SEC y mercado; con red). La interfaz los guarda en la sesión."""
    from .construir import reunir

    contenido = version.contenido
    emitidas = [v for v in almacen.historial(version.ticker) if v.estado == Estado.EMITIDA and v.contenido.get("resumen")]
    return reunir(version.ticker, con_ia=con_ia, comparables=comparables or contenido.get("comparables"),
                  anterior=emitidas[-1].contenido["resumen"] if emitidas else None,
                  historial_resumenes=[v.contenido["resumen"] for v in emitidas])


def preparar(version: Version, almacen: Almacen, con_ia: bool = True, comparables: list[str] | None = None,
             carpeta: Path | None = None, datos: dict | None = None) -> tuple[Version, dict]:
    """Compone el informe de la versión con lo que aportó el analista y guarda el contenido y el PDF.

    `datos`: argumentos de `componer` ya reunidos (la interfaz los reutiliza para no volver a la SEC)."""
    from . import render
    from .motor import exportar as exportar_modelo

    contenido = version.contenido
    lista = comparables or contenido.get("comparables")
    estimaciones = estimaciones_desde_dict(contenido["estimaciones"]) if contenido.get("estimaciones") else None
    datos = datos or datos_de_la_version(version, almacen, con_ia, lista)
    c = recomponer(datos, estimaciones, contenido.get("textos"), contenido.get("ajustes_escenarios"))
    destino = (carpeta or _carpeta(version.ticker))
    destino.mkdir(parents=True, exist_ok=True)
    nombre = f"{version.ticker}_FY{version.ejercicio}{'' if version.periodo == 'FY' else '_' + version.periodo}_v{version.revision}.pdf"
    pdf = render.pdf(c, destino / nombre)
    modelo_xlsx, avisos_modelo = exportar_modelo(c, pdf)  # B1: el libro del motor junto al PDF, contrastado con LibreOffice
    nuevo = {
        **contenido, "textos": c["textos"], "estimaciones": asdict(c["estimaciones"]), "resumen": resumen(c),
        "instantanea": cifras_clave(c), "avisos_emision": list(c["avisos_emision"]) + avisos_modelo, "pdf": str(pdf),
        "modelo_xlsx": modelo_xlsx,
        "calidad": {"nivel": str(c["calidad"].nivel), "errores": list(c["calidad"].errores)},
        "comparables": lista if c["comparables_del_analista"] else None, "recomendacion": c["recomendacion"],
    }
    preparada = replace(version, contenido=nuevo)
    almacen.guardar(preparada)
    return preparada, c


def ultima_abierta(almacen: Almacen, ticker: str) -> Version | None:
    """La versión más reciente que aún no está emitida ni descartada."""
    abiertas = [v for v in almacen.historial(ticker) if v.estado in (Estado.DETECTADA, Estado.BORRADOR)]
    return abiertas[-1] if abiertas else None
