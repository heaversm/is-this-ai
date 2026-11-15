"""Download every cited source and pull out its readable text.

Each URL gets a status:
  ok       text extracted
  dead     the page doesn't exist (404, 410, bad domain)
  blocked  the site refused us (401, 403, 429, bot wall), so we can't judge it
  empty    the page loaded but had no readable text (e.g. a video or an app page)

Plain HTTP first; if a site refuses, it tries again in a real browser.
Results are cached in data/sources/, so re-runs only fetch new URLs.

    .venv/bin/python fetch_sources.py
"""

import hashlib
import io
import json
from pathlib import Path

import requests
import trafilatura
from pypdf import PdfReader

HERE = Path(__file__).parent
CACHE = HERE / "data" / "sources"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def key(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def pdf_text(data):
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:40])
    except Exception:
        return ""


def from_response(content, ctype):
    if "pdf" in ctype or content[:4] == b"%PDF":
        return pdf_text(content)
    return trafilatura.extract(content.decode("utf-8", "ignore"), include_tables=True, favor_recall=True) or ""


def fetch_plain(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en"}, timeout=25, allow_redirects=True)
    except requests.RequestException as e:
        return {"status": "dead", "detail": type(e).__name__}
    if r.status_code in (404, 410):
        return {"status": "dead", "detail": f"HTTP {r.status_code}"}
    if r.status_code >= 400:
        return {"status": "blocked", "detail": f"HTTP {r.status_code}"}
    text = from_response(r.content, r.headers.get("content-type", ""))
    return {"status": "ok" if len(text.split()) > 40 else "empty", "detail": f"HTTP {r.status_code}", "text": text, "final_url": r.url}


def fetch_browser(page, url):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        code = resp.status if resp else 0
        if code in (404, 410):
            return {"status": "dead", "detail": f"browser HTTP {code}"}
        text = trafilatura.extract(page.content(), include_tables=True, favor_recall=True) or ""
        if code >= 400 and len(text.split()) < 80:
            return {"status": "blocked", "detail": f"browser HTTP {code}"}
        return {"status": "ok" if len(text.split()) > 40 else "empty", "detail": f"browser HTTP {code}", "text": text, "final_url": page.url}
    except Exception as e:
        return {"status": "blocked", "detail": f"browser {type(e).__name__}"}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    urls = []
    for line in (HERE / "data" / "claims.jsonl").read_text().splitlines():
        urls += json.loads(line)["urls"]
    urls = [u for u in dict.fromkeys(urls) if not (CACHE / f"{key(u)}.json").exists()]
    print(f"{len(urls)} sources to fetch")
    retry = []
    for i, u in enumerate(urls, 1):
        res = fetch_plain(u)
        if res["status"] in ("blocked", "empty"):
            retry.append(u)
        else:
            (CACHE / f"{key(u)}.json").write_text(json.dumps({"url": u, **res}))
        print(f"  [{i}/{len(urls)}] {res['status']:7} {u[:90]}")
    if retry:
        from playwright.sync_api import sync_playwright
        print(f"Retrying {len(retry)} in a browser")
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            page = b.new_page(user_agent=UA)
            for u in retry:
                res = fetch_browser(page, u)
                (CACHE / f"{key(u)}.json").write_text(json.dumps({"url": u, **res}))
                print(f"  {res['status']:7} {u[:90]}")
            b.close()


if __name__ == "__main__":
    main()
