import pytest

from informes_warrants.ia import seleccion
from informes_warrants.ia.bloques import frases_candidatas
from informes_warrants.ia.llm import LLMSettings
from informes_warrants.ingesta.riesgos import titulos_de_riesgo

HTML = """<html><body>
<p><span style="font-weight:700">Item 1A. Risk Factors</span></p>
<p><span style="font-style: italic; font-weight: 700">The Company’s business depends on global economic conditions.</span></p>
<p><span>The Company has international operations and adverse conditions can hurt results.</span></p>
<p><b>Competition could reduce the Company's margins and market share.</b></p>
<p><b>Short.</b> <i>This italic sentence is not part of Item 1A at all, so it is ignored.</i></p>
</body></html>"""
ITEM_1A = ("Item 1A. Risk Factors The Company's business depends on global economic conditions. The Company has "
           "international operations and adverse conditions can hurt results. Competition could reduce the "
           "Company's margins and market share. Competitors are strong.")


def test_titulos_de_riesgo_literales_y_solo_del_item_1a():
    assert titulos_de_riesgo(HTML, ITEM_1A) == [
        "The Company's business depends on global economic conditions.",
        "Competition could reduce the Company's margins and market share.",
    ]


def test_seleccion_cita_siempre_literal(monkeypatch):
    titulos = titulos_de_riesgo(HTML, ITEM_1A)
    cfg = LLMSettings("ollama", "m", "http://x", "k")
    respuesta = '[{"n": 2, "resumen": "Competencia en márgenes."}, {"n": 9, "resumen": "Inventado"}, {"n": 2, "resumen": "Repetido"}]'
    monkeypatch.setattr(seleccion, "completar", lambda s, u, c: (respuesta, cfg))
    elegidos, usado = seleccion.seleccionar(titulos + ["Frase que no está en el 10-K."], ITEM_1A, "Elige", cfg=cfg)
    assert [(e.resumen, e.cita) for e in elegidos] == [("Competencia en márgenes.", titulos[1])]
    assert usado is cfg


def test_respuesta_sin_json_es_un_error(monkeypatch):
    cfg = LLMSettings("ollama", "m", "http://x", "k")
    monkeypatch.setattr(seleccion, "completar", lambda s, u, c: ("No sé", cfg))
    with pytest.raises(ValueError):
        seleccion.seleccionar(["The Company's business depends on global economic conditions."], ITEM_1A, "Elige", cfg=cfg)


def test_frases_candidatas_del_mdna():
    texto = "We expect revenue growth from new products in 2026 across all geographic segments and channels. Hola. " * 2
    candidatas, total = frases_candidatas(texto)
    assert total == 2 and all("expect" in c for c in candidatas)


def test_proveedor_por_defecto(monkeypatch):
    for var in ("LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL", "GROQ_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("informes_warrants.ia.llm.load_dotenv", lambda: None)
    assert LLMSettings.desde_entorno().proveedor == "ollama"
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    assert (LLMSettings.desde_entorno().proveedor, LLMSettings.desde_entorno().modelo) == ("groq", "openai/gpt-oss-120b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    cfg = LLMSettings.desde_entorno()
    assert (cfg.proveedor, cfg.modelo) == ("openrouter", "meta-llama/llama-4-scout")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert LLMSettings.desde_entorno().proveedor == "groq"
    monkeypatch.delenv("LLM_PROVIDER")
    monkeypatch.setenv("GEMINI_API_KEY", "g-x")  # Gemini, primero si hay clave (usuario, 2026-10-15)
    assert (LLMSettings.desde_entorno().proveedor, LLMSettings.desde_entorno().modelo) == ("gemini", "gemini-3.8-flash")



def _cfg():
    return LLMSettings("prueba", "modelo", "http://x", "k")


def test_lecturas_de_los_hechos_sin_cifras_nuevas(monkeypatch):
    """P1: la lectura que trae una cifra que no está en el hecho se descarta."""
    from informes_warrants.ia import etiquetas

    respuesta = '[{"n": 1, "lectura": "El crecimiento del 14,2 % refuerza la tesis."}, {"n": 2, "lectura": "Margen del 40 % récord."}]'
    monkeypatch.setattr(etiquetas, "completar", lambda s, u: (respuesta, _cfg()))
    lecturas, modelo = etiquetas.lecturas_hechos(["Ingresos: 466.823 USD Mn (+14,2 % interanual)", "El margen mejoró 339 pb"])
    assert lecturas == ["El crecimiento del 14,2 % refuerza la tesis.", None] and modelo == "prueba · modelo"


def test_clasificacion_de_riesgos_solo_con_categorias_validas(monkeypatch):
    """P2: categoría y supuesto de una lista cerrada; lo demás se ignora."""
    from informes_warrants.ia import etiquetas

    respuesta = ('[{"n": 1, "categoria": "competencia", "supuesto": "margen", "probabilidad": "alta", "impacto": "media"}, '
                 '{"n": 2, "categoria": "astrología", "supuesto": "margen"}]')
    monkeypatch.setattr(etiquetas, "completar", lambda s, u: (respuesta, _cfg()))
    r = etiquetas.clasificar_riesgos([{"resumen": "a", "cita": "Markets are competitive."}, {"resumen": "b", "cita": "Other."}])
    assert (r[0]["categoria"], r[0]["supuesto"]) == ("competencia", "margen") and "categoria" not in r[1]
    assert (r[0]["probabilidad"], r[0]["impacto"]) == ("alta", "media")  # P16: matriz de riesgos


def test_emparejar_miembros_de_segmento(monkeypatch):
    """F7: solo pares de nombres que existen y uno a uno."""
    from informes_warrants.ia import etiquetas

    respuesta = '[{"trimestral": "Cloud & Software", "anual": "Cloud and Software"}, {"trimestral": "Inventado", "anual": "Hardware"}]'
    monkeypatch.setattr(etiquetas, "completar", lambda s, u: (respuesta, _cfg()))
    assert etiquetas.emparejar_miembros(["Cloud and Software", "Hardware"], ["Cloud & Software", "Hardware"]) == {
        "Cloud & Software": "Cloud and Software"}


def test_guidance_del_comunicado_con_cita_literal(monkeypatch):
    """P22: la guidance es la frase literal del 8-K; un resumen con cifras que no están en la cita se vacía."""
    from informes_warrants.ia import consenso, seleccion

    texto = ("Revenue grew 16% in the quarter. For Q3, we expect revenue growth of 12% (or 11% F/X neutral). "
             "We continue to anticipate an operating margin of 31.5% for 2026.")
    respuesta = '[{"n": 1, "resumen": "Prevén un crecimiento del 12 % en el tercer trimestre."}, {"n": 2, "resumen": "Margen del 35 %."}]'
    monkeypatch.setattr(seleccion, "completar", lambda s, u, c: (respuesta, _cfg()))
    g = consenso.guidance_8k(texto, "0001065280-26-000001", "2026-07-16")
    assert [x["cita"][:16] for x in g["lista"]] == ["For Q3, we expec", "We continue to a"]
    assert g["lista"][0]["resumen"].startswith("Prevén") and g["lista"][1]["resumen"] == ""  # 35 % no está en la cita


def test_consenso_publicado_verificado_en_su_fuente(monkeypatch):
    """P22: una estimación entra solo si su frase literal está en la página citada y su valor es una cifra de esa frase."""
    from informes_warrants.ia import consenso, gemini

    datos = {"estimaciones": [
        {"concepto": "bpa", "ejercicio": "FY2027", "valor": 8.12, "unidad": "USD", "analistas": 41, "url": "https://x.com/a",
         "literal": "Next Year (2027) 8.12"},
        {"concepto": "ventas", "ejercicio": "FY2027", "valor": 470.0, "unidad": "USD bn", "analistas": None, "url": "https://x.com/a",
         "literal": "Revenue estimate 470B"}]}
    monkeypatch.setattr(gemini, "disponible", lambda: True)
    monkeypatch.setattr(gemini, "generar", lambda *a, **k: {"datos": datos, "modelo": "gemini-2.5-flash", "fuentes": []})
    monkeypatch.setattr(gemini, "texto_de_pagina", lambda url: "Earnings Estimate Next Year (2027) 8.12 Avg. Estimate")
    r = consenso.consenso_publicado("AAPL", "Apple Inc.")
    assert [e["valor"] for e in r["estimaciones"]] == [8.12] and r["descartadas"] == 1


def test_json_de_la_respuesta_de_gemini():
    from informes_warrants.ia.gemini import extraer_json

    bloque = chr(96) * 3
    assert extraer_json(bloque + "json" + chr(10) + '{"a": [1, 2]}' + chr(10) + bloque) == {"a": [1, 2]}
    assert extraer_json("sin json") is None
