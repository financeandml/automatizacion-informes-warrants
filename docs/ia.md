# Modelo de lenguaje (capa 4)

## Decisión

| Prioridad | Proveedor | Modelo | Estado |
|---|---|---|---|
| 1 | OpenRouter | `meta-llama/llama-4-scout` (**llama4**) | Se activa con `OPENROUTER_API_KEY`. De pago: 0,10 USD por millón de tokens de entrada y 0,30 USD de salida; con el uso mínimo de IA, menos de un céntimo por informe |
| 2 | Groq (plan gratuito) | `openai/gpt-oss-120b` | ✅ **Activo** (con `GROQ_API_KEY`): modelo abierto de 120.000 millones de parámetros; riesgos de AAPL en unos 7 s |
| 3 (respaldo) | Ollama local | `llama3.2:3b` (2 GB) | ✅ Instalado; sin conexión, unos 40-50 s por bloque. Se usa si el proveedor elegido falla, y lo registra con un aviso |
| — | OpenAI, Anthropic, LM Studio, vLLM | Configurables | Mismo código (API compatible con OpenAI) |

**Dónde se puede usar llama4 (comprobado el 2026-10-11):**
- **Groq** retiró Llama 4 de su catálogo: solo quedan los modelos `llama-prompt-guard`.
- **Ollama** no lo ofrece en su nube; en local ocupa 67 GB (`llama4:scout`) y este portátil tiene 16 GB de RAM.
- **OpenRouter** sí lo ofrece (Scout y Maverick). Es la vía para usar llama4 sin un servidor propio.

La IA tiene un papel mínimo: elige entre fragmentos literales numerados y resume cada uno en una línea ([editor-y-versiones.md](editor-y-versiones.md)). Código: [ia/llm.py](../src/informes_warrants/ia/llm.py), con la configuración adaptada de `LLMSettings` de financial-research-analyst-agent (MIT).

## Plan por fases

| Fase | Qué | Estado |
|---|---|---|
| 1 | Interfaz única para todos los proveedores (`openai` con URL base), `LLMSettings` desde `.env`, respaldo automático a Ollama | ✅ Hecho |
| 2 | Instalar Ollama y `llama3.2:3b`; probar de principio a fin (`informes-warrants riesgos AAPL`: 27 riesgos → 5 resumidos con cita literal) | ✅ Hecho |
| 3 | IA mínima: selección por número + cita verificada en el texto del 10-K; 3 bloques del informe (riesgos, catalizadores y, desde el 2026-10-13, la traducción verificada del apartado «Competition»: mismas cifras, nombres propios y longitud; si no pasa, original para el analista) | ✅ Hecho |
| 4 | Groq con `GROQ_API_KEY`: llama4 ya no está disponible, así que se usa `openai/gpt-oss-120b`. `informes-warrants ia` → `groq · openai/gpt-oss-120b: listo` | ✅ Hecho |
| 4b | **llama4 en OpenRouter**: crear una key en <https://openrouter.ai/keys>, añadir saldo (con 5 USD basta para miles de informes) y poner `OPENROUTER_API_KEY=...` en `.env`; pasa a ser el proveedor por defecto automáticamente | ⏳ Opcional, a decisión del usuario |
| 5 | En el despliegue del SaaS, llama4 en servidor propio con GPU mediante vLLM (`LLM_PROVIDER=vllm`; ya soportado) si se quiere prescindir de Groq | Fase 8 del plan |

## Configuración (`.env`)

```bash
OPENROUTER_API_KEY=sk-or-... # llama4 (prioridad 1)
GROQ_API_KEY=gsk_...         # gpt-oss-120b gratis (prioridad 2); sin ninguna, Ollama local
# LLM_PROVIDER=ollama        # forzar un proveedor: openrouter | groq | ollama | openai | anthropic | lmstudio | vllm
# LLM_MODEL=llama3.2:3b     # cambiar el modelo del proveedor forzado
# LLM_TEMPERATURE=0.1
```

## Instalación del respaldo local

```powershell
winget install Ollama.Ollama
ollama pull llama3.2:3b
informes-warrants ia        # → ollama · llama3.2:3b: listo
```

`ollama launch claude` (lo sugiere Ollama al iniciar sesión) abre Claude Code usando modelos de Ollama. Es una herramienta de programación y no la usa el SaaS.
