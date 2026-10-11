# Modelo de lenguaje (capa 4)

## Decisión

| Uso | Proveedor | Modelo | Por qué |
|---|---|---|---|
| **Principal** | Groq (API, plan gratuito) | `meta-llama/llama-4-scout-17b-16e-instruct` (**llama4**) | Es el modelo por defecto del repo base y la única forma de usar llama4 en un portátil. Responde en 1-2 s |
| **Respaldo automático y sin conexión** | Ollama local | `llama3.2:3b` (2 GB) | Funciona en un portátil de 16 GB sin GPU (unos 50 s por bloque). Se usa si no hay `GROQ_API_KEY` o si Groq falla |
| Alternativas | OpenAI, Anthropic, LM Studio, vLLM | Configurables | Mismo código: todas se usan por su API compatible con OpenAI |

- **Por qué llama4 no corre en local:** su versión más pequeña (Scout, 109.000 millones de parámetros en total) ocupa unos 67 GB incluso cuantizada a 4 bits. Este portátil tiene 16 GB de RAM y una gráfica integrada (Intel Iris Xe).
- La IA tiene un papel mínimo: elige entre fragmentos literales numerados y resume cada uno en una línea ([editor-y-versiones.md](editor-y-versiones.md)). Por eso basta un modelo pequeño y el uso del plan gratuito de Groq es muy bajo.
- Código: [ia/llm.py](../src/informes_warrants/ia/llm.py). La configuración está adaptada de `LLMSettings` de financial-research-analyst-agent (MIT).

## Plan por fases

| Fase | Qué | Estado |
|---|---|---|
| 1 | Interfaz única para todos los proveedores (`openai` con URL base), `LLMSettings` desde `.env`, respaldo automático a Ollama | ✅ Hecho |
| 2 | Instalar Ollama y `llama3.2:3b`; probar de principio a fin (`informes-warrants riesgos AAPL`: 27 riesgos → 5 resumidos con cita literal) | ✅ Hecho |
| 3 | IA mínima: selección por número + cita verificada en el texto del 10-K; solo 2 bloques del informe | ✅ Hecho |
| 4 | **Activar llama4 en Groq**: crear una API key gratuita en <https://console.groq.com/keys>, añadir `GROQ_API_KEY=...` al `.env` y comprobarlo con `informes-warrants ia`, que debe responder `groq · meta-llama/llama-4-scout-17b-16e-instruct` | ⏳ Necesita la key del usuario (2 minutos) |
| 5 | En el despliegue del SaaS, llama4 en servidor propio con GPU mediante vLLM (`LLM_PROVIDER=vllm`; ya soportado) si se quiere prescindir de Groq | Fase 8 del plan |

## Configuración (`.env`)

```bash
GROQ_API_KEY=gsk_...        # activa llama4 en Groq (si falta, se usa Ollama)
# LLM_PROVIDER=ollama       # forzar un proveedor: groq | ollama | openai | anthropic | lmstudio | vllm
# LLM_MODEL=llama3.2:3b     # cambiar el modelo del proveedor forzado
# LLM_TEMPERATURE=0.1
```

## Instalación del respaldo local

```powershell
winget install Ollama.Ollama
ollama pull llama3.2:3b
informes-warrants ia        # → ollama · llama3.2:3b: listo
```
