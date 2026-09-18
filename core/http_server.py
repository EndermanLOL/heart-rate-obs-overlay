"""
http_server.py

Servidor HTTP local (sin dependencias externas) que sirve:
    GET /            -> overlay HTML para OBS Browser Source
    GET /bpm         -> JSON con el estado actual {bpm, connected, live, device}

Se crea con create_server(...) y se corre en un hilo aparte con
server.serve_forever(); para detenerlo, llama a server.shutdown() desde
otro hilo (por ejemplo desde la GUI).
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .overlay_html import OVERLAY_HTML


class OverlayRequestHandler(BaseHTTPRequestHandler):
    # El SharedState se inyecta como atributo de clase antes de arrancar el server
    state = None

    def log_message(self, format, *args):
        # Silenciamos el log por defecto de http.server para no ensuciar la consola
        pass

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_html(OVERLAY_HTML)
        elif path == "/bpm":
            self._send_json(self.state.snapshot())
        else:
            self._send_json({"error": "not found"}, status=404)


def create_server(host: str, port: int, state) -> ThreadingHTTPServer:
    """Crea (sin arrancar) el servidor HTTP ligado a un SharedState dado."""
    handler_cls = type("BoundOverlayHandler", (OverlayRequestHandler,), {"state": state})
    server = ThreadingHTTPServer((host, port), handler_cls)
    return server
