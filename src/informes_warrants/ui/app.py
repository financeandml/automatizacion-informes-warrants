"""Interfaz del analista (A12): un analista, en su ordenador. Se abre con `informes-warrants interfaz`.

Estructura tomada de financial-research-analyst-agent `frontend/` (Copyright (c) 2024 Gopal Saini, licencia MIT):
`init_session_state` con valores por defecto, navegación en la barra lateral y la interfaz como fachada del
núcleo (aquí no se calcula nada: las cifras salen de `calculo/` a través de `ui/logica.py`). Tres pantallas:

1. Empresas y versiones: detectar el 10-Q/10-K nuevo y confirmar la versión.
2. Editor del informe: textos del analista (Markdown), estimaciones, escenarios, calendario y catalizadores, con
   la vista previa del informe al lado; avisos antes de emitir y botón «Confirmar emisión del informe».
3. Configuración: la autoría de cada usuario (uso interno del SaaS; se guarda fuera del repositorio).
"""

from dataclasses import asdict, replace

import streamlit as st

from informes_warrants.almacenamiento.almacen import Almacen
from informes_warrants.almacenamiento.deteccion import detectar
from informes_warrants.almacenamiento.versiones import Estado, TransicionInvalida
from informes_warrants.config import configurar_identidad
from informes_warrants.informe import autoria, render
from informes_warrants.informe.cambios import estimaciones_desde_dict
from informes_warrants.informe.secciones import BLOQUES, Tipo
from informes_warrants.informe.versionado import datos_de_la_version, preparar, ultima_abierta
from informes_warrants.ui import logica

PANTALLAS = ("Empresas y versiones", "Editor del informe", "Configuración")
ESCENARIOS = ("pesimista", "base", "optimista")


def iniciar_sesion() -> None:
    valores = {"ticker": "", "datos": None, "datos_de": None, "textos": {}, "estimaciones": None, "ajustes": {}}
    for clave, valor in valores.items():
        st.session_state.setdefault(clave, valor)


@st.cache_resource
def _almacen() -> Almacen:
    return Almacen()


def pantalla_versiones(almacen: Almacen, ticker: str) -> None:
    st.header(f"{ticker} · versiones")
    c1, c2 = st.columns(2)
    if c1.button("Detectar 10-Q/10-K nuevo", use_container_width=True):
        nueva = detectar(ticker, almacen)
        st.success(f"Versión propuesta: {nueva.etiqueta}. Confírmala para editarla." if nueva else "No hay filings nuevos.")
    abierta = ultima_abierta(almacen, ticker)
    if abierta is not None and abierta.estado == Estado.DETECTADA and c2.button(f"Confirmar {abierta.etiqueta}", use_container_width=True):
        almacen.guardar(abierta.confirmar())
        st.success("Versión confirmada: ya puedes editarla en «Editor del informe».")
    filas = [{"Versión": v.etiqueta, "Estado": v.estado.value, "Filing": v.accession, "Fecha": v.fecha_filing,
              "PDF": v.contenido.get("pdf", "—")} for v in reversed(almacen.historial(ticker))]
    if filas:
        st.dataframe(filas, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay versiones de esta empresa: pulsa «Detectar 10-Q/10-K nuevo».")


def _cargar(version, almacen: Almacen, con_ia: bool, comparables: list[str] | None) -> None:
    with st.spinner("Reuniendo los datos de la SEC y del mercado (puede tardar unos minutos)…"):
        st.session_state.datos = datos_de_la_version(version, almacen, con_ia, comparables)
    st.session_state.datos_de = version.etiqueta
    contenido = version.contenido
    st.session_state.textos = dict(contenido.get("textos") or {})
    st.session_state.estimaciones = estimaciones_desde_dict(contenido["estimaciones"]) if contenido.get("estimaciones") else None
    st.session_state.ajustes = {}


def _bloques_editables(c: dict) -> list:
    """Bloques del analista y los que el SaaS dejó con un marcador pendiente."""
    return [b for b in BLOQUES if b.id in c["textos"] and (b.tipo == Tipo.ANALISTA or "[[ANALISTA" in c["textos"][b.id])]


def _editor_textos(c: dict) -> None:
    for b in _bloques_editables(c):
        actual = st.session_state.textos.get(b.id) or c["textos"][b.id]
        nuevo = st.text_area(b.titulo, actual, key=f"texto_{b.id}", height=140,
                             help="Markdown. Sustituye cada [[ANALISTA: …]] por tu texto; mientras quede alguno, no se puede emitir.")
        if nuevo != c["textos"][b.id]:
            st.session_state.textos[b.id] = nuevo


def _editor_estimaciones(c: dict) -> None:
    est = c["estimaciones"]
    cambios = {}
    st.caption("Supuestos del escenario base. Los porcentajes, en %.")
    anios = c["etiquetas_estimadas"][:len(est.crecimiento_ventas)]
    tabla = st.data_editor([{"Periodo": a, "Crecimiento de ventas (%)": g * 100, "Margen EBITDA (%)": m * 100}
                            for a, g, m in zip(anios, est.crecimiento_ventas, est.margen_ebitda, strict=False)],
                           disabled=["Periodo"], hide_index=True, key="tabla_explicitos")
    cambios["crecimiento_ventas"] = [f["Crecimiento de ventas (%)"] / 100 for f in tabla]
    cambios["margen_ebitda"] = [f["Margen EBITDA (%)"] / 100 for f in tabla]
    columnas = st.columns(2)
    for i, nombre in enumerate(logica.ESCALARES):
        valor = logica.a_pantalla(nombre, getattr(est, nombre))
        if nombre == "precio_objetivo_analista":
            texto = columnas[i % 2].text_input(logica.ETIQUETAS[nombre], "" if valor is None else f"{valor:.2f}", key=f"est_{nombre}")
            cambios[nombre] = float(texto.replace(",", ".")) if texto.strip() else None
        elif nombre == "anios_convergencia":
            cambios[nombre] = int(columnas[i % 2].number_input(logica.ETIQUETAS[nombre], 0, 15, int(valor), key=f"est_{nombre}"))
        else:
            cambios[nombre] = logica.de_pantalla(nombre, columnas[i % 2].number_input(
                logica.ETIQUETAS[nombre], value=float(valor), format="%.2f", key=f"est_{nombre}"))
    pesos = st.data_editor([{"Método": k, "Peso (%)": v * 100} for k, v in est.pesos.items()], disabled=["Método"],
                           hide_index=True, key="tabla_pesos")
    cambios["pesos"] = {f["Método"]: f["Peso (%)"] / 100 for f in pesos}
    nuevas, errores = logica.editar(est, **cambios)
    for e in errores:
        st.error(e)
    st.session_state.estimaciones = nuevas


def _editor_escenarios(c: dict) -> None:
    esc = c["escenarios"]
    if esc is None:
        st.info("Sin DCF: no hay escenarios que editar.")
        return
    columnas = st.columns(3)
    probabilidades = tuple(columnas[i].number_input(f"Probabilidad {n} (%)", 0.0, 100.0, p * 100, key=f"prob_{n}") / 100
                           for i, (n, p) in enumerate(zip(ESCENARIOS, esc.probabilidades, strict=True)))
    desencadenantes = {n: st.text_input(f"Qué tendría que pasar en el escenario {n}", esc.desencadenantes.get(n, ""), key=f"des_{n}")
                       for n in ESCENARIOS}
    st.session_state.ajustes = {"probabilidades": probabilidades, "desencadenantes": {k: v for k, v in desencadenantes.items() if v}}


def _editor_catalizadores(c: dict) -> None:
    cat = c["catalizadores"]
    st.caption("El calendario lo introduce preferentemente el analista: el del SaaS es un borrador con fechas estimadas.")
    calendario = st.data_editor([{"evento": e.get("evento", ""), "fecha": str(e.get("fecha") or ""), "base": e.get("base", "")}
                                 for e in cat.get("calendario") or []], num_rows="dynamic", hide_index=True, key="tabla_calendario")
    confirmar = st.checkbox("Este es mi calendario (sustituye al borrador del SaaS)", value=cat.get("del_analista", False))
    lista_ia = (cat.get("ia") or {}).get("lista") or []
    catalizadores = st.data_editor([{"resumen": s["resumen"], "cita": s["cita"]} for s in lista_ia], num_rows="dynamic",
                                   hide_index=True, key="tabla_catalizadores")
    propios = st.checkbox("Estos son mis catalizadores (sustituyen a la propuesta de la IA)", value=not (cat.get("ia") or {}).get("modelo")
                          and bool(lista_ia))
    est = st.session_state.estimaciones or c["estimaciones"]
    st.session_state.estimaciones = replace(est, calendario=[dict(f) for f in calendario] if confirmar else [],
                                            catalizadores=[dict(f) for f in catalizadores] if propios else [])


def _emision(c: dict, version, almacen: Almacen) -> None:
    for aviso in c["avisos_emision"]:
        st.warning(aviso)
    motivos = logica.motivos_para_no_emitir(c)
    if version.estado == Estado.DETECTADA:
        motivos.insert(0, "Confirma la versión en «Empresas y versiones» antes de emitir.")
    for m in motivos:
        st.error(m)
    contenido = {**version.contenido, **logica.contenido_editable(c), "ajustes_escenarios": st.session_state.ajustes}
    c1, c2 = st.columns(2)
    if c1.button("Guardar borrador (regenera el PDF)", use_container_width=True):
        preparada, _ = preparar(replace(version, contenido=contenido), almacen, datos=st.session_state.datos)
        st.success(f"Guardado: {preparada.contenido['pdf']}")
    if c2.button("Confirmar emisión del informe", type="primary", disabled=bool(motivos), use_container_width=True):
        preparada, _ = preparar(replace(version, contenido=contenido), almacen, datos=st.session_state.datos)
        try:
            emitida = preparada.emitir()
        except TransicionInvalida as e:
            st.error(str(e))
            return
        almacen.guardar(emitida)
        st.success(f"{emitida.etiqueta} emitida: ya no se puede modificar.")
        with open(emitida.contenido["pdf"], "rb") as f:
            st.download_button("Descargar el PDF", f.read(), file_name=emitida.contenido["pdf"].split("\\")[-1].split("/")[-1],
                               mime="application/pdf")


def pantalla_editor(almacen: Almacen, ticker: str) -> None:
    version = ultima_abierta(almacen, ticker)
    if version is None:
        st.info("No hay ninguna versión abierta: detecta y confirma una en «Empresas y versiones».")
        return
    st.header(version.etiqueta)
    if st.session_state.datos is None or st.session_state.datos_de != version.etiqueta:
        con_ia = st.checkbox("Usar el modelo de lenguaje (riesgos, catalizadores y competencia)", value=True)
        lista = st.text_input("Comparables (tickers separados por comas; vacío = propuesta automática por SIC)",
                              ",".join(version.contenido.get("comparables") or []))
        if st.button("Cargar los datos de la SEC y del mercado", type="primary"):
            _cargar(version, almacen, con_ia, [t.strip().upper() for t in lista.split(",") if t.strip()] or None)
            st.rerun()
        return
    c = logica.recomponer(st.session_state.datos, st.session_state.estimaciones, st.session_state.textos, st.session_state.ajustes)
    izquierda, derecha = st.columns([2, 3])
    with izquierda:
        pestanas = st.tabs(["Textos", "Estimaciones", "Escenarios", "Calendario y catalizadores", "Emisión"])
        with pestanas[0]:
            _editor_textos(c)
        with pestanas[1]:
            _editor_estimaciones(c)
        with pestanas[2]:
            _editor_escenarios(c)
        with pestanas[3]:
            _editor_catalizadores(c)
        with pestanas[4]:
            _emision(c, version, almacen)
    with derecha:
        st.caption(f"Vista previa · {len(c['pendientes'])} apartados pendientes del analista · calidad {c['calidad'].nivel}")
        st.iframe(render.html_autonomo(c), height=1400)  # HTML propio; los textos de terceros llegan escapados (render._md)


def pantalla_configuracion() -> None:
    st.header("Configuración")
    st.caption("Uso interno del SaaS: cada usuario introduce aquí su autoría; se guarda en su carpeta de datos, "
               "fuera del repositorio.")
    actual = autoria.cargar()
    with st.form("autoria"):
        valores = {campo: st.text_input(etiqueta, getattr(actual, campo)) for campo, etiqueta in (
            ("analista", "Analista"), ("correo", "Correo del analista"), ("telefono", "Teléfono del analista"),
            ("empresa", "Empresa"), ("contacto_empresa", "Contacto de la empresa"))}
        if st.form_submit_button("Guardar"):
            autoria.guardar(autoria.Autoria(**valores))
            st.success("Guardado.")
    st.json(asdict(autoria.cargar()))


def main() -> None:
    st.set_page_config(page_title="Warrants & Co · Informes", layout="wide")
    try:
        configurar_identidad()
    except Exception as e:  # noqa: BLE001  (sin EDGAR_IDENTITY no se puede consultar la SEC)
        st.error(str(e))
        st.stop()
    iniciar_sesion()
    with st.sidebar:
        st.markdown("**WARRANTS & CO.** · Apertura de posiciones")
        st.session_state.ticker = st.text_input("Empresa (ticker)", st.session_state.ticker).strip().upper()
        pantalla = st.radio("Pantalla", PANTALLAS)
    almacen = _almacen()
    if pantalla == "Configuración":
        pantalla_configuracion()
    elif not st.session_state.ticker:
        st.info("Escribe el ticker de una empresa cotizada en EEUU en la barra lateral.")
    elif pantalla == PANTALLAS[0]:
        pantalla_versiones(almacen, st.session_state.ticker)
    else:
        pantalla_editor(almacen, st.session_state.ticker)


main()
