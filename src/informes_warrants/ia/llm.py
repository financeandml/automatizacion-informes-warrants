"""Acceso al modelo de lenguaje.

Configuración adaptada de `LLMSettings` de financial-research-analyst-agent (src/config.py,
MIT, Copyright (c) 2024 Gopal Saini): proveedor elegible por .env, temperatura 0,1, 4096 tokens.
Todos los proveedores se usan por su API compatible con OpenAI, así que hay un solo camino de código.

Sin LLM_PROVIDER se usa el primero disponible de PRIORIDAD (Gemini, llama4 en OpenRouter, gpt-oss-120b en
Groq, Ollama local); si el elegido falla, se recurre a Ollama local. Ver docs/ia.md.
"""

import logging
import os
import time
from dataclasses import dataclass, replace

from dotenv import load_dotenv

from ..observabilidad import medido

PROVEEDORES = {
    # proveedor: (URL base compatible con OpenAI, modelo por defecto, variable de la API key)
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-3.8-flash", "GEMINI_API_KEY"),  # 2026-10-15
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-4-scout", "OPENROUTER_API_KEY"),  # llama4
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b", "GROQ_API_KEY"),  # Groq retiró llama4
    "ollama": ("http://localhost:11434/v1", "llama3.2:3b", None),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini", "OPENAI_API_KEY"),
    "anthropic": ("https://api.anthropic.com/v1/", "claude-haiku-5-5", "ANTHROPIC_API_KEY"),
    "lmstudio": ("http://localhost:1234/v1", "local-model", None),
    "vllm": ("http://localhost:8000/v1", "meta-llama/Llama-4-Scout-17B-16E-Instruct", None),
}
RESPALDO = "ollama"
log = logging.getLogger(__name__)
PRIORIDAD = ("gemini", "openrouter", "groq", RESPALDO)  # sin LLM_PROVIDER, el primero con API key (Gemini: usuario, 2026-10-15)
# Con el cupo agotado (429/413), los otros modelos del mismo proveedor tienen su propio cupo diario (Groq gratuito:
# 200.000 tokens al día por modelo, unos 3-4 informes): se prueban antes de bajar a Ollama local, que es lento.
MODELOS_ALTERNATIVOS = {"groq": ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b")}
AGOTADO_DURANTE = 3600  # segundos que se salta un modelo sin cupo
_agotados: dict[str, float] = {}  # modelo: hasta cuándo se salta


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMSettings:
    proveedor: str
    modelo: str
    url_base: str
    api_key: str
    temperatura: float = 0.1
    max_tokens: int = 4096

    @classmethod
    def desde_entorno(cls, proveedor: str | None = None) -> "LLMSettings":
        load_dotenv()
        proveedor = (proveedor or os.getenv("LLM_PROVIDER") or next(
            p for p in PRIORIDAD if p == RESPALDO or os.getenv(PROVEEDORES[p][2] or ""))).lower()
        if proveedor not in PROVEEDORES:
            raise LLMError(f"Proveedor desconocido: {proveedor}. Opciones: {', '.join(PROVEEDORES)}")
        url, modelo, var_key = PROVEEDORES[proveedor]
        propio = proveedor == (os.getenv("LLM_PROVIDER") or "").lower()  # LLM_MODEL/LLM_BASE_URL solo para el elegido
        return cls(
            proveedor=proveedor,
            modelo=(os.getenv("LLM_MODEL") if propio else None) or modelo,
            url_base=(os.getenv("LLM_BASE_URL") if propio else None) or url,
            api_key=(os.getenv(var_key) if var_key else None) or "no-necesaria",
            temperatura=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        )


def _llamar(cfg: LLMSettings, sistema: str, usuario: str, reintentos: int = 2) -> str:
    from openai import OpenAI

    cliente = OpenAI(base_url=cfg.url_base, api_key=cfg.api_key, timeout=600, max_retries=reintentos)
    # gpt-oss razona antes de responder y ese razonamiento gasta el cupo de tokens por minuto (Groq gratuito: 8.000).
    # Para elegir, resumir o traducir basta «low»: medido, 5 veces menos tokens de salida y 3 veces más rápido.
    extra = {"extra_body": {"reasoning_effort": os.getenv("LLM_REASONING", "low")}} if "gpt-oss" in cfg.modelo else {}
    respuesta = cliente.chat.completions.create(
        model=cfg.modelo, temperature=cfg.temperatura, max_tokens=cfg.max_tokens,
        messages=[{"role": "system", "content": sistema}, {"role": "user", "content": usuario}], **extra,
    )
    return (respuesta.choices[0].message.content or "").strip()


def _sin_cupo(error: Exception) -> bool:
    return getattr(error, "status_code", None) in (413, 429)


def _candidatos(cfg: LLMSettings) -> list[LLMSettings]:
    """El modelo elegido y, detrás, los demás del mismo proveedor; sin los que agotaron su cupo hace poco."""
    ahora = time.time()
    modelos = [cfg.modelo] + [m for m in MODELOS_ALTERNATIVOS.get(cfg.proveedor, ()) if m != cfg.modelo]
    vivos = [m for m in modelos if _agotados.get(m, 0) < ahora] or modelos[:1]
    return [replace(cfg, modelo=m) for m in vivos]


@medido("ia")
def completar(sistema: str, usuario: str, cfg: LLMSettings | None = None) -> tuple[str, LLMSettings]:
    """Respuesta del modelo y la configuración que la produjo (para registrarla en la versión)."""
    cfg = cfg or LLMSettings.desde_entorno()
    errores = []
    for intento in _candidatos(cfg):
        try:
            return _llamar(intento, sistema, usuario), intento
        except Exception as error:  # noqa: BLE001
            errores.append(f"{intento.proveedor} · {intento.modelo}: {error}")
            if intento.proveedor == RESPALDO:
                raise LLMError(f"Ollama no responde en {intento.url_base}: ¿está instalado y arrancado? ({error})") from error
            if not _sin_cupo(error):
                break
            _agotados[intento.modelo] = time.time() + AGOTADO_DURANTE
            log.warning("Sin cupo en %s · %s; se prueba el siguiente modelo.", intento.proveedor, intento.modelo)
    # C5: después, los demás proveedores con clave y, al final, el respaldo local; sin reintentos con espera
    siguientes = [x for x in PRIORIDAD if x not in (cfg.proveedor, RESPALDO) and os.getenv(PROVEEDORES[x][2] or "")] + [RESPALDO]
    for proveedor in siguientes:
        log.warning("Falló %s (%s); se usa %s.", cfg.proveedor, errores[-1][:200], proveedor)
        respaldo = LLMSettings.desde_entorno(proveedor)
        try:
            return _llamar(respaldo, sistema, usuario, reintentos=0), respaldo
        except Exception as error2:  # noqa: BLE001
            errores.append(f"{proveedor}: {error2}")
    raise LLMError("Fallaron todos los proveedores: " + "; ".join(e[:200] for e in errores))
