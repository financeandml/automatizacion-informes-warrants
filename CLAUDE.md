# Guía del proyecto (personas y agentes de IA)

SaaS que genera informes de análisis (estilo *equity research*) sobre empresas cotizadas en EEUU a partir de datos oficiales de la SEC. El analista los revisa, completa la tesis y los versiona cada trimestre.

**Objetivos.** Medio: que cualquier persona nueva entienda, use y modifique el proyecto sin ayuda. Final: el SaaS de automatización de informes.

## Reglas obligatorias

1. **Reutilizar antes que construir.** Antes de cualquier tarea, consulta [docs/inventario/README.md](docs/inventario/README.md) (análisis del 100 % de los repos base) y deja escrito qué se reutiliza y por qué. Si cambia un zip de `repositorios-github/`, actualiza su ficha.
2. **No saltar pasos ni dejar nada a medias:** cada tarea termina con código, tests, docs y commit, o con una nota explícita de lo que queda.
3. **No borrar nada** que pueda perjudicar el objetivo final; ante la duda, preguntar.
4. **Ahorro de tokens:** leer solo lo necesario (inventario y docs primero), sin repetir información entre documentos.
5. **Repo publicable en todo momento:** sin secretos (`.env` ignorado), sin código de terceros versionado (`repositorios-github/` ignorado), docs al día.
6. **Licencias:** MIT/Apache se puede copiar con atribución; sec-edgar-toolkit (AGPL-3.0), automated-market-report y financial-ai-agent (sin licencia) solo como referencia.
7. **Determinismo:** las cifras salen de código (capas 1-3); la IA (capa 4) solo redacta texto con cita literal del 10-K y siempre lo revisa un humano.

## Navegación

| Necesito… | Archivo |
|---|---|
| Plan, capas, fases y decisiones | [docs/plan.md](docs/plan.md) |
| Contenido del informe (índice) | [docs/estructura-informe.md](docs/estructura-informe.md) |
| Qué reutilizar y dónde (rutas exactas) | [docs/inventario/README.md](docs/inventario/README.md) |
| Resumen de los repos base y licencias | [docs/repositorios-base.md](docs/repositorios-base.md) |
| Identidad corporativa (colores, tipografía, logo) | [docs/identidad-corporativa.md](docs/identidad-corporativa.md) |
| Decisiones pendientes del usuario | [docs/requisitos-pendientes.md](docs/requisitos-pendientes.md) |
| Configuración de EDGAR | [src/informes_warrants/config.py](src/informes_warrants/config.py), [.env.example](.env.example) |
| Texto legal del informe | [src/informes_warrants/plantillas/legal/descargo.md](src/informes_warrants/plantillas/legal/descargo.md) |

## Flujo de datos

```
ticker → ingesta/ (SEC + precio, snapshot) → calculo/ (métricas) → visual/ + plantillas/ (gráficos, tablas, HTML → PDF)
       → ia/ (riesgos y MD&A con citas) → ui/ (Streamlit: editor híbrido) → almacenamiento/ (versiones)
```

## Marca

Solo tres colores: burdeos `#2B0B02`, negro `#000000` y blanco `#FFFFFF`. Tipografía: Montserrat (títulos) + Inter (texto). Estilo sobrio e institucional, inspirado en Morningstar (sin sus marcas).

## Comandos

```bash
pip install -e ".[dev]"   # instalar (Python 3.13 recomendado)
pytest                    # tests
```

## Definition of Done

- El razonamiento de reutilización (regla 1) está escrito en el commit o en la doc.
- Hay test que valida la cifra o el comportamiento real (valores *golden* de AAPL para cálculos).
- Docs y [docs/plan.md](docs/plan.md) actualizados si cambia una decisión.
- Commit en español con descripción clara.
