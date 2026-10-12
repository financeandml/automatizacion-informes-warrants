"""Múltiplos frente a su propia historia (R11): bandas de PER, EV/EBITDA y P/FCF de los últimos años.

Adaptado de FinRobot `finrobot_desktop/finrobot/engine/primitives/historical_valuation.py`
(`compute_historical_band`, `_quantile`), AI4Finance Foundation, licencia Apache-2.0. Cambios, que
corrigen dos errores habituales de ese tipo de cálculo:
  1. **Acciones de cada ejercicio** (ajustadas por desdoblamientos), no las de hoy para todas las fechas:
     con recompras, usar las actuales infla la capitalización histórica y los múltiplos antiguos.
  2. **Sin sesgo de anticipación**: a cada precio se le asigna el último ejercicio YA PRESENTADO a la SEC
     (fecha de presentación del 10-K), no el último cerrado (sus cifras aún no se conocían).
Los precios deben ser cierres sin ajustar por dividendos (solo por desdoblamientos): los ajustados por
dividendos rebajan los precios antiguos y los múltiplos históricos.

  PER      = precio / BPA diluido del ejercicio
  EV/EBITDA = (precio · acciones + deuda neta ajustada) / EBITDA
  P/FCF    = precio · acciones / FCF tras remuneración en acciones
  Solo valores positivos y finitos. Cuantiles con interpolación lineal (como numpy).
"""

import bisect
import math
import statistics
from dataclasses import dataclass, field
from datetime import date

METRICAS = {"per": "PER", "ev_ebitda": "EV / EBITDA", "p_fcf": "P / FCF"}
MAX_PUNTOS_SERIE = 120


@dataclass(frozen=True)
class Anual:
    """Cifras de un ejercicio y fecha desde la que eran públicas."""

    disponible: date  # fecha de presentación del 10-K
    bpa: float | None
    ebitda: float | None
    fcf: float | None  # tras remuneración en acciones
    deuda_neta_ajustada: float | None  # DFN + otros componentes del EV
    acciones: float | None


@dataclass(frozen=True)
class Banda:
    metrica: str
    actual: float | None
    mediana: float | None = None
    p25: float | None = None
    p75: float | None = None
    p90: float | None = None
    n: int = 0
    serie: list[tuple[date, float]] = field(default_factory=list)
    percentil_actual: float | None = None  # posición del actual en la historia (0-1)


def cuantil(valores: list[float], q: float) -> float:
    """Cuantil con interpolación lineal inclusiva (FinRobot `_quantile`, igual que numpy por defecto)."""
    s = sorted(valores)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (pos - lo) * (s[hi] - s[lo])


def _multiplo(metrica: str, precio: float, a: Anual) -> float | None:
    if metrica == "per":
        return precio / a.bpa if a.bpa and a.bpa > 0 else None
    if not a.acciones or a.acciones <= 0:
        return None
    capitalizacion = precio * a.acciones
    if metrica == "ev_ebitda":
        if not a.ebitda or a.ebitda <= 0 or a.deuda_neta_ajustada is None:
            return None
        return (capitalizacion + a.deuda_neta_ajustada) / a.ebitda
    return capitalizacion / a.fcf if a.fcf and a.fcf > 0 else None


def banda(metrica: str, precios: list[tuple[date, float]], anuales: list[Anual]) -> Banda:
    """Banda histórica de `metrica`. El actual es el último punto de la serie (precio de hoy sobre el último
    ejercicio presentado): la misma base que la historia, para que el percentil compare iguales. El múltiplo
    LTM de la portada usa cifras más recientes y en una empresa que crece saldría siempre «barato»."""
    anuales = sorted(anuales, key=lambda a: a.disponible)
    fechas = [a.disponible for a in anuales]
    muestras = []
    for fecha, precio in precios:
        i = bisect.bisect_right(fechas, fecha) - 1  # último ejercicio ya presentado en esa fecha
        if i < 0 or precio is None or precio <= 0:
            continue
        m = _multiplo(metrica, precio, anuales[i])
        if m is not None and math.isfinite(m) and m > 0:
            muestras.append((fecha, m))
    if not muestras:
        return Banda(metrica, None)
    valores = [v for _, v in muestras]
    paso = max(1, math.ceil(len(muestras) / MAX_PUNTOS_SERIE))
    serie = muestras[::paso]
    if serie[-1] != muestras[-1]:
        serie.append(muestras[-1])
    actual = muestras[-1][1]
    percentil = sum(v <= actual for v in valores) / len(valores)
    return Banda(metrica, actual, statistics.median(valores), cuantil(valores, 0.25), cuantil(valores, 0.75),
                 cuantil(valores, 0.90), len(valores), serie, percentil)


def valor_implicito(b: Banda, f_ltm: dict, deuda_neta_ajustada: float, acciones: float, q: str = "mediana") -> float | None:
    """Precio por acción si la empresa cotizase a su múltiplo histórico (`mediana`, `p25` o `p75`) sobre el LTM."""
    m = getattr(b, q)
    if m is None or not acciones:
        return None
    if b.metrica == "per":
        return m * f_ltm["bpa_diluido"] if f_ltm.get("bpa_diluido") and f_ltm["bpa_diluido"] > 0 else None
    if b.metrica == "ev_ebitda":
        return (m * f_ltm["ebitda"] - deuda_neta_ajustada) / acciones if f_ltm.get("ebitda") and f_ltm["ebitda"] > 0 else None
    return m * f_ltm["fcf_tras_sbc"] / acciones if f_ltm.get("fcf_tras_sbc") and f_ltm["fcf_tras_sbc"] > 0 else None
