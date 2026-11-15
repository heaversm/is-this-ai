"""Drag-and-drop image checker: a small local web server.

Drop an image on the page and it runs the same checks as the test:
labels in the file, the four free detectors, and (only if you click the button)
Google's watermark through Gemini. Images are checked on this Mac and never leave
it, except for the Gemini button, which sends that one image to Google.

    cd image-test
    .venv/bin/python checker/server.py
    then open http://localhost:8765
"""

import json
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from check_metadata import check as check_metadata  # noqa: E402
import detectors  # noqa: E402

PORT = 8765
UPLOADS = Path(tempfile.gettempdir()) / "provenance-checker-uploads"
UPLOADS.mkdir(exist_ok=True)
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".heic", ".avif"}
LIKELY = 0.95  # the cutoff used in the test
BEST = "haywoodsloan_swinv2"


def verdict(meta, det, gemini=None):
    if meta["meta_verdict"] == "ai" or gemini == "found":
        return "confirmed_ai"
    if meta["meta_verdict"] == "real":
        return "confirmed_real"
    if det.get(BEST, 0) >= LIKELY:
        return "likely_ai"
    return "dont_know"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if self.path == "/check":
            name = Path(unquote(self.headers.get("X-Filename", "image.jpg"))).name  # sent URL-encoded: names can have non-ASCII characters
            ext = Path(name).suffix.lower()
            if ext not in EXTS:
                return self.send(400, {"error": f"Not an image type we can read ({ext or 'no extension'})."})
            path = UPLOADS / f"{int(time.time() * 1000)}{ext}"
            path.write_bytes(self.rfile.read(n))
            try:
                meta = check_metadata(path)
                det = detectors.run_all(path)
            except Exception as e:
                return self.send(500, {"error": f"Couldn't read this image: {type(e).__name__}: {e}"})
            return self.send(200, {"id": path.name, "filename": name, "meta": meta, "detectors": det,
                                   "verdict": verdict(meta, det)})
        if self.path == "/gemini":
            body = json.loads(self.rfile.read(n) or b"{}")
            path = UPLOADS / Path(body.get("id", "")).name
            if not path.exists():
                return self.send(400, {"error": "Image not found; drop it again."})
            cache = UPLOADS / f"{path.stem}.gemini.json"
            proc = subprocess.run([sys.executable, str(ROOT / "gemini_check.py"), "--cache", str(cache), "--pause", "0", str(path)],
                                  capture_output=True, text=True, timeout=300, cwd=ROOT)
            if not cache.exists():
                msg = (proc.stdout + proc.stderr).strip().splitlines()
                return self.send(500, {"error": msg[-1] if msg else "The Gemini check didn't run."})
            res = json.loads(cache.read_text()).get(str(path), {})
            return self.send(200, {"synthid": res.get("synthid"), "reply": res.get("reply", "")})
        self.send(404, {"error": "not found"})


def main():
    print("Loading the detectors (first time takes a moment)...")
    detectors.run_all(ROOT / "fixtures" / "C.jpg")  # warm up all four models
    print(f"Ready: open http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
