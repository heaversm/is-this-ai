"""For each claim and each source it cites, ask a local model (Ollama, free, nothing
leaves the machine) whether the source supports the claim.

Verdicts:
  supported     the source states what the claim says
  partly        the source supports some of the claim but not all of it
  not_found     the source doesn't say this (it may be about something else)
  contradicts   the source says the opposite
  can't_check   the source couldn't be read (dead, blocked, empty)

Long sources are cut down to the passages that share the most words with the
claim, so the model sees the relevant part.

    .venv/bin/python judge.py                 # all pairs not yet judged
    .venv/bin/python judge.py --model qwen3:14b
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import requests

HERE = Path(__file__).parent
SOURCES = HERE / "data" / "sources"
OUT = HERE / "data" / "judgments.jsonl"
STOP = set("the a an and or of to in on for with is are was were be been it its this that as at by from not no can may than more most which who what when how do does did has have had".split())

PROMPT = """You check citations. Decide whether the SOURCE supports the CLAIM.

CLAIM:
{claim}

SOURCE (excerpts from {url}):
{source}

Answer with JSON only:
{{"verdict": "supported" | "partly" | "not_found" | "contradicts",
  "quote": "the source sentence that best supports or contradicts the claim, copied exactly, or empty",
  "reason": "one short sentence"}}

Rules:
- "supported": the source states the claim's main point, including any numbers in it.
- "partly": the source supports some of the claim, but another part (often a number, date or specific detail) is missing or different.
- "not_found": the source doesn't state the claim, even if it's on the same topic.
- "contradicts": the source states the opposite.
Judge only from the source text, not from what you know."""


def words(t):
    return [w for w in re.findall(r"[a-z0-9%.$]+", t.lower()) if w not in STOP and len(w) > 2 or any(c.isdigit() for c in w)]


def excerpts(text, claim, n=6, size=110):
    w = text.split()
    chunks = [" ".join(w[i:i + size]) for i in range(0, len(w), size // 2)] or [""]
    cw = Counter(words(claim))
    def score(c):
        cc = set(words(c))
        return sum((3 if any(ch.isdigit() for ch in t) else 1) for t in cw if t in cc)
    best = sorted(range(len(chunks)), key=lambda i: -score(chunks[i]))[:n]
    # Chunks overlap by half; merge the chosen ones into continuous stretches so no text repeats
    step, spans = size // 2, []
    for i in sorted(best):
        start, end = i * step, min(i * step + size, len(w))
        if spans and start <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], end)
        else:
            spans.append([start, end])
    return "\n...\n".join(" ".join(w[a:b]) for a, b in spans)


def ask(model, claim, url, src):
    r = requests.post("http://localhost:11434/api/chat", timeout=300, json={
        "model": model, "stream": False, "format": "json", "think": False,
        "options": {"temperature": 0, "num_ctx": 8192},
        "messages": [{"role": "user", "content": PROMPT.format(claim=claim, url=url, source=src)}]})
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:14b")
    args = ap.parse_args()
    done = set()
    if OUT.exists():
        done = {(j["cid"], j["url"], j["model"]) for j in map(json.loads, OUT.read_text().splitlines())}
    claims = [json.loads(l) for l in (HERE / "data" / "claims.jsonl").read_text().splitlines()]
    pairs = [(c, u) for c in claims for u in c["urls"] if (c["cid"], u, args.model) not in done]
    print(f"{len(pairs)} claim-source pairs to judge with {args.model}")
    with OUT.open("a") as fh:
        for i, (c, u) in enumerate(pairs, 1):
            f = SOURCES / f"{hashlib.sha1(u.encode()).hexdigest()[:16]}.json"
            src = json.loads(f.read_text()) if f.exists() else {"status": "dead", "detail": "not fetched"}
            row = {"cid": c["cid"], "tool": c["tool"], "qid": c["qid"], "url": u, "model": args.model, "source_status": src["status"]}
            if src["status"] != "ok":
                row.update(verdict="can't_check", quote="", reason=f"source {src['status']} ({src.get('detail', '')})")
            else:
                try:
                    v = ask(args.model, c["claim"], u, excerpts(src["text"], c["claim"]))
                    row.update(verdict=v.get("verdict", "?"), quote=v.get("quote", ""), reason=v.get("reason", ""))
                except Exception as e:
                    print(f"  error on {c['cid']}: {type(e).__name__}: {e}")
                    continue
            fh.write(json.dumps(row) + "\n"); fh.flush()
            print(f"  [{i}/{len(pairs)}] {row['verdict']:12} {c['claim'][:70]}")


if __name__ == "__main__":
    main()
