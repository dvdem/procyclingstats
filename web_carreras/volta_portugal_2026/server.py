import os
import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

PORT = int(os.environ.get("PORT", "8080"))
ROOT = Path(__file__).resolve().parent
RACECENTER_URL = "https://racecenter.lavuelta.es/api/rankingType-2026-{stage}"


class StaticHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        match = re.fullmatch(r"/api/ganador/(\d+)", urlsplit(self.path).path)
        if match:
            self.send_winner_time(int(match.group(1)))
            return
        super().do_GET()

    def send_winner_time(self, stage_number):
        url = RACECENTER_URL.format(stage=stage_number)
        try:
            request = Request(url, headers={"User-Agent": "volta-portugal-local/1.0"})
            with urlopen(request, timeout=15) as response:
                data = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            self.send_json(502, {"ok": False, "error": f"No se pudo consultar Race Center: {error}"})
            return

        rankings_list = data if isinstance(data, list) else data.get("rankings", [])
        winner_candidate = None

        for section in rankings_list:
            if not isinstance(section, dict):
                continue
            entries = section.get("rankings") or []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("position")) != "1":
                    continue
                absolute = entry.get("absolute")
                try:
                    absolute = float(absolute) if absolute is not None else None
                except (TypeError, ValueError):
                    absolute = None
                if not isinstance(absolute, (int, float)) or absolute <= 1000:
                    continue

                # Race Center exposes several rankings for each stage (time, general, intermediate,
                # mountain, points, etc.). The real stage winner is the smallest positive elapsed
                # time among the first-place entries; the auxiliary rankings are usually much
                # larger or near zero and are not the actual stage result.
                if winner_candidate is None or absolute < winner_candidate:
                    winner_candidate = float(absolute)

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
        # Permite que fueracontrol.html alojado en GCS (otro origen) consulte esta API
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), StaticHandler)
    print(f"Servidor escuchando en el puerto {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
