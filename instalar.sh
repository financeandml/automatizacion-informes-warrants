#!/usr/bin/env sh
# Instalación en macOS y Linux (C3): ejecútalo en la carpeta del repositorio descargado de GitHub.
#   sh instalar.sh
# El PDF necesita Pango: macOS «brew install pango»; Debian/Ubuntu «sudo apt install libpango-1.0-0 libpangoft2-1.0-0».
set -e
cd "$(dirname "$0")"
ENTORNO="${1:-$HOME/.local/share/informes-warrants/venv}"
command -v python3 >/dev/null || { echo "Instala Python 3.11 o superior (https://www.python.org/downloads/)"; exit 1; }
[ -x "$ENTORNO/bin/python" ] || { echo "1/3 Creando el entorno en $ENTORNO"; python3 -m venv "$ENTORNO"; }
echo "2/3 Instalando dependencias"
"$ENTORNO/bin/python" -m pip install --upgrade pip --quiet
"$ENTORNO/bin/python" -m pip install -e ".[pdf,ui,dev]" --quiet
[ -f .env ] || cp .env.example .env
printf '#!/usr/bin/env sh\n"%s/bin/python" -m informes_warrants.cli interfaz\n' "$ENTORNO" > abrir.sh && chmod +x abrir.sh
echo "3/3 Diagnóstico"
"$ENTORNO/bin/python" -m informes_warrants.cli diagnostico
echo "Listo. Para abrir la interfaz: sh abrir.sh"
