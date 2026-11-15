"""One-time login for the answer collectors.

Opens a normal Chrome window, with its own profile (folder .ai-profile/, not your
everyday Chrome), on the sites below. Log in, press Enter, and it checks each
site is really logged in before closing. If one isn't, it says which, and keeps
the window open so you can fix it. Gemini isn't here: the collector reuses the
Google login already saved for the watermark check.

    .venv/bin/python login.py
"""

import socket
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
PROFILE = HERE / ".ai-profile"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9334
SITES = {  # site: (address, text of the button shown when logged out)
    "Perplexity": ("https://www.perplexity.ai/", "Sign in"),
    "ChatGPT": ("https://chatgpt.com/", "Log in"),
}


def logged_in(ctx, url, signin):
    pg = ctx.new_page()
    try:
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        return (pg.get_by_role("button", name=signin).count() + pg.get_by_role("link", name=signin).count()) == 0
    finally:
        pg.close()


def main():
    PROFILE.mkdir(exist_ok=True)
    proc = subprocess.Popen([CHROME, f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}",
                             "--no-first-run", "--no-default-browser-check", *[u for u, _ in SITES.values()]],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.5)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = browser.contexts[0]
        while True:
            input(f"Log in on each tab ({', '.join(SITES)}), then press Enter here... ")
            status = {name: logged_in(ctx, u, s) for name, (u, s) in SITES.items()}
            for name, ok in status.items():
                print(f"  {name}: {'logged in' if ok else 'NOT logged in yet'}")
            if all(status.values()):
                break
            print("Finish the ones marked NOT logged in, then press Enter again.")
        # Quit Chrome cleanly (not killed), so the logins are written to disk
        browser.new_browser_cdp_session().send("Browser.close")
    proc.wait(timeout=20)
    print("Saved. The collectors will use these logins without opening a window.")


if __name__ == "__main__":
    main()
