"""Hand-labeling page: judge a sample of claim-and-source pairs yourself, so we can
measure whether the automatic checker is accurate enough to trust.

You don't see the checker's verdict. Each answer you click is saved straight away
to data/human_labels.json, so you can stop and come back.

    .venv/bin/python label_server.py      then open http://localhost:8766
"""

import hashlib
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from judge import excerpts

HERE = Path(__file__).parent
DATA = HERE / "data"
LABELS = DATA / "human_labels.json"
SAMPLE = DATA / "label_sample.json"
PORT = 8766
N = 50


def answer_parts(tool, qid, claim):
    """Perplexity's whole answer as plain text, split around the claim so the page can
    highlight it. Citation links become [label] markers."""
    import re
    from claims import clean
    md = (HERE / "answers" / tool / f"{qid}.md").read_text().split("-->", 1)[1]
    md = re.sub(r"\[([^\]]{1,80})\]\(https?://[^)\s]+\)", r"[\1]", md)
    blocks = [clean(b) for b in re.split(r"\n\s*\n|\n(?=\s*[-•]|\s*\d+[.)]\s)", md) if b.strip()]
    text = "\n\n".join(b for b in blocks if b)
    flat = lambda t: re.sub(r"\s*\[[^\]]{1,80}\]", "", t)
    # find the claim, ignoring the [label] markers
    plain, idx = "", []
    for k, ch in enumerate(text):
        idx.append(len(plain)); plain += ch
    target = flat(claim)
    m = re.search(re.escape(target[:60]).replace("\\ ", r"\s+"), re.sub(r"\s*\[[^\]]{1,80}\]", lambda x: " " * len(x.group(0)), text))
    if not m:
        return {"answer_before": text, "answer_claim": "", "answer_after": ""}
    start = m.start()
    end = min(len(text), start + len(claim) + 120)
    # extend to the end of the claim's citation marker(s)
    tail = re.match(r".*?(\s*\[[^\]]{1,80}\])+", text[start:end], re.S)
    stop = start + (tail.end() if tail else len(claim))
    return {"answer_before": text[:start], "answer_claim": text[start:stop], "answer_after": text[stop:]}


def build_sample():
    """About 50 pairs the checker could read: up to half from the pairs it didn't call
    'supported' (rarer, and they matter most), the rest a random set it did."""
    if SAMPLE.exists():
        cached = json.loads(SAMPLE.read_text())
        if cached and "answer_claim" in cached[0]:
            return cached
    claims = {c["cid"]: c for c in map(json.loads, (DATA / "claims.jsonl").read_text().splitlines())}
    js = [j for j in map(json.loads, (DATA / "judgments.jsonl").read_text().splitlines()) if j["verdict"] != "can't_check"]
    rng = random.Random(7)
    other = [j for j in js if j["verdict"] != "supported"]
    sup = [j for j in js if j["verdict"] == "supported"]
    rng.shuffle(sup)
    k = min(len(other), N // 2)  # up to half from the pairs it didn't call supported
    pick = rng.sample(other, k) + sup[: N - k]
    rng.shuffle(pick)
    items = []
    for j in pick:
        c = claims[j["cid"]]
        src = json.loads((DATA / "sources" / f"{hashlib.sha1(j['url'].encode()).hexdigest()[:16]}.json").read_text())
        prev_cid = c["cid"][:-2] + f"{int(c['cid'][-2:]) - 1:02d}"
        before = claims[prev_cid]["claim"] if prev_cid in claims else ""
        items.append({"id": f"{j['cid']}|{j['url']}", "question": c["question"], "before": before, "claim": c["claim"], "url": j["url"],
                      **answer_parts(c["tool"], c["qid"], c["claim"]),
                      "excerpt": excerpts(src["text"], c["claim"])})
    SAMPLE.write_text(json.dumps(items, indent=1))
    return items


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Does the cited page back up the claim? — Citation check</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700&family=Public+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
 :root{--paper:#f6f3ec;--paper-2:#ece7dc;--ink:#151412;--ink-2:#4d4a44;--ink-3:#7b776e;--rule:#d8d2c4;--accent:#2a78d6;--hl:#ffe28a;
   --serif:"Newsreader",Georgia,serif;--sans:"Public Sans","Helvetica Neue",sans-serif}
 *{box-sizing:border-box} body{margin:0;padding:0 32px 72px;background:var(--paper);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
 a{color:inherit;text-decoration-color:var(--ink-3);text-underline-offset:3px} a:hover{text-decoration-color:var(--ink)}
 .wrap{max-width:1180px;margin:0 auto}
 .mast{border-bottom:1px solid var(--ink);padding:18px 0 12px;display:flex;justify-content:space-between;font:500 12px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2)}
 .head{display:grid;grid-template-columns:1.4fr 1fr;gap:48px;align-items:end;padding:40px 0 24px;border-bottom:1px solid var(--rule)}
 h1{font:600 clamp(32px,4vw,46px)/1.05 var(--serif);letter-spacing:-.015em;margin:0 0 12px}
 .dek{font:400 18px/1.5 var(--serif);color:var(--ink-2);margin:0;max-width:52ch}
 .progress{border-top:3px solid var(--ink);padding-top:12px}
 .progress .big{font:700 52px/1 var(--serif);letter-spacing:-.02em}.progress .big span{color:var(--ink-3);font-weight:400}
 .progress p{margin:6px 0 10px;font-size:14px;color:var(--ink-2)}
 .bar{height:6px;background:var(--paper-2);border-radius:3px}.bar b{display:block;height:100%;width:0;background:var(--accent);border-radius:3px;transition:width .4s}
 .label{font:600 12px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);margin:0 0 10px}
 .nav{display:flex;gap:14px;align-items:center;font-size:14px;color:var(--ink-2);padding:18px 0}
 .nav button{font:500 14px/1 var(--sans);padding:8px 12px;border:1px solid var(--ink-3);background:transparent;border-radius:2px;cursor:pointer}
 .nav button:hover{border-color:var(--ink)}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:start}
 .q{font:600 24px/1.25 var(--serif);margin:0 0 28px}
 .answer{border-left:3px solid var(--rule);padding:2px 0 2px 18px;font-size:14px;color:var(--ink-3);white-space:pre-wrap;max-height:52vh;overflow:auto;margin-bottom:28px}
 .answer mark{display:block;background:var(--hl);color:var(--ink);font:400 21px/1.45 var(--serif);padding:12px 14px;margin:10px 0;border-left:4px solid #e0b400}
 .claim{border-left:3px solid var(--ink);padding:2px 0 2px 18px;font:400 22px/1.45 var(--serif);margin-bottom:30px}
 .ask{font:600 20px/1.3 var(--serif);margin:0 0 14px}
 .opts{border-top:1px solid var(--ink)}
 .opt{display:grid;grid-template-columns:1fr;gap:10px;align-items:baseline;width:100%;text-align:left;padding:13px 4px;background:transparent;border:0;border-bottom:1px solid var(--rule);cursor:pointer;font:inherit;color:var(--ink)}
 .opt kbd{font:500 13px/1 var(--sans);color:var(--ink-3);border:1px solid var(--rule);border-radius:2px;padding:4px 7px;justify-self:start}
 .opt b{font:600 16px/1.3 var(--sans)} .opt small{display:block;font-size:13px;color:var(--ink-3);margin-top:2px}
 .opt:hover,.opt:focus-visible{background:var(--paper-2);outline:none}
 .opt.on{background:var(--ink);color:var(--paper)} .opt.on small,.opt.on kbd{color:#d6d1c6;border-color:#5a5650}
 .keys{font-size:13px;color:var(--ink-3);margin-top:12px}
 .srchead{display:flex;justify-content:space-between;gap:16px;align-items:baseline;margin-bottom:10px}
 .srchead .label{margin:0}.srchead a{font-size:13px;white-space:nowrap}
 .url{font-size:13px;color:var(--ink-3);margin:-4px 0 12px;word-break:break-all}
 .src{background:#fff;border:1px solid var(--rule);padding:18px 20px;max-height:72vh;overflow:auto;font:400 16px/1.6 var(--serif);color:var(--ink);white-space:pre-wrap}
 .src .gap{display:block;font:500 11px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);text-align:center;margin:14px 0;white-space:normal}
 .source{border-top:3px solid var(--ink);padding-top:16px}
 .source .site{font:600 26px/1.2 var(--serif);margin:0 0 6px}
 .source .url{font-size:13px;color:var(--ink-3);word-break:break-all;margin:0 0 20px}
 .source a.open{display:inline-block;font:600 16px/1 var(--sans);padding:14px 18px;border-radius:3px;background:var(--ink);color:var(--paper);text-decoration:none}
 .source a.open:hover{background:#000}
 .source .how{font-size:14px;color:var(--ink-2);margin:16px 0 0;max-width:46ch}
 .done{padding:64px 0}.done h2{font:600 36px/1.1 var(--serif);margin:0 0 12px}
 @media (max-width:860px){body{padding:0 20px 60px}.head,.grid{grid-template-columns:1fr;gap:24px}}
</style></head><body><div class="wrap">
<header class="mast"><span>Citation check</span><span>Hand labels</span></header>
<div class="head">
  <div><p class="label">Checking the checker</p><h1>Does the cited page back up the claim?</h1>
  <p class="dek">Each item is one claim from a Perplexity answer, and the page Perplexity cited for it. Open the page and judge only from what it says: not from what you know, and not from whether the answer is good.</p></div>
  <div class="progress"><div class="big" id="count">0<span>/50</span></div><p>labeled · saved as you go</p><div class="bar"><b id="prog"></b></div></div>
</div>
<div id="app"></div></div>
<script>
let items=[], labels={}, i=0;
const OPTS=[['supported','Backs it up','The page states the claim’s main point, including any numbers'],['partly','Partly','Some of it, but a number, date or detail is missing or different'],['not_found','Doesn’t say it','Even if the page is on the same topic'],['contradicts','Says the opposite','The page states something that conflicts with the claim'],['cant_tell','Can’t tell','The page is unclear, or I’d need more of it']];
async function load(){ items=await (await fetch('/items')).json(); labels=await (await fetch('/labels')).json();
  i=items.findIndex(x=>!labels[x.id]); if(i<0)i=items.length; render(); }
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function render(){ const done=Object.keys(labels).length;
  document.getElementById('prog').style.width=(100*done/items.length)+'%';
  document.getElementById('count').innerHTML=`${done}<span>/${items.length}</span>`;
  const app=document.getElementById('app');
  if(i>=items.length){ app.innerHTML=`<div class="done"><h2>All ${items.length} done. Thank you.</h2><p class="dek">Your labels are saved. You can close this tab.</p><div class="nav"><button onclick="i=0;render()">Review from the start</button></div></div>`; return; }
  const it=items[i], cur=labels[it.id];
  const ans = it.answer_claim ? `${esc(it.answer_before)}<mark id="hl">${esc(it.answer_claim)}</mark>${esc(it.answer_after)}` : `<mark id="hl">${esc(it.claim)}</mark>`;
  const src = esc(it.excerpt).split('\n...\n').join('<span class="gap">— part of the page skipped —</span>');
  app.innerHTML=`<div class="nav"><button onclick="i=Math.max(0,i-1);render()">← Back</button><span>Item ${i+1} of ${items.length}</span></div>
  <div class="grid"><div>
    <p class="label">Someone asked Perplexity</p><p class="q">${esc(it.question)}</p>
    <p class="label">Its answer · the claim to check is highlighted</p><div class="answer">${ans}</div>
  </div><div>
    <p class="label">The source Perplexity cited for this claim</p>
    <div class="source">
      <p class="site">${esc(new URL(it.url).hostname.replace(/^www\./,''))}</p>
      <p class="url">${esc(it.url)}</p>
      <a class="open" href="${it.url}" target="_blank" rel="noopener">Open the source in a new tab ↗</a>
      <p class="how">Read the page, check whether it says what the highlighted claim says, then come back here and choose an answer.</p>
    <p class="ask" style="margin-top:36px">Does the cited page back up this claim?</p>
    <div class="opts">${OPTS.map(([v,t,h],k)=>`<button class="opt ${cur===v?'on':''}" onclick="pick('${v}')"><span><b>${t}</b><small>${h}</small></span></button>`).join('')}</div>
    </div>
  </div></div>`;
  window.scrollTo(0,0); const hl=document.getElementById('hl'); if(hl){ const box=hl.closest('.answer'); box.scrollTop=hl.offsetTop-box.offsetTop-60; } }
async function pick(v){ const it=items[i]; labels[it.id]=v; await fetch('/label',{method:'POST',body:JSON.stringify({id:it.id,label:v})}); i++; render(); }
// Keyboard answering is off: it caused accidental answers. Answer by clicking.
load();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/items":
            return self.send(json.dumps(build_sample()))
        if self.path == "/labels":
            return self.send(LABELS.read_text() if LABELS.exists() else "{}")
        return self.send(PAGE, "text/html; charset=utf-8")

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        labels = json.loads(LABELS.read_text()) if LABELS.exists() else {}
        labels[body["id"]] = body["label"]
        LABELS.write_text(json.dumps(labels, indent=1))
        self.send("{}")


if __name__ == "__main__":
    print(f"{len(build_sample())} pairs to label. Open http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
