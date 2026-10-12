"""Gráficos del informe en SVG vectorial (matplotlib), con la identidad de Warrants & Co.

Solo tres colores (docs/identidad-corporativa.md): burdeos #2B0B02, negro #000000 y blanco. Las
series se distinguen por relleno, trazo y grosor, nunca por colores nuevos. Tipografía Inter.
La lógica de qué mostrar sale de las métricas ya calculadas: aquí no se calcula nada financiero.
"""

import io
import itertools
import re
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

BURDEOS, NEGRO, BLANCO = "#2B0B02", "#000000", "#FFFFFF"
FUENTES = Path(__file__).resolve().parent.parent / "plantillas" / "fuentes"
ANCHO_CM, ALTO_CM = 8.6, 5.2
_contador = itertools.count(1)

for ttf in FUENTES.glob("*.ttf"):
    font_manager.fontManager.addfont(str(ttf))

plt.rcParams.update({
    "font.family": "Inter", "font.size": 6.5, "axes.edgecolor": NEGRO, "axes.linewidth": 0.5,
    "axes.labelcolor": NEGRO, "xtick.color": NEGRO, "ytick.color": NEGRO, "text.color": NEGRO,
    "xtick.major.width": 0.4, "ytick.major.width": 0.4, "xtick.major.size": 2, "ytick.major.size": 2,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 6,
    "svg.fonttype": "none",  # el texto queda como texto: nítido y con la fuente del PDF
    "hatch.color": BURDEOS, "hatch.linewidth": 0.5,
})


def _figura():
    fig, ax = plt.subplots(figsize=(ANCHO_CM / 2.54, ALTO_CM / 2.54), dpi=100)
    ax.yaxis.grid(True, color=NEGRO, linewidth=0.15)
    ax.set_axisbelow(True)
    return fig, ax


def _svg(fig) -> str:
    buffer = io.StringIO()
    fig.savefig(buffer, format="svg", bbox_inches="tight", pad_inches=0.02, transparent=True)
    plt.close(fig)
    texto = buffer.getvalue()
    texto = texto[texto.index("<svg"):]
    prefijo = f"g{next(_contador)}_"  # ids únicos: varios SVG en el mismo HTML no deben repetirlos
    texto = re.sub(r'id="([^"]+)"', lambda m: f'id="{prefijo}{m.group(1)}"', texto)
    es_color = re.compile(r"[0-9A-Fa-f]{3,8}").fullmatch  # #2b0b02 es un color, no una referencia
    return re.sub(r"#([A-Za-z_][\w.-]*)", lambda m: m.group(0) if es_color(m.group(1)) else f"#{prefijo}{m.group(1)}", texto)


def _miles(x, _=None):
    return f"{x:,.0f}".replace(",", ".")


def _pct(x, _=None):
    return f"{x * 100:.0f} %"


def barras_y_linea(etiquetas, barras, linea, nombre_barras, nombre_linea) -> str:
    """Barras burdeos (eje izq., USD Mn) + línea negra (eje dcho., %): p. ej. ingresos y margen EBITDA."""
    fig, ax = _figura()
    ax.bar(etiquetas, barras, color=BURDEOS, width=0.6, label=nombre_barras)
    ax.yaxis.set_major_formatter(_miles)
    eje = ax.twinx()
    eje.plot(etiquetas, linea, color=NEGRO, linewidth=1.2, marker="o", markersize=2.5, label=nombre_linea)
    eje.yaxis.set_major_formatter(_pct)
    eje.spines["right"].set_visible(True)
    eje.spines["top"].set_visible(False)
    validos = [v for v in linea if v is not None]
    eje.set_ylim(0, max(max(validos, default=0.0), 0.01) * 1.3)  # sin datos de la línea (p. ej. EBITDA n.d.): eje vacío
    handles = ax.get_legend_handles_labels()[0] + eje.get_legend_handles_labels()[0]
    ax.legend(handles, [nombre_barras, nombre_linea], loc="upper left", ncol=2, bbox_to_anchor=(0, 1.16))
    return _svg(fig)


def _separador(ax, posicion: int | None) -> None:
    """Línea discontinua entre datos reales y estimados (etiquetas «e» a la derecha)."""
    if posicion:
        ax.axvline(posicion - 0.5, color=NEGRO, linewidth=0.5, linestyle=(0, (3, 2)))


def barras_pareadas(etiquetas, serie_a, serie_b, nombre_a, nombre_b, separar_en: int | None = None) -> str:
    """Dos series en barras: A sólida burdeos, B blanca con trama burdeos (p. ej. beneficio neto vs FCF)."""
    import numpy as np

    fig, ax = _figura()
    x, ancho = np.arange(len(etiquetas)), 0.38
    ax.bar(x - ancho / 2, serie_a, ancho, color=BURDEOS, label=nombre_a)
    ax.bar(x + ancho / 2, serie_b, ancho, color=BLANCO, edgecolor=BURDEOS, hatch="//////", linewidth=0.5, label=nombre_b)
    ax.set_xticks(x, etiquetas)
    ax.yaxis.set_major_formatter(_miles)
    ax.axhline(0, color=NEGRO, linewidth=0.4)
    _separador(ax, separar_en)
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.16))
    return _svg(fig)


# Rellenos para series apiladas: solo los tres colores de la marca (sólidos y tramas)
RELLENOS = [dict(color=BURDEOS), dict(color=NEGRO), dict(color=BLANCO, edgecolor=BURDEOS, hatch="//////"),
            dict(color=BLANCO, edgecolor=NEGRO, hatch="......"), dict(color=BLANCO, edgecolor=BURDEOS, hatch="xxxx"),
            dict(color=BLANCO, edgecolor=NEGRO, hatch="\\\\\\")]


def barras_apiladas(etiquetas, series: dict[str, list], ancho_relativo: float = 0.6) -> str:
    """Barras apiladas (p. ej. ingresos por segmento, USD mn); como máximo 6 series (el resto, agrupado antes)."""
    import numpy as np

    fig, ax = _figura()
    x = np.arange(len(etiquetas))
    base = np.zeros(len(etiquetas))
    for (nombre, valores), relleno in zip(series.items(), RELLENOS, strict=False):
        v = np.array([0.0 if x_ is None else x_ for x_ in valores])
        ax.bar(x, v, ancho_relativo, bottom=base, linewidth=0.4, label=nombre, **{"edgecolor": BLANCO, **relleno})
        base += v
    ax.set_xticks(x, etiquetas)
    ax.yaxis.set_major_formatter(_miles)
    ax.legend(loc="upper left", ncol=3, bbox_to_anchor=(0, 1.22), fontsize=5.5)
    return _svg(fig)


def rangos_valoracion(metodos: list[tuple[str, float | None, float | None, float | None]], cotizacion: float,
                      objetivo: float | None) -> str:
    """Rangos por método (barra bajo-alto y punto central) frente a la cotización y al precio objetivo (USD)."""
    validos = [m for m in metodos if m[1] is not None or (m[2] is not None and m[3] is not None)]
    fig, ax = plt.subplots(figsize=(ANCHO_CM * 2 / 2.54, (1.2 + 0.55 * len(validos)) / 2.54 * 1.6), dpi=100)
    ax.xaxis.grid(True, color=NEGRO, linewidth=0.15)
    ax.set_axisbelow(True)
    for i, (_nombre, central, bajo, alto) in enumerate(reversed(validos)):
        if bajo is not None and alto is not None:
            ax.barh(i, alto - bajo, left=bajo, height=0.45, color=BLANCO, edgecolor=BURDEOS, hatch="//////", linewidth=0.6)
        if central is not None:
            ax.plot([central], [i], marker="D", markersize=3.2, color=BURDEOS)
    ax.set_yticks(range(len(validos)), [m[0] for m in reversed(validos)])
    ax.axvline(cotizacion, color=NEGRO, linewidth=0.9, label="Cotización")
    if objetivo is not None:
        ax.axvline(objetivo, color=BURDEOS, linewidth=1.2, linestyle=(0, (4, 2)), label="Precio objetivo")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.0 + 0.9 / max(len(validos), 1)))
    return _svg(fig)


def serie_multiplo(serie: list[tuple], mediana: float, p25: float, p75: float, actual: float | None, nombre: str) -> str:
    """Múltiplo histórico (línea burdeos) con su mediana (negra) y sus cuartiles (discontinuas)."""
    fig, ax = _figura()
    fechas, valores = [f for f, _ in serie], [v for _, v in serie]
    ax.plot(fechas, valores, color=BURDEOS, linewidth=1.2, label=nombre)
    ax.axhline(mediana, color=NEGRO, linewidth=0.9, label="Mediana")
    for q in (p25, p75):
        ax.axhline(q, color=NEGRO, linewidth=0.6, linestyle=(0, (3, 2)))
    if actual is not None:
        ax.plot([fechas[-1]], [actual], marker="o", markersize=3, color=NEGRO)
    ax.yaxis.set_major_formatter(lambda x, _=None: f"{x:.0f}x")
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.16))
    fig.autofmt_xdate(rotation=0, ha="center")
    return _svg(fig)


def historial_recomendacion(precios, puntos: list[tuple]) -> str:
    """Cotización (línea negra) y precio objetivo de cada informe emitido (escalones burdeos)."""
    fig, ax = _figura()
    ax.plot(precios.index, precios.values, color=NEGRO, linewidth=0.9, label="Cotización")
    if puntos:
        fechas = [p[0] for p in puntos] + [precios.index[-1]]
        objetivos = [p[1] for p in puntos] + [puntos[-1][1]]
        ax.step(fechas, objetivos, where="post", color=BURDEOS, linewidth=1.2, label="Precio objetivo")
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.16))
    fig.autofmt_xdate(rotation=0, ha="center")
    return _svg(fig)


def lineas(etiquetas, series: dict[str, list], porcentaje: bool = True) -> str:
    """Hasta tres líneas: burdeos sólida, negra sólida y negra discontinua."""
    estilos = [dict(color=BURDEOS, linewidth=1.4), dict(color=NEGRO, linewidth=1.0), dict(color=NEGRO, linewidth=0.9, linestyle="--")]
    fig, ax = _figura()
    for (nombre, valores), estilo in zip(series.items(), estilos, strict=False):
        ax.plot(etiquetas, valores, label=nombre, marker="o" if len(etiquetas) < 12 else None, markersize=2.5, **estilo)
    if porcentaje:
        ax.yaxis.set_major_formatter(_pct)
    ax.legend(loc="upper left", ncol=len(series), bbox_to_anchor=(0, 1.16))
    return _svg(fig)


def base_100(series: dict[str, "object"]) -> str:
    """Evolución bursátil en base 100 (pandas.Series de cierres alineadas por fecha)."""
    import pandas as pd

    tabla = pd.concat({k: s.resample("W-FRI").last() for k, s in series.items()}, axis=1).dropna()  # semanal: sin ruido diario
    tabla = tabla / tabla.iloc[0] * 100
    estilos = [dict(color=BURDEOS, linewidth=1.3), dict(color=NEGRO, linewidth=0.8), dict(color=NEGRO, linewidth=0.8, linestyle="--")]
    fig, ax = _figura()
    for (nombre, serie), estilo in zip(tabla.items(), estilos, strict=False):
        ax.plot(serie.index, serie.values, label=nombre, **estilo)
    ax.axhline(100, color=NEGRO, linewidth=0.3)
    ax.legend(loc="upper left", ncol=len(series), bbox_to_anchor=(0, 1.16))
    fig.autofmt_xdate(rotation=0, ha="center")
    return _svg(fig)
