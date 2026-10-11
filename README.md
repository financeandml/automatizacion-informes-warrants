# Automatización de informes de warrants

SaaS para automatizar la generación de informes de inversión (estilo *equity research*) sobre empresas cotizadas en EEUU, a partir de los datos públicos de la SEC (EDGAR) mediante [edgartools](https://github.com/dgunning/edgartools).

> En desarrollo. Empieza por [CLAUDE.md](CLAUDE.md) (guía, reglas y mapa del proyecto). Ver [plan](docs/plan.md), [editor y versiones](docs/editor-y-versiones.md), [IA](docs/ia.md), [inventario de repos base](docs/inventario/README.md), [estructura del informe](docs/estructura-informe.md) y [requisitos pendientes](docs/requisitos-pendientes.md).

## Puesta en marcha

Requisitos: Python 3.11-3.13 (recomendado 3.13).

```bash
# 1. Entorno virtual. Si el proyecto está en OneDrive, crea el entorno fuera
#    (p. ej. %LOCALAPPDATA%\informes-warrants\venv): la sincronización lo ralentiza.
python -m venv .venv
.venv\Scripts\activate          # Windows (en macOS/Linux: source .venv/bin/activate)

# 2. Dependencias (pdf = WeasyPrint)
pip install -e ".[dev,pdf]"

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

```bash
informes-warrants datos AAPL                 # estados financieros del último 10-K
informes-warrants cobertura JPM              # plantilla: general, sectorial o «pendiente de validar»
informes-warrants metricas JPM               # métricas del perfil sectorial con su fuente XBRL
informes-warrants riesgos AAPL               # riesgos del 10-K y los 5 principales (IA)
informes-warrants riesgos AAPL --sin-ia      # solo la lista literal
informes-warrants versiones detectar AAPL    # propone la versión del último 10-Q/10-K
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
