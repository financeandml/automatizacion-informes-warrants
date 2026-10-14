"""Informe completo (composición + HTML + PDF) sin conexión, con el 10-K FY2023 de Apple de referencia."""

from pathlib import Path

import pandas as pd
import pytest

from informes_warrants.calculo.calidad import revisar
from informes_warrants.calculo.normalizador import FuenteXBRL, normalizar
from informes_warrants.informe.cobertura import clasificar
from informes_warrants.informe.construir import componer
from informes_warrants.ingesta.mercado import Cotizacion

FIXTURE = Path(__file__).parent / "fixtures" / "aapl_10k_2023"


def _componer(**extra):
    return componer(**_datos(**extra))


def _datos(**extra) -> dict:
    """Argumentos de `componer` de prueba (lo que `reunir` traería de la SEC y del mercado)."""
    from edgar.xbrl import XBRL

    estados = normalizar(FuenteXBRL(XBRL.from_directory(FIXTURE), "0000320193-23-000106"), [2022, 2023], "AAPL")
    fechas = pd.date_range("2021-01-01", "2023-12-29", freq="B")
    serie = pd.Series(range(100, 100 + len(fechas)), index=fechas, dtype=float)
    return dict(
        ticker="AAPL", empresa="Apple Inc.", sic=3571, cobertura=clasificar("Operating Company", False),
        filing={"accession": "0000320193-23-000106", "fecha": "2023-11-03", "ejercicio": 2023},
        estados=estados, calidad=revisar(estados),
        cotizacion=Cotizacion("AAPL", 190.0, "2023-12-29", 199.0, 165.0, 180.0, 1.0e10),
        acciones=15.55e9, beta_estimada=1.2,
        comportamiento={"absoluta": {"1m": 0.01, "3m": 0.02, "12m": 0.45, "3a": None, "5a": None, "ytd": 0.48}},
        series_bolsa={"AAPL": serie, "S&P 500": serie * 0.9, "XLK": serie * 1.1},
        riesgos=[{"resumen": "Dependencia de la economía global.", "cita": "The Company's operations depend on conditions.",
                  "modelo": "prueba"}],
        riesgos_lista=["The Company's operations depend on conditions."], texto_negocio="", fecha="2023-12-30", **extra,
    )


@pytest.fixture(scope="module")
def contexto():
    return _componer()


def test_contexto_coherente(contexto):
    assert contexto["calidad"].nivel == "verde"
    assert contexto["fundamentales"][2023]["fcf"] == 99584e6
    assert contexto["recomendacion"] in ("Comprar", "Mantener", "Vender")
    assert contexto["pendientes"]  # el borrador marca lo que debe completar el analista


def test_html_del_informe(contexto):
    from informes_warrants.informe import render

    html = render.html(contexto)
    for esperado in ("Apple Inc.", "383.285", "99.584", 'class="pendiente"',
                     "RevenueFromContractWithCustomerExcludingAssessedTax", "DESCARGO DE RESPONSABILIDAD", "<svg"):
        assert esperado in html, esperado
    import re

    assert not re.search(r"\b(None|nan|inf)\b", html)  # ningún hueco sin formatear


def test_precio_objetivo_del_analista(contexto):
    """El analista fija el precio objetivo: el potencial y la propuesta se recalculan; el DCF no cambia."""
    from dataclasses import replace

    from informes_warrants.informe import render

    c = _componer(estimaciones=replace(contexto["estimaciones"], precio_objetivo_analista=250.0))
    assert c["precio_objetivo"] == 250.0
    assert c["potencial"] == pytest.approx(250.0 / 190.0 - 1)
    assert c["recomendacion"] == "Comprar"
    assert c["dcf"].valor_por_accion == contexto["dcf"].valor_por_accion
    assert c["potencial_dcf"] == contexto["potencial_dcf"]
    assert "Precio objetivo (analista)" in render.html(c)
    with pytest.raises(ValueError):
        _componer(estimaciones=replace(contexto["estimaciones"], precio_objetivo_analista=-1.0))


def test_pdf_del_informe(contexto, tmp_path):
    from informes_warrants.visual.pdf import _preparar_gtk

    _preparar_gtk()
    pytest.importorskip("weasyprint", reason="Instala el extra [pdf] para generar el PDF")
    from informes_warrants.informe import render

    destino = render.pdf(contexto, tmp_path / "AAPL.pdf")
    assert destino.read_bytes().startswith(b"%PDF") and destino.with_suffix(".html").exists()


def test_comparables_automaticos_avisan_sin_bloquear(contexto):
    """Sin lista del analista: precio solo por DCF y un aviso interno antes de emitir, que no bloquea la emisión."""
    from informes_warrants.almacenamiento.versiones import Version
    from informes_warrants.informe import render
    from informes_warrants.informe.construir import AVISO_COMPARABLES

    assert not contexto["comparables_del_analista"] and contexto["valor_multiplos"] is None
    assert contexto["precio_objetivo"] == pytest.approx(contexto["valor_dcf"])
    assert contexto["avisos_emision"][0] == AVISO_COMPARABLES  # (y el de parámetros del fondo sin definir)
    assert not any("lista de comparables" in p for p in contexto["pendientes"])  # no es un apartado pendiente
    v = Version("AAPL", 2023, "FY", 1, "x", "2023-11-03", contenido={"textos": {}, "avisos_emision": contexto["avisos_emision"]})
    assert AVISO_COMPARABLES in v.avisos() and v.confirmar().emitir().estado == "emitida"
    html = render.html(contexto)
    assert "El analista debe introducir su lista de comparables" in html  # la sección de comparables se mantiene
    for interno in ("informes-warrants", "--comparables", "pendiente*", AVISO_COMPARABLES):  # nada interno en el informe
        assert interno not in html, interno


def test_historial_y_multiplos_historicos_en_el_informe():
    """R11 y R17 con datos de prueba: bandas sobre cierres sin ajustar y precio objetivo de cada versión emitida."""
    from datetime import date, timedelta

    from informes_warrants.informe import render

    semanas = [(date(2021, 1, 1) + timedelta(weeks=i), 120.0 + i * 0.5) for i in range(156)]
    emitidas = [{"fecha": "2023-03-01", "precio_objetivo": 170.0, "cotizacion": 150.0, "recomendacion": "Comprar"}]
    c = _componer(precios_semanales=semanas, fechas_disponibles={2022: date(2022, 10, 28), 2023: date(2023, 11, 3)},
                  historial_resumenes=emitidas)
    assert c["bandas"]["per"].n and c["bandas"]["per"].actual == c["bandas"]["per"].serie[-1][1]
    assert [h["senal"] for h in c["historial"]] == ["acertada"]  # cotización actual 190 frente a objetivo 170
    html = render.html(c)
    assert "Múltiplos frente a su propia historia" in html and "Comprar" in html


def test_version_preparada_con_lo_del_analista(tmp_path, monkeypatch):
    """A11: la versión guarda textos, estimaciones, resumen, instantánea y PDF; lo del analista prevalece."""
    from informes_warrants.almacenamiento.almacen import Almacen
    from informes_warrants.almacenamiento.versiones import Estado, TransicionInvalida, Version
    from informes_warrants.informe import render, versionado

    monkeypatch.setattr(render, "pdf", lambda c, destino: destino)
    monkeypatch.setattr("informes_warrants.calculo.motor.recalculo.soffice", lambda: None)  # sin LibreOffice: aviso
    almacen = Almacen(tmp_path / "v.sqlite")
    v = Version("AAPL", 2023, "FY", 1, "0000320193-23-000106", "2023-11-03",
                contenido={"textos": {"conclusiones.perspectivas": "Mi tesis."}, "estimaciones": {"g": 0.02}})
    almacen.guardar(v)
    preparada, c = versionado.preparar(versionado.ultima_abierta(almacen, "AAPL"), almacen, con_ia=False, carpeta=tmp_path,
                                       datos=_datos())
    assert c["estimaciones"].g == 0.02  # se compone con las estimaciones del analista
    assert c["textos"]["conclusiones.perspectivas"] == "Mi tesis."  # lo escrito por el analista prevalece
    assert preparada.contenido["textos"]["conclusiones.perspectivas"] == "Mi tesis."
    assert {"resumen", "instantanea", "pdf", "calidad", "avisos_emision"} <= set(preparada.contenido)
    assert almacen.historial("AAPL")[0].contenido["pdf"].endswith("AAPL_FY2023_v1.pdf")
    assert preparada.contenido["modelo_xlsx"].endswith("AAPL_FY2023_v1.xlsx") and Path(preparada.contenido["modelo_xlsx"]).exists()
    assert any("segunda vía de cálculo" in x for x in preparada.contenido["avisos_emision"])  # avisa, no bloquea
    borrador = preparada.confirmar()
    assert borrador.avisos() and borrador.emitir().estado == Estado.EMITIDA  # los pendientes avisan, no bloquean
    rojo = Version("AAPL", 2023, "FY", 2, "x", "2023-11-03", estado=Estado.BORRADOR,
                   contenido={"textos": {}, "calidad": {"nivel": "rojo", "errores": ["activo ≠ pasivo + patrimonio"]}})
    with pytest.raises(TransicionInvalida, match="rojo"):
        rojo.emitir()


# --- A12: interfaz (lógica sin Streamlit y prueba de humo de la app) -----------------------------------------------

def test_logica_de_la_interfaz():
    from informes_warrants.ui import logica

    datos = _datos()
    c = logica.recomponer(datos, None, {"conclusiones.perspectivas": "Mi tesis."},
                          {"probabilidades": [0.2, 0.6, 0.2], "desencadenantes": {"base": "Se cumple el plan."}})
    assert c["textos"]["conclusiones.perspectivas"] == "Mi tesis."
    assert c["escenarios"].probabilidades == (0.2, 0.6, 0.2) and c["escenarios"].desencadenantes["base"] == "Se cumple el plan."
    nuevas, errores = logica.editar(c["estimaciones"], g=0.03, tasa_fiscal=1.5)
    assert nuevas.g == 0.03 and errores  # tasa fiscal fuera de rango
    assert logica.a_pantalla("g", 0.025) == 2.5 and logica.de_pantalla("g", 2.5) == 0.025 and logica.a_pantalla("beta", 1.1) == 1.1
    assert logica.motivos_para_no_emitir(c) == []  # los marcadores pendientes no impiden emitir…
    assert any(m.startswith("Pendiente del analista") for m in logica.pendientes_aviso(c))  # …pero se avisan
    assert set(logica.contenido_editable(c)) == {"textos", "estimaciones"}


def test_la_interfaz_arranca(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    from informes_warrants import ui

    monkeypatch.setenv("EDGAR_IDENTITY", "Prueba prueba@ejemplo.com")
    monkeypatch.setenv("INFORMES_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(Path(ui.__file__).parent / "app.py"), default_timeout=60).run()
    assert not app.exception
    assert any("ticker" in i.value for i in app.info)  # sin empresa elegida, pide el ticker
    app.sidebar.radio[0].set_value("Configuración").run()
    assert not app.exception and app.header[0].value == "Configuración"


def test_el_html_de_terceros_no_se_ejecuta():
    from informes_warrants.informe.render import _md

    salida = str(_md("Texto <script>alert(1)</script> de AT&T y [[ANALISTA: completar]]\n\n> cita"))
    assert "<script>" not in salida and "&lt;script" in salida  # se ve como texto, no se ejecuta
    assert '<span class="pendiente">completar</span>' in salida and "<blockquote>" in salida and "AT&amp;T" in salida


def test_borradores_de_la_ia_en_el_informe():
    from informes_warrants.informe import render
    from informes_warrants.informe.plantillas import MARCADOR

    instruccion = next(m.strip() for t in _componer()["textos"].values() for m in MARCADOR.findall(t))
    c = _componer(borradores_ia={instruccion: "Borrador de prueba sin cifras."})
    assert any("revisar el borrador de la IA" in p for p in c["pendientes"])  # sigue siendo tarea del analista
    html = render.html(c)
    assert 'class="borrador-ia"' in html and "Borrador de prueba sin cifras." in html


def test_comparacion_de_versiones_en_la_interfaz():
    """B9: textos, estimaciones, recomendación y atribución del cambio de valor entre dos versiones."""
    from dataclasses import asdict

    from informes_warrants.almacenamiento.versiones import Version
    from informes_warrants.informe.cambios import resumen
    from informes_warrants.ui import logica

    c1 = _componer()
    c2 = logica.recomponer(_datos(), logica.editar(c1["estimaciones"], g=0.03)[0], {"conclusiones.perspectivas": "Nueva tesis."})

    def version(c, revision):
        return Version("AAPL", 2023, "FY", revision, "x", "2023-11-03", contenido={
            "textos": c["textos"], "estimaciones": asdict(c["estimaciones"]), "resumen": resumen(c),
            "recomendacion": c["recomendacion"]})

    r = logica.comparacion(version(c1, 1), version(c2, 2))
    assert "conclusiones.perspectivas" in r["textos"] and r["estimaciones"]["g"] == (c1["estimaciones"].g, 0.03)
    pasos = r["valoracion"]["atribucion"]["pasos"]
    assert sum(p["impacto"] for p in pasos) == pytest.approx(r["valoracion"]["atribucion"]["total"])
    assert next(p for p in pasos if p["grupo"] == "Crecimiento a perpetuidad")["impacto"] > 0  # g más alto, más valor



def test_gestion_de_la_posicion_con_parametros_del_fondo():
    """B4: criterios, stop por volatilidad y tamaño con los parámetros del analista; sin ellos, solo un aviso interno."""
    from informes_warrants.informe import render
    from informes_warrants.informe.construir import AVISO_PARAMETROS
    from informes_warrants.informe.parametros import ParametrosFondo

    assert AVISO_PARAMETROS in _componer()["avisos_emision"]
    p = ParametrosFondo(potencial_minimo=0.15, per_maximo=30.0, capital_cartera=10e6, riesgo_por_posicion=0.01,
                        multiplo_volatilidad=2.0, horizonte_stop_dias=20, perdida_maxima_stop=0.10, peso_maximo=0.05)
    c = _componer(parametros=p)
    assert AVISO_PARAMETROS not in c["avisos_emision"]
    g = c["gestion"]
    assert [k["criterio"] for k in g["criterios"]] == ["Potencial frente al precio objetivo", "PER (LTM)"]
    r = g["riesgo"]
    assert r["perdida"] <= 0.10 and r["peso"] <= 0.05 + 1e-9 and r["stop"] < c["cotizacion"].precio
    assert "Gestión de la posición" in render.html(c) and "Stop por volatilidad" in render.html(c)


# --- B1: motor de valoración en el informe ----------------------------------------------------------------------------

def test_motor_de_valoracion_en_el_informe(contexto):
    """El modelo se calcula sin celdas en error, el WACC cuadra con sus componentes y el DCF del informe es el del modelo."""
    from informes_warrants.calculo.motor.excel import Error

    m = contexto["motor"]["modelo"]
    s = m.salidas
    assert not [k for k, v in m.valores.items() if isinstance(v, Error)]
    assert all(s[k] is not False for k in s if k.startswith("control_"))  # cuadran todos (uno es informativo: la convención)
    # el 10-K de 2023 trae 2 ejercicios: los 3 anteriores quedan «--» en el libro y se avisa
    assert any("marcadas «--»" in x for x in m.avisos)
    assert s["ke"] == pytest.approx(0.045 + 1.2 * 0.055)
    tasa = (19300 / 119103 + 16741 / 113736 + 16741 / 113736) / 3  # media de la plantilla (FY2022, FY2023 y LTM)
    e, d = 190.0 * 15550, 111088.0
    assert s["wacc"] == pytest.approx(e / (e + d) * s["ke"] + d / (e + d) * s["kd"] * (1 - tasa))
    assert contexto["valor_dcf"] == pytest.approx(s["precio_dcf"])
    fila = s["sensibilidad"][2]  # g central: la celda central es el DCF; más WACC, menos valor; más g, más valor
    assert fila[2] == pytest.approx(s["precio_dcf"])
    wacc, tgr = s["sensibilidad_wacc"], s["sensibilidad_tgr"]
    assert wacc == sorted(wacc, reverse=True) and tgr == sorted(tgr)  # la plantilla ordena el WACC de mayor a menor
    assert fila == sorted(fila)  # menos WACC (a la derecha), más valor
    columna = [f[2] for f in s["sensibilidad"]]
    assert columna == sorted(columna)  # más g, más valor


def test_entradas_del_analista_en_el_motor(contexto):
    """Fin de año descuenta medio año más que mitad de año; la versión guarda solo lo que el analista cambió."""
    from dataclasses import replace

    from informes_warrants.ui import logica

    fin = _componer(estimaciones=replace(contexto["estimaciones"], motor={"convencion": 2}))
    assert fin["motor"]["modelo"].salidas["convencion"] == 2
    assert fin["valor_dcf"] < contexto["valor_dcf"]
    assert replace(contexto["estimaciones"], motor={"convencion": 3}).validar()
    actuales, defecto = logica.entradas_motor(contexto)
    segmento = next(iter(actuales.crecimientos))
    propio = logica.motor_del_analista(defecto, {segmento: [0.1] * 6}, dict(actuales.margenes), actuales.pct_perpetuidad, 2, True, False)
    assert propio == {"crecimientos": {segmento: [0.1] * 6}, "convencion": 2}
    todo = logica.motor_del_analista(defecto, dict(actuales.crecimientos), dict(actuales.margenes), 0.8, 1, True, True)
    assert set(todo) == set(logica.CLAVES_MOTOR)
    assert logica.libro_del_motor(contexto)[:2] == b"PK"  # .xlsx para el botón de descarga


def test_libro_del_motor_junto_al_pdf(contexto, tmp_path, monkeypatch):
    """El .xlsx se guarda con fórmulas vivas; sin LibreOffice, la segunda vía avisa y no bloquea."""
    import openpyxl

    from informes_warrants.informe.motor import exportar

    monkeypatch.setattr("informes_warrants.calculo.motor.recalculo.soffice", lambda: None)
    ruta, avisos = exportar(contexto, tmp_path / "AAPL.pdf")
    assert ruta.endswith("AAPL.xlsx") and any("LibreOffice" in a for a in avisos)
    wb = openpyxl.load_workbook(ruta)
    assert {"Entradas", "Operating Model", "WACC", "Consolidated", "LBO", "Controles", "Trazabilidad"} <= set(wb.sheetnames)
    assert str(wb["WACC"]["F22"].value).startswith("=")


def test_contraste_con_libreoffice(contexto, tmp_path):
    """Segunda vía de cálculo (D3): cada celda con fórmula, igual en Python y en LibreOffice (solo si está instalado)."""
    from informes_warrants.calculo.motor.recalculo import soffice
    from informes_warrants.informe.motor import exportar

    if soffice() is None:
        pytest.skip("LibreOffice no está instalado")
    _, avisos = exportar(contexto, tmp_path / "AAPL.pdf")
    assert any("coinciden con LibreOffice" in a for a in avisos), avisos


def test_dcf_negativo_del_motor_no_entra_en_el_precio(contexto):
    """Un DCF con valor por acción ≤ 0 no es una valoración: se avisa, el texto lo explica y no entra en el precio objetivo."""
    from dataclasses import replace

    segmento = next(iter(contexto["motor"]["datos"].segmentos)).nombre
    c = _componer(estimaciones=replace(contexto["estimaciones"], motor={"margenes": {segmento: [-0.3] * 6}}))
    assert c["motor"]["modelo"].salidas["precio_dcf"] < 0
    assert c["valor_dcf"] is None and c["potencial_dcf"] is None
    assert any("no entra en el precio objetivo" in a for a in c["avisos_emision"])
    assert "valor por acción negativo (−" in c["textos"]["valoracion.comentario"]
    assert next(m for m in c["metodos"] if m.nombre == "DCF").valor is None
