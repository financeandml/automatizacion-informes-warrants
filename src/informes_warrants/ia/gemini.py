"""API de Gemini (Google AI Studio): llamada nativa con búsqueda de Google y citas, y caché por día.

Plan y reglas en docs/plan-pendientes.md §1. La clave va en `.env` (`GEMINI_API_KEY`); sin ella, todo lo que depende
de Gemini se omite y el informe sale igual (aviso). Para los textos normales Gemini es además un proveedor más de
`ia/llm.py` (API compatible con OpenAI); este módulo cubre lo que esa API no da: la búsqueda en Google con las fuentes
de cada frase (*grounding*), necesaria para el consenso de analistas (P22).

Regla de cero alucinaciones: la respuesta nunca se usa tal cual. Quien llama verifica por código cada cifra (en la
fuente citada o en el propio informe) y descarta lo que no cuadre.
"""

import hashlib
import json
import logging
import os
import re
import urllib.request
from datetime import date

log = logging.getLogger(__name__)
URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"  # clave en cabecera, no en la URL
MODELO = "gemini-3.8-flash"  # rápido y con búsqueda; se cambia con GEMINI_MODEL
TIEMPO_MAXIMO = 90  # segundos por llamada


class GeminiError(RuntimeError):
    pass


def clave() -> str | None:
    from dotenv import load_dotenv

    load_dotenv()
    return os.getenv("GEMINI_API_KEY") or None


def disponible() -> bool:
    return clave() is not None


def _cache(clave_cache: str):
    from ..config import directorio_datos

    carpeta = directorio_datos() / "ia_cache"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / f"{date.today().isoformat()}_{hashlib.sha1(clave_cache.encode()).hexdigest()[:20]}.json"


def generar(sistema: str, usuario: str, buscar: bool = False, json_salida: bool = True) -> dict:
    """{"texto", "datos" (JSON si se pidió), "fuentes": [{"url", "titulo"}], "apoyos": [{"texto", "fuentes"}], "modelo"}.

    `buscar`: activa la búsqueda de Google (las fuentes salen de groundingMetadata). Caché por día y contenido."""
    api = clave()
    if not api:
        raise GeminiError("Falta GEMINI_API_KEY en .env")
    modelo = os.getenv("GEMINI_MODEL") or MODELO
    ruta = _cache(f"{modelo}|{buscar}|{sistema}|{usuario}")
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    cuerpo = {"systemInstruction": {"parts": [{"text": sistema}]}, "contents": [{"role": "user", "parts": [{"text": usuario}]}],
              "generationConfig": {"temperature": 0.1}}
    if buscar:
        cuerpo["tools"] = [{"google_search": {}}]
    elif json_salida:
        cuerpo["generationConfig"]["responseMimeType"] = "application/json"
    peticion = urllib.request.Request(URL.format(modelo=modelo), data=json.dumps(cuerpo).encode(),
                                      headers={"Content-Type": "application/json", "x-goog-api-key": api})
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO) as r:
            respuesta = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        raise GeminiError(f"Gemini no responde: {e}") from e
    candidato = (respuesta.get("candidates") or [{}])[0]
    texto = "".join(p.get("text", "") for p in (candidato.get("content") or {}).get("parts", []))
    meta = candidato.get("groundingMetadata") or {}
    fuentes = [{"url": (c.get("web") or {}).get("uri", ""), "titulo": (c.get("web") or {}).get("title", "")}
               for c in meta.get("groundingChunks", [])]
    apoyos = [{"texto": (s.get("segment") or {}).get("text", ""), "fuentes": s.get("groundingChunkIndices", [])}
              for s in meta.get("groundingSupports", [])]
    salida = {"texto": texto, "datos": extraer_json(texto) if json_salida else None, "fuentes": fuentes, "apoyos": apoyos,
              "modelo": modelo}
    ruta.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    return salida


def extraer_json(texto: str):
    """El primer objeto o lista JSON del texto (con o sin bloque ```json)."""
    limpio = re.sub(r"^```(?:json)?|```$", "", (texto or "").strip(), flags=re.M).strip()
    for apertura, cierre in (("{", "}"), ("[", "]")):
        i, j = limpio.find(apertura), limpio.rfind(cierre)
        if i != -1 and j > i:
            try:
                return json.loads(limpio[i:j + 1])
            except ValueError:
                continue
    return None


def texto_de_pagina(url: str, limite: int = 2_000_000) -> str:
    """Texto visible de una página (para comprobar que una cifra citada aparece en su fuente)."""
    peticion = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Warrants & Co research)"})
    with urllib.request.urlopen(peticion, timeout=30) as r:
        html = r.read(limite).decode("utf-8", errors="replace")
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())
