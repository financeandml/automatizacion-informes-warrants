"""Acceso al modelo de lenguaje.

Configuración adaptada de `LLMSettings` de financial-research-analyst-agent (src/config.py,
MIT, Copyright (c) 2024 Gopal Saini): proveedor elegible por .env, temperatura 0,1, 4096 tokens.
Todos los proveedores se usan por su API compatible con OpenAI, así que hay un solo camino de código.

Sin LLM_PROVIDER se usa el primero disponible de PRIORIDAD (llama4 en OpenRouter, gpt-oss-120b en
Groq, Ollama local); si el elegido falla, se recurre a Ollama local. Ver docs/ia.md.
"""

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

PROVEEDORES = {
    # proveedor: (URL base compatible con OpenAI, modelo por defecto, variable de la API key)
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
PRIORIDAD = ("openrouter", "groq", RESPALDO)  # sin LLM_PROVIDER, el primero con API key


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


def _llamar(cfg: LLMSettings, sistema: str, usuario: str) -> str:
    from openai import OpenAI

    cliente = OpenAI(base_url=cfg.url_base, api_key=cfg.api_key, timeout=600)
    respuesta = cliente.chat.completions.create(
        model=cfg.modelo, temperature=cfg.temperatura, max_tokens=cfg.max_tokens,
        messages=[{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
    )
    return (respuesta.choices[0].message.content or "").strip()


def completar(sistema: str, usuario: str, cfg: LLMSettings | None = None) -> tuple[str, LLMSettings]:
    """Respuesta del modelo y la configuración que la produjo (para registrarla en la versión)."""
    cfg = cfg or LLMSettings.desde_entorno()
    try:
        return _llamar(cfg, sistema, usuario), cfg
    except Exception as error:
        if cfg.proveedor == RESPALDO:
            raise LLMError(f"Ollama no responde en {cfg.url_base}: ¿está instalado y arrancado? ({error})") from error
        log.warning("Falló %s · %s (%s); se usa el respaldo local %s.", cfg.proveedor, cfg.modelo, error, RESPALDO)
        respaldo = LLMSettings.desde_entorno(RESPALDO)
        try:
            return _llamar(respaldo, sistema, usuario), respaldo
        except Exception as error2:
            raise LLMError(f"Falló {cfg.proveedor} ({error}) y el respaldo local ({error2}).") from error2
