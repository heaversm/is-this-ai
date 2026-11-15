"""Google watermark (SynthID) check, by driving the Gemini web app.

Gemini checks uploaded images for Google's SynthID watermark when asked. There is
no public API for this, so the script uploads each image to gemini.google.com in
a real Chrome window and reads the reply. It is for this test only, not a product:
it breaks when Google changes the page, and every image goes to Google.

It uses a separate Chrome profile (folder .gemini-profile/), not your everyday one.

First time only, log in by hand:
    .venv/bin/python gemini_check.py --login

Then check images (results are cached in results/gemini.json, so re-runs skip done ones):
    .venv/bin/python gemini_check.py images/ai/direct/foo.png images/real/direct/bar.jpg
"""

import argparse
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
PROFILE = HERE / ".gemini-profile"
CACHE = HERE / "results" / "gemini.json"
PORT = 9333
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
URL = "https://gemini.google.com/app"

PROMPT = (
    "Was this image made or edited with Google AI? Use your SynthID watermark check on it. "
    "Start your reply with exactly one of these words on its own line: "
    "SYNTHID_FOUND, SYNTHID_NOT_FOUND, CANNOT_CHECK. Then one sentence on what you found."
)


class _Background:
    """Handle for a Chrome started with `open -g`: there's no child process to kill,
    so quitting goes through the debugging port (see quit_chrome)."""
    def terminate(self):
        quit_chrome()


def quit_chrome():
    """Quit the Chrome on PORT cleanly, so its login cookies are written to disk."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}").new_browser_cdp_session().send("Browser.close")
    except Exception:
        pass


def minimize_chrome():
    """Minimize every window of the Chrome on PORT to the Dock (macOS ignores off-screen positions)."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
            cdp = browser.new_browser_cdp_session()
            for t in cdp.send("Target.getTargets")["targetInfos"]:
                if t["type"] == "page":
                    wid = cdp.send("Browser.getWindowForTarget", {"targetId": t["targetId"]})["windowId"]
                    cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"windowState": "minimized"}})
    except Exception:
        pass


def start_chrome(visible=False):
    """Start Chrome as a normal app (not under automation), so Google login works.

    --login: a normal visible window. Checks: Google blocks hidden (headless) Chrome
    with a CAPTCHA, so checks use a normal window, but opened in the background
    (`open -g`, so it never takes focus) and placed off-screen."""
    PROFILE.mkdir(exist_ok=True)
    flags = [f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}", "--no-first-run", "--no-default-browser-check"]
    if visible:
        proc = subprocess.Popen([CHROME, *flags, URL], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["open", "-g", "-n", "-a", "Google Chrome", "--args", *flags,
                        "--window-position=-3000,0", "--window-size=1400,1000", URL], check=False)
        proc = _Background()
    for _ in range(40):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
            if not visible:
                minimize_chrome()
            return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    sys.exit("Chrome didn't open its debugging port. Close any Chrome window using .gemini-profile and retry.")


def parse(reply):
    if "quota" in reply.lower():
        return "quota"  # Gemini's watermark tool is rationed; the check didn't run
    first = reply.strip().upper()
    for word in ("SYNTHID_NOT_FOUND", "SYNTHID_FOUND", "CANNOT_CHECK"):  # NOT_FOUND first: it contains FOUND
        if word in first[:200]:
            return {"SYNTHID_FOUND": "found", "SYNTHID_NOT_FOUND": "not_found", "CANNOT_CHECK": "cannot_check"}[word]
    # Gemini sometimes ignores the format. Fall back to its usual wording.
    low = reply.lower()
    if re.search(r"(no|not|didn.t|did not|doesn.t|couldn.t|could not)[^.]{0,60}synthid|synthid[^.]{0,40}(not|wasn.t)", low):
        return "not_found"
    if re.search(r"(contains|has|detected|found)[^.]{0,40}synthid|synthid[^.]{0,40}(detected|found|present)", low):
        return "found"
    return "unparsed"


def goto(page, url=URL):
    """Load a page, tolerating Gemini's own redirects, which abort the first navigation."""
    for attempt in range(3):
        try:
            page.goto(url, wait_until="load")
            return
        except Exception as e:
            if "ERR_ABORTED" not in str(e) and "interrupted" not in str(e).lower():
                raise
            page.wait_for_timeout(2000)
            if page.url.startswith("https://gemini.google.com"):
                page.wait_for_load_state("load")
                return
    raise RuntimeError("Couldn't load Gemini")


def open_fresh_chat(page):
    """Load a new, empty chat and wait until the upload button is ready.
    Going to the same address from inside a chat doesn't always reset the page,
    so reload, and try once more if the button still isn't there."""
    upload = page.get_by_role("button", name=re.compile("Upload", re.I)).first
    for attempt in range(2):
        goto(page)
        try:
            upload.wait_for(state="visible", timeout=20000)
            page.wait_for_timeout(1000)
            return upload
        except Exception:
            if attempt == 1:
                raise


def check_one(page, path, debug=False):
    try:
        return _check_one(page, path, debug)
    except Exception:
        # Keep a picture of what Gemini was showing, to fix the script from
        shot = HERE / "results" / "gemini_errors" / f"{Path(path).stem}.png"
        shot.parent.mkdir(parents=True, exist_ok=True)
        try:
            page.screenshot(path=str(shot))
        except Exception:
            pass
        raise


def _check_one(page, path, debug=False, dry_run=False):
    goto(page)
    if "unusual traffic" in page.content() or "/sorry/" in page.url:
        raise RuntimeError("Google is asking to confirm you're not a robot. Run: .venv/bin/python gemini_check.py --login, tick the box, then try again.")
    open_fresh_chat(page).click()
    with page.expect_file_chooser(timeout=15000) as fc:
        # Gemini's menu has had two designs: an "Upload files" list item, and (Nov 2026) a "Files" tile
        # Wait for whichever design appears, then click the visible one
        upload = (page.get_by_role("menuitem", name=re.compile(r"Upload files", re.I))
                  .or_(page.get_by_role("button", name=re.compile(r"^\s*(Upload )?files\s*$", re.I)))
                  .or_(page.get_by_text(re.compile(r"^\s*(Upload files|Files)\s*$")))
                  .filter(visible=True).first)
        upload.click(timeout=20000)
    fc.value.set_files(str(path))
    if dry_run:
        return {"synthid": "dry_run", "reply": "uploaded, not sent"}
    # Wait for the thumbnail to finish uploading
    page.wait_for_timeout(3000)

    before = page.locator("model-response").count()
    box = page.get_by_role("textbox", name=re.compile("prompt", re.I))
    box.click()
    box.fill(PROMPT)
    page.keyboard.press("Enter")

    # Wait for a new reply, then until its text stops changing
    # (Gemini's page blocks injected JS, so poll from Python instead of wait_for_function)
    for _ in range(90):
        if page.locator("model-response").count() > before:
            break
        time.sleep(1)
    else:
        raise TimeoutError("no reply from Gemini within 90 s")
    last, stable = "", 0
    for _ in range(120):
        time.sleep(1)
        text = page.locator("model-response").last.inner_text()
        busy = "Connecting to" in text or len(text.strip()) < 25  # tool still running
        stable = stable + 1 if text == last and not busy else 0
        last = text
        if stable >= 4:
            break
    if debug:
        page.screenshot(path=str(HERE / "results" / f"gemini_{Path(path).stem}.png"))
    return {"synthid": parse(last), "reply": last.strip()[:1000]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--login", action="store_true", help="open Chrome to log in to Gemini by hand")
    ap.add_argument("--debug", action="store_true", help="save a screenshot of each reply")
    ap.add_argument("--cache", default=str(CACHE), help="where to store results")
    ap.add_argument("--pause", type=float, default=8, help="seconds between images, to stay under rate limits")
    args = ap.parse_args()

    if args.login:
        proc = start_chrome(visible=True)
        input("Log in to Gemini in the Chrome window that opened (and tick \"I'm not a robot\" if Google asks), then press Enter here to close it... ")
        quit_chrome()
        return

    from playwright.sync_api import sync_playwright

    cache_path = Path(args.cache)
    cache_path.parent.mkdir(exist_ok=True)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    # Retry anything that didn't get a real answer last time
    RETRY = {"error", "cannot_check", "unparsed", "quota"}
    todo = [f for f in args.files if f not in cache or cache[f]["synthid"] in RETRY]
    if not todo:
        print("All files already checked (see results/gemini.json).")
        return

    proc = start_chrome()
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
            ctx = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            goto(page)
            page.wait_for_timeout(3000)
            if page.get_by_role("button", name="Sign in").count():
                sys.exit("Not logged in. Run: .venv/bin/python gemini_check.py --login")
            for i, f in enumerate(todo, 1):
                try:
                    cache[f] = check_one(page, f, args.debug)
                except Exception as e:
                    cache[f] = {"synthid": "error", "reply": f"{type(e).__name__}: {e}"[:500]}
                print(f"[{i}/{len(todo)}] {f}: {cache[f]['synthid']}")
                cache_path.write_text(json.dumps(cache, indent=2))
                recent = [cache[x]["synthid"] for x in todo[max(0, i - 3):i]]
                if len(recent) == 3 and all(r in ("quota", "cannot_check") for r in recent):
                    print("Gemini's watermark-check quota looks used up. Stopping; re-run later and it will "
                          "pick up only the images that didn't get an answer.")
                    break
                time.sleep(args.pause)
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
