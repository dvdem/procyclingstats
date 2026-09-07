import os
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

PORT = int(os.environ.get("PORT", "8080"))
ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "fueracontrol.html"
RACECENTER_URL = "https://racecenter.lavuelta.es/api/rankingType-2026-{stage}"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        match = re.fullmatch(r"/api/ganador/(\d+)", path)
        if match:
            self.send_winner_time(int(match.group(1)))
            return
        if path in ("/", "/fueracontrolvuelta26", "/fueracontrol.html"):
            self.send_html()
            return
        self.send_error(404, "Not found")

    def send_html(self):
        body = HTML_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def send_winner_time(self, stage_number):
        url = RACECENTER_URL.format(stage=stage_number)
        try:
            request = Request(url, headers={"User-Agent": "fueracontrol-service/1.0"})
            with urlopen(request, timeout=15) as response:
                data = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            self.send_json(502, {"ok": False, "error": f"No se pudo consultar Race Center: {error}"})
            return

        rankings_list = data if isinstance(data, list) else data.get("rankings", [])

        def first_place_time(predicate):
            """Devuelve el tiempo (ms) del 1er clasificado del primer bloque que cumpla predicate."""
            for section in rankings_list:
                if not isinstance(section, dict) or not predicate(section):
                    continue
                for entry in section.get("rankings") or []:
                    if not isinstance(entry, dict) or str(entry.get("position")) != "1":
                        continue
                    absolute = entry.get("absolute")
                    try:
                        absolute = float(absolute) if absolute is not None else None
                    except (TypeError, ValueError):
                        absolute = None
                    if isinstance(absolute, (int, float)) and absolute > 1000:
                        return absolute
            return None

        # "ite" = clasificación individual de ETAPA (tiempo de llegada); es la fuente correcta
        # para cualquier tipo de etapa, incluidas las CRI. Los bloques "itt" contienen además
        # los pasos por puntos de control intermedios (types:"C") cuyo tiempo es menor y NO es
        # el de meta, por lo que no deben usarse como primera opción.
        winner_candidate = first_place_time(lambda s: s.get("type") == "ite")
        if winner_candidate is None:
            # Fallback: bloque "itt" de meta (types contiene N o A), evitando el checkpoint "C"
            winner_candidate = first_place_time(
                lambda s: s.get("type") == "itt" and any(t in (s.get("types") or []) for t in ("N", "A"))
            )
        if winner_candidate is None:
            # Último recurso: cualquier bloque con datos de tiempo válidos
            winner_candidate = first_place_time(lambda s: True)

        if winner_candidate is None:
            self.send_json(404, {"ok": False, "error": "No hay tiempo oficial del ganador para esta etapa."})
            return

        self.send_json(200, {
            "ok": True,
            "stage": stage_number,
            "winnerTimeSeconds": winner_candidate / 1000,
            "source": url,
        })

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # Permite consultar esta API desde otros orígenes (p.ej. la copia estática en GCS)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Servidor fueracontrol escuchando en el puerto {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
