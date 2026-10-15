"""Borradores de la IA para los apartados del analista (decisión del usuario, 2026-10-14).

Cada `[[ANALISTA: instrucción]]` recibe un borrador para ayudar al analista, que sigue siendo quien escribe el
informe: el borrador se muestra marcado («Borrador de la IA · el analista debe revisarlo») y cuenta como pendiente.

Salvaguardas (regla 9, cero alucinaciones):
- El modelo solo recibe lo que ya dice el informe (sus textos con las cifras calculadas por `calculo/`, los riesgos,
  los catalizadores, la competencia y la cita del Item 1). No recibe ni puede usar nada más.
- Toda cifra del borrador debe estar en ese contexto: si aparece una cifra nueva, el borrador se descarta.
- Si el contexto no basta (p. ej. el tamaño del mercado o la composición del consejo, que la SEC no estructura),
  el modelo responde «SIN DATOS» y el apartado queda con su marcador, como antes.
"""

import logging
import re

from .bloques import _cifras
from .llm import LLMSettings, completar

log = logging.getLogger(__name__)

SISTEMA = (
    "Eres analista de renta variable. Escribes en español de España un BORRADOR breve de un apartado de un informe de "
    "apertura de posición, para que el analista lo revise. Usas exclusivamente la información del contexto: no añades "
    "datos, cifras, fechas ni nombres que no estén en él, y no opinas más allá de lo que el contexto permite justificar. "
    "Las cifras del contexto son de la empresa: nunca las presentes como cifras de su mercado o de su sector. Si el "
    "apartado pide datos que el contexto no tiene (tamaño o cuotas del mercado, composición del consejo, fuentes "
    "externas), responde exactamente: SIN DATOS. Si usas una cifra, cópiala exactamente como aparece en el contexto "
    "(sin redondear, sin convertirla ni calcular otras); si no, no uses cifras. No cites el contexto ni uses "
    "corchetes. {extension}"
)
EXTENSION_PARRAFO = "Un solo párrafo, sin listas, sin títulos ni negritas, de 40 a 120 palabras."
EXTENSION_FRASE = "Una sola frase de como máximo 30 palabras, sin negritas."
MAX_PALABRAS_FRASE = 35
SIN_DATOS = "SIN DATOS"
MAX_CARACTERES_CONTEXTO = 14000
MAX_CARACTERES_BORRADOR = 1200


def _es_frase(instruccion: str) -> bool:
    return "titular" in instruccion.lower() or "una frase" in instruccion.lower()


def verificar_borrador(borrador: str, contexto: str, frase: bool = False) -> str:
    """Motivo por el que el borrador no vale ("" si vale)."""
    texto = (borrador or "").strip()
    if not texto or texto.upper().startswith(SIN_DATOS):
        return "el contexto no basta"
    if len(texto) > MAX_CARACTERES_BORRADOR or "[" in texto or "]" in texto or "||" in texto:
        return "formato no válido"
    if frase and len(texto.split()) > MAX_PALABRAS_FRASE:
        return "demasiado largo para una frase"
    nuevas = sorted(set(_cifras(texto)) - set(_cifras(contexto)))
    if nuevas:
        return f"cifras que no están en el informe: {', '.join(nuevas[:5])}"
    return ""


def contexto(c: dict, texto_negocio: str = "") -> str:
    """Lo que el informe ya dice, en texto: es lo único que puede usar el modelo."""
    partes = [f"Empresa: {c['empresa']} ({c['ticker']}). Fecha del informe: {c['fecha']}."]
    for texto in c["textos"].values():
        if texto and "[[" not in texto:  # solo lo ya escrito (no otros apartados pendientes)
            partes.append(re.sub(r"[*_#>]", "", texto).strip())
    partes += [f"Riesgo: {r['resumen']}" for r in c.get("riesgos") or [] if r.get("resumen") and "[[" not in r["resumen"]]
    partes += [f"Catalizador: {s['resumen']}" for s in ((c.get("catalizadores") or {}).get("ia") or {}).get("lista") or []]
    if c.get("cita_negocio"):
        partes.append(f"Descripción de la empresa (Item 1 del 10-K): {c['cita_negocio']}")
    if texto_negocio:
        partes.append(f"Extracto del Item 1 del 10-K: {' '.join(texto_negocio.split())[:4000]}")
    return "\n".join(partes)[:MAX_CARACTERES_CONTEXTO]


LOTE = 12  # apartados por llamada: el contexto va una vez por lote (Groq gratuito limita los tokens por minuto)
FORMATO_LOTE = (
    "Te pido varios apartados numerados. Responde con un bloque por apartado, en el mismo orden, y empieza cada bloque "
    "con una línea que solo diga «### n» (n = número del apartado). Cada apartado se valora por separado: si a uno le "
    "faltan datos, ese bloque dice exactamente SIN DATOS."
)


def _bloques(respuesta: str, n: int) -> dict[int, str]:
    """{número: texto} de una respuesta por bloques «### n»."""
    partes = re.split(r"^[ \t*]*#{1,4}\s*(\d+)[ \t*]*$", respuesta or "", flags=re.M)
    return {int(partes[i]): partes[i + 1].strip() for i in range(1, len(partes) - 1, 2) if 1 <= int(partes[i]) <= n}


def generar(instrucciones: list[str], contexto_informe: str, cfg: LLMSettings | None = None) -> dict[str, str]:
    """{instrucción: borrador verificado}. Las instrucciones sin borrador válido no aparecen (quedan para el analista).

    Se piden por lotes de `LOTE` (antes, una llamada por apartado con todo el contexto: ~20 llamadas y esperas de
    20-110 s cada una por el límite de Groq); cada borrador se verifica por separado, como antes."""
    borradores = {}
    unicas = list(dict.fromkeys(instrucciones))
    sistema = SISTEMA.format(extension="Respeta en cada apartado la extensión indicada entre paréntesis.") + " " + FORMATO_LOTE
    for inicio in range(0, len(unicas), LOTE):
        lote = unicas[inicio:inicio + LOTE]
        pedidos = "\n".join(f"{n}. {ins} ({EXTENSION_FRASE if _es_frase(ins) else EXTENSION_PARRAFO})"
                            for n, ins in enumerate(lote, 1))
        try:
            respuesta, cfg = completar(sistema, f"Apartados que debes redactar:\n{pedidos}\n\nContexto:\n{contexto_informe}", cfg)
        except Exception as e:  # noqa: BLE001  (sin modelo, los apartados quedan con su marcador)
            log.warning("Sin borradores de la IA para %d apartados: %s", len(lote), e)
            continue
        textos = _bloques(respuesta, len(lote))
        for n, instruccion in enumerate(lote, 1):
            motivo = verificar_borrador(textos.get(n, ""), contexto_informe, _es_frase(instruccion))
            if motivo:
                log.info("Borrador descartado («%s»): %s", instruccion[:60], motivo)
                continue
            borradores[instruccion] = " ".join(textos[n].split())
    return borradores
