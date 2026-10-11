import pytest

from informes_warrants.visual.pdf import _preparar_gtk

_preparar_gtk()  # en Windows, WeasyPrint necesita saber dónde están las DLL de GTK antes de importarse
weasyprint = pytest.importorskip("weasyprint", reason="Instala el extra [pdf] (y GTK en Windows) para probar el PDF")


def test_html_a_pdf_con_logo_y_acentos(tmp_path):
    from pathlib import Path

    from informes_warrants.visual.pdf import html_a_pdf

    raiz = Path(__file__).resolve().parent.parent
    html = """<!doctype html><html lang="es"><head><meta charset="utf-8">
    <style>@page { size: A4; margin: 2cm } body { color: #000; } h1 { color: #2B0B02; }</style></head>
    <body><img src="src/informes_warrants/plantillas/marca/logo.svg" width="80"><h1>Análisis · Apple Inc.</h1>
    <p>Recomendación: Mantener. Ingresos de 416.161,0 USD Mn (−1,2 %).</p></body></html>"""
    pdf = html_a_pdf(html, tmp_path / "prueba.pdf", base_url=raiz)
    assert pdf.startswith(b"%PDF") and (tmp_path / "prueba.pdf").stat().st_size > 1000
