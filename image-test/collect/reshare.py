"""Make "re-shared" copies of every original file, the way apps do to images
people pass around. Each original gets one copy, rotating through three methods:

  social      metadata removed, longest side 1080 px, JPEG quality 78 (roughly Instagram)
  chat        metadata removed, longest side 1600 px, JPEG quality 60 (roughly WhatsApp)
  screenshot  the image shown on a phone-sized screen in Chrome, captured as a PNG

These are simulations. Real trips through Instagram or WhatsApp may differ, so the
report keeps them apart from the fact-checked viral images (origin column).

    .venv/bin/python collect/reshare.py
"""

import csv
import io
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent.parent
IMAGES = HERE / "images"
SOURCES = HERE / "collect" / "sources_reshare.csv"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
METHODS = ["social", "chat", "screenshot"]


def recompress(src, long_side, quality):
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")  # apps apply rotation, then drop EXIF
    img.thumbnail((long_side, long_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)  # no exif/xmp passed: metadata gone
    return buf.getvalue(), ".jpg"


def screenshot(page, src):
    import base64
    mime = {".png": "image/png", ".webp": "image/webp"}.get(src.suffix.lower(), "image/jpeg")
    data = base64.b64encode(src.read_bytes()).decode()
    page.set_content(
        "<html><body style='margin:0;background:#000;display:flex;align-items:center;justify-content:center;height:100vh'>"
        f"<img id=i style='max-width:100%;max-height:100%' src='data:{mime};base64,{data}'></body></html>"
    )
    page.wait_for_function("document.getElementById('i').complete")
    return page.locator("#i").screenshot(type="png"), ".png"


def main():
    done = set()
    if SOURCES.exists():
        done = {r["notes"].removeprefix("copy of ") for r in csv.DictReader(SOURCES.open())}
    originals = [p for truth in ("ai", "real") for p in sorted((IMAGES / truth / "direct").iterdir())
                 if p.suffix.lower() in EXTS and str(p.relative_to(IMAGES)) not in done]
    if not originals:
        print("Nothing new to copy.")
        return

    from playwright.sync_api import sync_playwright
    new = not SOURCES.exists()
    with sync_playwright() as pw, SOURCES.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["file", "truth", "source", "origin", "origin_url", "notes"])
        browser = pw.chromium.launch(channel="chrome", headless=True)
        # iPhone-sized screen at 3x pixel density
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        start = len(done)
        for i, src in enumerate(originals):
            truth = src.parent.parent.name
            method = METHODS[(start + i) % len(METHODS)]
            try:
                if method == "social":
                    data, ext = recompress(src, 1080, 78)
                elif method == "chat":
                    data, ext = recompress(src, 1600, 60)
                else:
                    data, ext = screenshot(page, src)
            except Exception as e:
                print(f"  skip {src.name}: {type(e).__name__}: {e}")
                continue
            rel = f"{truth}/reshared/rs_{method}_{src.stem}{ext}"
            (IMAGES / rel).write_bytes(data)
            w.writerow([rel, truth, "reshared", f"simulated:{method}", "", f"copy of {src.relative_to(IMAGES)}"])
            fh.flush()
            print(f"  {rel}")
        browser.close()


if __name__ == "__main__":
    main()
