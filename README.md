# Automatización de informes de warrants

SaaS para automatizar la generación de informes de inversión (estilo *equity research*) sobre empresas cotizadas en EEUU, a partir de los datos públicos de la SEC (EDGAR) mediante [edgartools](https://github.com/dgunning/edgartools).

> En desarrollo. Ejemplo de salida: [docs/ejemplos/AAPL_FY2025_borrador.pdf](docs/ejemplos/AAPL_FY2025_borrador.pdf). Reglas y mapa del proyecto: [CLAUDE.md](CLAUDE.md). Índice de la documentación: [docs/README.md](docs/README.md).

## Cómo funciona

```
ticker → ingesta/  (SEC: 10-K, 10-Q, proxy; mercado: cotización, bono a 10 años)
       → calculo/  (normalizador SEC único → métricas, LTM, DCF por escenarios, proyección hasta el BPA, puntuaciones)
       → informe/  (bloques: automáticos, plantillas con datos, 2 de IA y los del analista [[ANALISTA: …]])
       → visual/   (gráficos SVG y PDF con la plantilla de la marca)
       → borrador PDF + vista previa HTML → el analista completa y confirma → almacenamiento/ (versión)
```

Tres reglas lo explican casi todo:
- **Las cifras salen siempre de código** (`calculo/`), con la fuente de cada dato en el anexo del informe.
- **La IA solo elige y resume frases literales** del 10-K.
- **Lo que el código no puede saber, lo marca para el analista**, y esas marcas bloquean la emisión.

## Estructura

```
src/informes_warrants/   código (cada carpeta explica sus módulos en su __init__.py)
  cli.py                 comandos: informes-warrants -h
  ingesta/ calculo/ informe/ visual/ ia/ almacenamiento/   (ver «Cómo funciona»)
  plantillas/            plantilla HTML/CSS del PDF, textos de cada bloque, marca, fuentes y texto legal
tests/                   pytest: sin conexión (CI) y contra la SEC real (marcados «red»)
docs/                    documentación (empieza por docs/README.md)
repositorios-github/     copias locales de los repos base (zips; no se publican)
```

## Puesta en marcha

Requisitos: Python 3.11-3.13 (recomendado 3.13).

```bash
# 1. Entorno virtual. Si el proyecto está en OneDrive, crea el entorno fuera
#    (p. ej. %LOCALAPPDATA%\informes-warrants\venv): la sincronización lo ralentiza.
python -m venv .venv
.venv\Scripts\activate          # Windows (en macOS/Linux: source .venv/bin/activate)

# 2. Dependencias (pdf = WeasyPrint)
pip install -e ".[dev,pdf,ui]"   # ui: interfaz del analista (Streamlit)

# 3. Configuración
copy .env.example .env          # rellena EDGAR_IDENTITY y la key del modelo (docs/ia.md)
```

### WeasyPrint en Windows (PDF)

WeasyPrint necesita las bibliotecas GTK/Pango, que se instalan con MSYS2:

```powershell
winget install MSYS2.MSYS2
C:\msys64\usr\bin\bash.exe -lc "pacman -S --noconfirm mingw-w64-x86_64-pango"
```

El proyecto las encuentra solo en `C:\msys64\mingw64\bin`. Si las instalas en otra ruta, defínela en la variable `WEASYPRINT_DLL_DIRECTORIES`.

### Modelo de lenguaje

Por orden: llama4 en OpenRouter (`OPENROUTER_API_KEY`), `gpt-oss-120b` en Groq (`GROQ_API_KEY`, gratis) y Ollama en local. Detalle en [docs/ia.md](docs/ia.md).

```powershell
winget install Ollama.Ollama
ollama pull llama3.2:3b
```

## Uso

Flujo del analista con la interfaz (`informes-warrants interfaz`, en el navegador):
1. **Empresas y versiones:** escribe el ticker, detecta el 10-Q/10-K nuevo y confirma la versión.
2. **Editor del informe:** carga los datos de la SEC una vez; edita textos (Markdown), estimaciones, escenarios,
   calendario y catalizadores con la vista previa al lado; atiende los avisos y pulsa «Confirmar emisión del
   informe» para emitir y descargar el PDF.
3. **Configuración:** tu autoría (se guarda en tu carpeta de datos, no en el repositorio).

Flujo equivalente por línea de comandos:
1. Genera el borrador: `informes-warrants informe AAPL`.
2. Revisa los recuadros «PENDIENTE DEL ANALISTA» y el aviso «REVISAR».
3. **Introduce tu lista de comparables:** sin ella, la valoración por múltiplos no entra en el precio objetivo, que queda solo por DCF (el SaaS lo avisa antes de emitir, sin bloquear):
   `informes-warrants informe AAPL --comparables MSFT,GOOGL,DELL`.

```bash
informes-warrants informe AAPL               # borrador del informe en PDF + vista previa HTML
informes-warrants informe AAPL --comparables MSFT,GOOGL,DELL   # con la lista de comparables del analista
informes-warrants informe AAPL --comparar-con ruta/AAPL_FY2025_borrador_resumen.json  # qué cambió y por qué
informes-warrants autoria --analista "Nombre" --correo nombre@empresa.com   # autoría de la portada (fuera del repo)
informes-warrants regresion                  # batería de regresión: cifras de la SEC de las 14 empresas de prueba
informes-warrants datos AAPL                 # estados financieros del último 10-K
informes-warrants cobertura JPM              # plantilla: general, sectorial o «pendiente de validar»
informes-warrants metricas JPM               # métricas del perfil sectorial con su fuente XBRL
informes-warrants informe JPM                # informe con la plantilla sectorial (banca, seguros, REIT o BDC)
informes-warrants riesgos AAPL               # riesgos del 10-K y los 5 principales (IA)
informes-warrants riesgos AAPL --sin-ia      # solo la lista literal
informes-warrants interfaz                   # interfaz del analista (Streamlit, en local)
informes-warrants versiones detectar AAPL    # propone la versión del último 10-Q/10-K
informes-warrants versiones preparar AAPL    # construye el informe de la versión abierta y guarda su PDF
informes-warrants versiones confirmar AAPL   # confirma la versión detectada
informes-warrants versiones emitir AAPL      # emite (bloquean los apartados pendientes y la calidad en rojo)
informes-warrants versiones lista AAPL       # historial de versiones
informes-warrants ia                         # comprueba el modelo de lenguaje
```

Los datos (base de datos de versiones, snapshots y PDFs) se guardan fuera del proyecto, en la carpeta de datos del usuario (`%LOCALAPPDATA%\informes-warrants\` en Windows), o en `INFORMES_DATA_DIR`.

## Tests

```bash
pytest -m "not red"     # sin conexión (lo que ejecuta la CI en Ubuntu y Windows)
pytest                  # incluye pruebas contra la SEC real
ruff check src tests
```

## Licencia

[MIT](LICENSE)
