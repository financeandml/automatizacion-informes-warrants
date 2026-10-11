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
    for var in ("LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
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
