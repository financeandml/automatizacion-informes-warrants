"""Vista previa del informe servida en local (C5: navegación fluida).

Antes, la vista previa iba incrustada en la página (HTML con las fuentes en base64: 2,4 MB) y Streamlit la reenviaba
al navegador en cada clic y la volvía a dibujar en cada cambio de pantalla. Ahora el HTML (~0,2 MB) se escribe en la
carpeta de datos y lo sirve este servidor mínimo, con la hoja de estilos, las fuentes y los logos como archivos aparte
que el navegador guarda en caché; Streamlit solo envía la dirección. Solo escucha en 127.0.0.1 y solo sirve esos
archivos (cualquier otra ruta: 404). Biblioteca estándar (`http.server`).
"""

import hashlib
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..config import directorio_datos
from ..informe.render import DIR, DIR_INFORME

MAX_VISTAS = 20  # vistas que se conservan en disco (las más recientes)


def carpeta() -> Path:
    destino = directorio_datos() / "vista"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


class _Manejador(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        partes = path.split("?", 1)[0].split("#", 1)[0].lstrip("/").split("/")
        if len(partes) == 2 and partes[1] and not any(x in partes[1] for x in ("..", "\\", ":")):
            seccion, nombre = partes
            raiz = {"fuentes": DIR / "fuentes", "marca": DIR / "marca"}.get(seccion)
            if seccion == "informe":
                raiz = carpeta() if nombre.startswith("vista-") else DIR_INFORME if nombre == "estilo.css" else None
            if raiz is not None:
                return str(raiz / nombre)
        return str(carpeta() / "no-existe")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "max-age=86400")  # nombres con huella: lo que cambia, cambia de nombre
        super().end_headers()

    def log_message(self, *args) -> None:  # sin ruido en la consola
        pass


def arrancar() -> str:
    """Arranca el servidor en un puerto libre de 127.0.0.1 y devuelve su dirección base."""
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Manejador)
    threading.Thread(target=servidor.serve_forever, name="vista-previa", daemon=True).start()
    return f"http://127.0.0.1:{servidor.server_address[1]}"


def publicar(html: str, base: str) -> str:
    """Escribe la vista (nombre = huella del contenido) y devuelve su dirección; borra las más antiguas."""
    huella = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
    destino = carpeta()
    ruta = destino / f"vista-{huella}.html"
    if not ruta.exists():
        ruta.write_text(html, encoding="utf-8")
        for antigua in sorted(destino.glob("vista-*.html"), key=lambda p: p.stat().st_mtime)[:-MAX_VISTAS]:
            antigua.unlink(missing_ok=True)
    return f"{base}/informe/{ruta.name}"
