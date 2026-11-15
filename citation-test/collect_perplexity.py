"""Ask Perplexity each question (logged out, in a real Chrome window) and save its
answer as Markdown, with each source link right after the claim it supports.

    .venv/bin/python collect_perplexity.py            # all questions not yet answered
    .venv/bin/python collect_perplexity.py --limit 3  # just the first 3, to test

Answers go to answers/perplexity/<nn>.md. Re-runs skip questions already answered.
Runs with no visible window. Logged out, Perplexity stops after ~15-20 questions;
run login.py once first to use your account.
"""

import argparse
import json
import socket
import subprocess
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
OUT = HERE / "answers" / "perplexity"
URL = "https://www.perplexity.ai/"
EXTRACT = r"""() => {
  const roots = [...document.querySelectorAll('main div.prose')];
  if (!roots.length) return null;
  const root = roots[roots.length - 1];
  function ser(node) {
    let out = '';
    for (const n of node.childNodes) {
      if (n.nodeType === 3) { out += n.textContent; continue; }
      if (n.nodeType !== 1) continue;
      if (n.matches('span.citation')) {
        const a = n.querySelector('a[href^="http"]');
        const label = (n.innerText || '').trim().split('\n')[0];
        if (a) out += ` [${label}](${a.href})`;
      } else if (n.matches('p,h1,h2,h3,h4')) out += '\n\n' + ser(n).trim();
      else if (n.matches('li')) out += '\n- ' + ser(n).trim();
      else out += ser(n);
    }
    return out;
  }
  return ser(root).trim();
}"""
PROFILE = HERE / ".ai-profile"   # logins saved by login.py
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9335
LIMIT_MSG = "Sign up and repeat your request"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"


def questions():
    qs = [l.strip() for l in (HERE / "questions.txt").read_text().splitlines()]
    return [q for q in qs if q and not q.startswith("#")]


DISMISS = ["Decline optional", "Maybe later", "Not now", "No thanks", "Close", "Dismiss"]  # cookie banner first: it can cover the promo's buttons


def dismiss_popups(pg):
    """Close promo pop-ups and cookie banners that cover the question box."""
    for _ in range(3):
        clicked = False
        for name in DISMISS:
            b = pg.get_by_role("button", name=name, exact=True).filter(visible=True)
            if b.count():
                try:
                    b.first.click(timeout=3000)
                except Exception:
                    b.first.click(timeout=3000, force=True)
                pg.wait_for_timeout(600); clicked = True
        if not clicked:
            break
    pg.keyboard.press("Escape")


def ask(ctx, q):
    pg = ctx.new_page()
    try:
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        try:
            dismiss_popups(pg)
        except Exception:
            pass  # a pop-up we couldn't close shouldn't fail the question; the box check below will
        box = pg.locator("textarea, [contenteditable=true]").first
        box.wait_for(state="visible", timeout=20000)
        box.click()
        box.fill(q)
        pg.keyboard.press("Enter")
        # Wait for Perplexity's own "Finished" marker, then until the text stops changing
        pg.locator("main button", has_text="Finished").first.wait_for(state="visible", timeout=150000)
        last, stable = "", 0
        for _ in range(60):
            time.sleep(1)
            t = pg.locator("main").inner_text()
            stable = stable + 1 if t == last else 0
            last = t
            if stable >= 3:
                break
        # Read the answer and its citation links straight from the page (never the clipboard)
        md = pg.evaluate(EXTRACT) or ""
        if LIMIT_MSG in pg.locator("main").inner_text():
            raise RuntimeError("Perplexity's logged-out limit was reached; run login.py")
        if q.lower()[:30] not in pg.locator("main").inner_text().lower():
            raise RuntimeError("page doesn't show this question")
        sources = pg.evaluate(
            "() => [...document.querySelectorAll('main a[href^=http]')].map(a=>a.href).filter(h=>!h.includes('perplexity.ai'))"
        )
        return md, pg.url, sources
    finally:
        pg.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pause", type=float, default=45, help="seconds between questions")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    qs = questions()
    if args.limit:
        qs = qs[: args.limit]
    with sync_playwright() as p:
        # No visible window. Real Chrome, hidden, with the profile login.py saved, reached
        # through its debugging port (Playwright's own launch can't read saved logins).
        chrome = None
        if PROFILE.exists():
            chrome = subprocess.Popen([CHROME, f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}", "--headless=new",
                                       f"--user-agent={UA}", "--no-first-run", "about:blank"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(40):
                try:
                    socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close(); break
                except OSError:
                    time.sleep(0.5)
            ctx = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}").contexts[0]
        else:
            ctx = p.chromium.launch(channel="chrome", headless=True, args=["--disable-blink-features=AutomationControlled"]).new_context(user_agent=UA)
        for i, q in enumerate(qs, 1):
            f = OUT / f"{i:02d}.md"
            if f.exists():
                continue
            try:
                md, url, sources = ask(ctx, q)
                if "](http" not in md and not sources:
                    # Perplexity sometimes answers without searching when used heavily; retry later
                    print(f"[{i}/{len(qs)}] {q[:60]} — no sources this time, not saved")
                    time.sleep(args.pause)
                    continue
                meta = {"question": q, "tool": "perplexity", "url": url, "collected": time.strftime("%Y-%m-%d %H:%M"), "page_links": sources}
                f.write_text("<!--meta " + json.dumps(meta) + " -->\n" + md)
                n = len(re.findall(r"\]\(https?://", md))
                print(f"[{i}/{len(qs)}] {q[:60]} — {n} citations")
            except Exception as e:
                print(f"[{i}/{len(qs)}] {q[:60]} — FAILED: {type(e).__name__}: {str(e)[:150]}")
            time.sleep(args.pause)
        if chrome:
            chrome.terminate()
        else:
            ctx.close()


if __name__ == "__main__":
    main()
