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
from informes_warrants.informe.plantillas import pendientes, sin_marcas_ia
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
    emitida = almacen.ultima_emitida(ticker)
    if abierta is None and emitida is not None and c2.button(f"Seguir editando {emitida.etiqueta} (crea la revisión siguiente)",
                                                             use_container_width=True):
        revision = emitida.nueva_revision()  # la emitida no cambia; la nueva hereda lo que aportó el analista
        almacen.guardar(revision)
        st.success(f"Creada {revision.etiqueta}: edítala en «Editor del informe».")
    versiones = almacen.historial(ticker)
    filas = [{"Versión": v.etiqueta, "Estado": v.estado.value, "Filing": v.accession, "Fecha": v.fecha_filing,
              "PDF": v.contenido.get("pdf", "—")} for v in reversed(versiones)]
    if filas:
        st.dataframe(filas, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay versiones de esta empresa: pulsa «Detectar 10-Q/10-K nuevo».")
    if len(versiones) >= 2:
        _comparar(versiones)


def _comparar(versiones: list) -> None:
    st.subheader("Comparar versiones")
    etiquetas = [v.etiqueta for v in versiones]
    c1, c2 = st.columns(2)
    anterior = versiones[etiquetas.index(c1.selectbox("Anterior", etiquetas, index=len(etiquetas) - 2))]
    actual = versiones[etiquetas.index(c2.selectbox("Actual", etiquetas, index=len(etiquetas) - 1))]
    r = logica.comparacion(anterior, actual)
    antes, ahora = r["recomendacion"]
    if antes != ahora:
        st.write(f"Recomendación: **{antes or '—'} → {ahora or '—'}**")
    if r["valoracion"]:
        cambios = r["valoracion"]["cambios"]
        if cambios:
            st.dataframe([{"Dato": x["campo"], "Antes": x["antes"], "Ahora": x["ahora"]} for x in cambios], hide_index=True)
        if r["valoracion"]["atribucion"]:
            st.caption("Qué explica el cambio del valor DCF (escenario base, USD por acción)")
            pasos = r["valoracion"]["atribucion"]["pasos"]
            st.dataframe([{"Grupo de supuestos": p["grupo"], "Impacto": round(p["impacto"], 2)} for p in pasos], hide_index=True)
    if r["estimaciones"]:
        st.dataframe([{"Estimación": k, "Antes": str(v[0]), "Ahora": str(v[1])} for k, v in r["estimaciones"].items()], hide_index=True)
    for bloque, diff in r["textos"].items():
        with st.expander(f"Texto cambiado: {bloque}"):
            st.code(diff, language="diff")
    if not (r["textos"] or r["estimaciones"] or (r["valoracion"] and r["valoracion"]["cambios"]) or antes != ahora):
        st.info("Sin diferencias entre estas dos versiones.")


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
    return [b for b in BLOQUES if b.id in c["textos"] and (b.tipo == Tipo.ANALISTA or pendientes(c["textos"][b.id]))]


def _editor_textos(c: dict) -> None:
    st.caption("Los apartados del analista traen un borrador de la IA (sobre lo que ya dice el informe) para ayudarte: "
               "revísalo, edítalo o sustitúyelo. Mientras no lo marques como revisado, el informe lo muestra como borrador.")
    for b in _bloques_editables(c):
        propio = st.session_state.textos.get(b.id)
        legible = propio or sin_marcas_ia(c["textos"][b.id])  # el borrador de la IA, en limpio
        nuevo = st.text_area(b.titulo, legible, key=f"texto_{b.id}", height=150,
                             help="Markdown. Sustituye cada [[ANALISTA: …]] por tu texto. Los pendientes no impiden emitir.")
        revisado = st.checkbox("Revisado por el analista", value=propio is not None, key=f"revisado_{b.id}")
        if revisado or nuevo != legible:
            st.session_state.textos[b.id] = nuevo
        else:
            st.session_state.textos.pop(b.id, None)


def _editor_estimaciones(c: dict) -> None:
    est = c["estimaciones"]
    cambios = {}
    if c.get("perfil"):
        st.caption("Plantilla sectorial: valoración por múltiplos justificados, dividendos y comparables (sin DCF). "
                   "Los porcentajes, en %.")
        st.warning("En banca, seguros, REIT y BDC la beta y los comparables los decides tú: revisa la beta de abajo y añade "
                   "tu lista de comparables al cargar los datos.")
    else:
        st.caption("Supuestos del escenario base. Los porcentajes, en %.")
        anios = c["etiquetas_estimadas"][:len(est.crecimiento_ventas)]
        tabla = st.data_editor([{"Periodo": a, "Crecimiento de ventas (%)": g * 100, "Margen EBITDA (%)": m * 100}
                                for a, g, m in zip(anios, est.crecimiento_ventas, est.margen_ebitda, strict=False)],
                               disabled=["Periodo"], hide_index=True, key="tabla_explicitos")
        cambios["crecimiento_ventas"] = [f["Crecimiento de ventas (%)"] / 100 for f in tabla]
        cambios["margen_ebitda"] = [f["Margen EBITDA (%)"] / 100 for f in tabla]
    columnas = st.columns(2)
    for i, nombre in enumerate(logica.escalares(c)):
        valor = logica.a_pantalla(nombre, getattr(est, nombre))
        if nombre in logica.OPCIONALES:
            texto = columnas[i % 2].text_input(logica.ETIQUETAS[nombre], "" if valor is None else f"{valor:.2f}", key=f"est_{nombre}")
            cambios[nombre] = logica.de_pantalla(nombre, float(texto.replace(",", "."))) if texto.strip() else None
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


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _nombre(ruta: str) -> str:
    return ruta.replace(chr(92), "/").split("/")[-1]


def _editor_motor(c: dict) -> None:
    """Entradas del modelo de valoración (B1) y descarga del libro de Excel para comprobarlo número a número."""
    libro = logica.libro_del_motor(c)
    if libro is not None:
        st.download_button("Descargar el modelo de valoración (Excel, fórmulas vivas)", libro,
                           file_name=f"{c['ticker']}_FY{c['filing']['ejercicio']}_modelo.xlsx", mime=XLSX)
    if c.get("perfil"):
        st.caption("Plantilla sectorial: el libro reproduce la valoración del perfil y la hoja de comparables; sus supuestos "
                   "(Rf, prima, beta, g, rentabilidad sostenible y pesos) se editan en «Estimaciones».")
        return
    actuales, defecto = logica.entradas_motor(c)
    if actuales is None:
        st.info(f"Sin modelo de valoración: {(c.get('motor') or {}).get('error', 'faltan las ventas o el EBIT del último ejercicio')}.")
        return
    est = st.session_state.estimaciones or c["estimaciones"]
    st.caption(f"Prima de riesgo propuesta por el SaaS: {c['origen_prima']} (se confirma o cambia en «Estimaciones»). Crecimiento "
               "y margen EBIT por segmento, en %, para los 6 años del modelo; sin tocar, son los del motor («Revisar» en el libro).")
    anios = [f"Año {i}" for i in range(1, 7)]

    def tabla(clave, titulo):
        st.caption(titulo)
        filas = st.data_editor([{"Segmento": s, **{a: x * 100 for a, x in zip(anios, v, strict=True)}}
                                for s, v in getattr(actuales, clave).items()], disabled=["Segmento"], hide_index=True, key=f"motor_{clave}")
        return {f["Segmento"]: [f[a] / 100 for a in anios] for f in filas}

    crecimientos = tabla("crecimientos", "Crecimiento anual de las ventas (%)")
    margenes = tabla("margenes", "Margen EBIT (%; en costes no asignados, % de las ventas totales)")
    columnas = st.columns(3)
    pct = columnas[0].number_input("Valor terminal por perpetuidad (%)", 0.0, 100.0, actuales.pct_perpetuidad * 100, key="motor_pct") / 100
    convencion = 1 if columnas[1].radio("Descuento", ("Mitad de año", "Fin de año"), index=actuales.convencion - 1,
                                        key="motor_convencion") == "Mitad de año" else 2
    lbo = columnas[2].checkbox("Hoja LBO", value=actuales.lbo, key="motor_lbo")
    revisado = st.checkbox("He revisado las entradas del motor", value=logica.motor_revisado(est), key="motor_revisado")
    st.session_state.estimaciones = replace(est, motor=logica.motor_del_analista(defecto, crecimientos, margenes, pct, convencion,
                                                                                 lbo, revisado))
    for aviso in c["motor"]["modelo"].avisos:
        st.warning(aviso)


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
    for aviso in c["avisos_emision"] + logica.pendientes_aviso(c):  # avisos: no bloquean la emisión
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
        st.success(f"Guardado: {preparada.contenido['pdf']}" + (f" y {preparada.contenido['modelo_xlsx']}"
                                                                 if preparada.contenido.get("modelo_xlsx") else ""))
        for aviso in preparada.contenido["avisos_emision"]:
            if aviso.startswith("Motor de valoración"):
                st.warning(aviso)
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
        if emitida.contenido.get("modelo_xlsx"):
            with open(emitida.contenido["modelo_xlsx"], "rb") as f:
                st.download_button("Descargar el modelo de valoración (Excel)", f.read(),
                                   file_name=_nombre(emitida.contenido["modelo_xlsx"]),
                                   mime=XLSX)


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
        pestanas = st.tabs(["Textos", "Estimaciones", "Modelo de valoración", "Escenarios", "Calendario y catalizadores", "Emisión"])
        with pestanas[0]:
            _editor_textos(c)
        with pestanas[1]:
            _editor_estimaciones(c)
        with pestanas[2]:
            _editor_motor(c)
        with pestanas[3]:
            _editor_escenarios(c)
        with pestanas[4]:
            _editor_catalizadores(c)
        with pestanas[5]:
            _emision(c, version, almacen)
    with derecha:
        st.caption(f"Vista previa · {len(c['pendientes'])} apartados pendientes del analista · calidad {c['calidad'].nivel}")
        st.iframe(render.html_autonomo(c), height=1400)  # HTML propio; los textos de terceros llegan escapados (render._md)


GUIA = """1. **Escribe el ticker** de una empresa cotizada en EE. UU. (p. ej. AAPL) aquí arriba.
2. **Empresas y versiones** → «Detectar 10-Q/10-K nuevo» y «Confirmar»: el SaaS crea la versión del último informe de la SEC.
3. **Editor del informe** → «Cargar los datos» (1-2 minutos la primera vez). Revisa cada pestaña: los textos marcados como
   pendientes son tuyos; las cifras salen de la SEC y no se editan.
4. **Emisión** → revisa los avisos y pulsa «Confirmar emisión»: descargas el PDF y el modelo de valoración en Excel.

Si algo no funciona: **Configuración → Diagnóstico** te dice qué falta."""


def _formulario_conexiones(clave_formulario: str) -> None:
    """Identidad de EDGAR (obligatoria) y claves de IA (opcionales), guardadas en el .env local (nunca en git)."""
    from informes_warrants.config import guardar_conexiones

    with st.form(clave_formulario):
        nombre = st.text_input("Tu nombre o el de tu empresa", help="La SEC exige identificarse en cada consulta (no tiene coste).")
        correo = st.text_input("Tu correo electrónico", help="Solo se envía a la SEC como identificación (cabecera User-Agent).")
        gemini = st.text_input("Clave de Gemini (opcional)", type="password",
                               help="Google AI Studio → Get API key. Activa los borradores de la IA y el consenso de analistas.")
        groq = st.text_input("Clave de Groq (opcional, respaldo de la IA)", type="password", help="console.groq.com → API Keys.")
        if st.form_submit_button("Guardar las conexiones", type="primary"):
            if nombre.strip() and "@" in correo:
                ruta = guardar_conexiones({"EDGAR_IDENTITY": f"{nombre.strip()} {correo.strip()}", "GEMINI_API_KEY": gemini,
                                           "GROQ_API_KEY": groq})
                st.success(f"Guardado en {ruta} (fichero local, fuera de git). Recarga la página.")
            elif gemini or groq:
                guardar_conexiones({"GEMINI_API_KEY": gemini, "GROQ_API_KEY": groq})
                st.success("Claves guardadas.")
            else:
                st.error("Escribe tu nombre y un correo válido.")


def pantalla_primeros_pasos() -> None:
    st.title("Bienvenido a Warrants & Co · Informes")
    st.markdown("Para empezar solo hace falta identificarte ante la SEC (gratis). Las claves de IA son opcionales: sin ellas "
                "el informe sale igual, con los textos del analista marcados.")
    _formulario_conexiones("primeros_pasos")
    st.markdown(GUIA)


@st.cache_data(ttl=86400, show_spinner=False)
def _filings_nuevos(tickers: tuple[str, ...]) -> list[str]:
    """C4: una consulta ligera por empresa seguida, como mucho una vez al día."""
    from edgar import Company

    from informes_warrants.almacenamiento.deteccion import FORMULARIOS

    almacen, nuevos = Almacen(), []
    for t in tickers[:20]:
        try:
            f = Company(t).get_filings(form=FORMULARIOS, amendments=False).latest()
            if f is not None and not almacen.conoce_accession(f.accession_no):
                nuevos.append(f"{t}: {f.form} del {f.filing_date}")
        except Exception:  # noqa: BLE001  (sin conexión: sin aviso)
            continue
    return nuevos


def _avisos_de_filings(almacen: Almacen) -> None:
    empresas = tuple(almacen.empresas())
    if empresas:
        for aviso in _filings_nuevos(empresas):
            st.sidebar.info(f"Nuevo informe en la SEC · {aviso}. Ábrelo en «Empresas y versiones» → «Detectar».")


def pantalla_configuracion() -> None:
    st.header("Configuración")
    with st.expander("Diagnóstico de la instalación", expanded=False):
        from informes_warrants.observabilidad import diagnostico, resumen_tiempos

        for nombre, bien, detalle in diagnostico():
            (st.success if bien else st.warning)(f"{nombre}: {detalle}")
        tiempos = resumen_tiempos()
        if tiempos:
            st.dataframe([{"Etapa": k, "Veces": v["n"], "Mediana (s)": v["mediana"], "Máximo (s)": v["maximo"], "Errores": v["errores"]}
                          for k, v in tiempos.items()], hide_index=True)
    with st.expander("Conexiones (SEC y claves de IA)"):
        _formulario_conexiones("conexiones")
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
    _configuracion_parametros()


PARAMETROS = (  # (campo, etiqueta, en porcentaje)
    ("potencial_minimo", "Potencial mínimo frente al precio objetivo (%)", True), ("per_maximo", "PER máximo (x)", False),
    ("ev_ebitda_maximo", "EV / EBITDA máximo (x)", False), ("deuda_neta_ebitda_maxima", "Deuda neta / EBITDA máxima (x)", False),
    ("roic_minimo", "ROIC mínimo (%)", True), ("crecimiento_minimo", "Crecimiento mínimo de ventas (%)", True),
    ("capital_cartera", "Capital de la cartera (USD)", False),
    ("riesgo_por_posicion", "Riesgo por posición hasta el stop (% de la cartera)", True),
    ("peso_maximo", "Peso máximo de una posición (%)", True), ("multiplo_volatilidad", "Múltiplo de volatilidad del stop (k)", False),
    ("horizonte_stop_dias", "Horizonte del stop (sesiones)", False), ("perdida_minima_stop", "Pérdida mínima hasta el stop (%)", True),
    ("perdida_maxima_stop", "Pérdida máxima hasta el stop (%)", True),
    ("participacion_maxima_volumen", "Participación máxima en el volumen diario (%)", True),
)


def _configuracion_parametros() -> None:
    from informes_warrants.informe import parametros

    st.subheader("Parámetros del fondo")
    st.caption("Los fija el analista bajo su responsabilidad. Vacío = no se evalúa. Uso interno: se guardan en tu carpeta "
               "de datos, fuera del repositorio; en el informe solo salen los criterios y el riesgo que resultan.")
    actual = parametros.cargar()
    with st.form("parametros"):
        valores = {}
        for campo, etiqueta, en_pct in PARAMETROS:
            v = getattr(actual, campo)
            texto = st.text_input(etiqueta, "" if v is None else f"{v * 100 if en_pct else v:g}", key=f"par_{campo}")
            numero = float(texto.replace(",", ".")) if texto.strip() else None
            if numero is not None and en_pct:
                numero /= 100
            valores[campo] = int(numero) if numero is not None and campo == "horizonte_stop_dias" else numero
        if st.form_submit_button("Guardar parámetros"):
            parametros.guardar(parametros.ParametrosFondo(**valores))
            st.success("Parámetros guardados: se aplican al recomponer el informe.")


def main() -> None:
    st.set_page_config(page_title="Warrants & Co · Informes", layout="wide")
    try:
        configurar_identidad()
    except Exception:  # noqa: BLE001  (sin EDGAR_IDENTITY no se puede consultar la SEC: primeros pasos)
        pantalla_primeros_pasos()
        st.stop()
    iniciar_sesion()
    with st.sidebar:
        st.markdown("**WARRANTS & CO.** · Apertura de posiciones")
        st.session_state.ticker = st.text_input("Empresa (ticker)", st.session_state.ticker).strip().upper()
        pantalla = st.radio("Pantalla", PANTALLAS)
        with st.expander("Cómo se usa (4 pasos)"):
            st.markdown(GUIA)
    almacen = _almacen()
    _avisos_de_filings(almacen)
    if pantalla == "Configuración":
        pantalla_configuracion()
    elif not st.session_state.ticker:
        st.info("Escribe el ticker de una empresa cotizada en EEUU en la barra lateral.")
    elif pantalla == PANTALLAS[0]:
        pantalla_versiones(almacen, st.session_state.ticker)
    else:
        pantalla_editor(almacen, st.session_state.ticker)


main()
