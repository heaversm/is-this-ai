"""Turn results/results.csv into results/report.md.

For each check it answers two questions, separately for original files and re-shared copies:
  - How often did it give an answer?
  - When it answered, how often was it right?

The bar: right at least 80% of the time when it answers, and "don't know" otherwise.

    .venv/bin/python report.py
"""

import csv
import math
import random
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results"
BAR = 0.80
CUTOFFS = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99]


def wilson(k, n, z=1.96):
    """95% range for a proportion, honest at small sample sizes."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def pct(x):
    return f"{100 * x:.0f}%"


def summarise(rows, predict):
    """predict(row) -> 'ai', 'real' or None (don't know)."""
    n = len(rows)
    answered = [(r, predict(r)) for r in rows]
    answered = [(r, p) for r, p in answered if p]
    right = sum(1 for r, p in answered if p == r["truth"])
    real_called_ai = sum(1 for r, p in answered if p == "ai" and r["truth"] == "real")
    lo, hi = wilson(right, len(answered))
    return {
        "n": n,
        "answered": len(answered),
        "coverage": len(answered) / n if n else 0,
        "right": right,
        "accuracy": right / len(answered) if answered else None,
        "range": (lo, hi),
        "real_called_ai": real_called_ai,
    }


HEADER = "| Check | Answered | Right when it answered (95% range) | Real photos called AI |\n|---|---|---|---|"


def line(label, s, note=""):
    acc = "—" if s["accuracy"] is None else f"{pct(s['accuracy'])} ({pct(s['range'][0])}–{pct(s['range'][1])})"
    return f"| {label} | {s['answered']}/{s['n']} ({pct(s['coverage'])}){note} | {acc} | {s['real_called_ai']} |"


def detector_predict(name, cutoff):
    def f(r):
        v = r.get(f"p_ai_{name}")
        if v in ("", None):
            return None
        p = float(v)
        if max(p, 1 - p) < cutoff:
            return None
        return "ai" if p >= 0.5 else "real"
    return f


def meta_predict(r):
    return r["meta_verdict"] if r["meta_verdict"] in ("ai", "real") else None


def gemini_predict(r):
    # A found watermark means Google AI made it. Not found only means "not Google", so it's not an answer.
    return "ai" if r.get("gemini_synthid") == "found" else None


def pick_cutoff(rows, name):
    """Lowest confidence cutoff where accuracy meets the bar, needing at least 10 answers."""
    for c in CUTOFFS:
        s = summarise(rows, detector_predict(name, c))
        if s["answered"] >= 10 and s["accuracy"] is not None and s["accuracy"] >= BAR:
            return c
    return None


def cross_validated(rows, name, seed=0):
    """Choose the cutoff on half the images and measure it on the other half, then swap.
    Choosing and measuring on the same images would flatter the detector."""
    # Split by picture, not by file: an original and its re-shared copy always land in the same half.
    groups = sorted({r.get("group") or r["file"] for r in rows})
    random.Random(seed).shuffle(groups)
    half = set(groups[::2])
    a = [r for r in rows if (r.get("group") or r["file"]) in half]
    b = [r for r in rows if (r.get("group") or r["file"]) not in half]
    total = {"answered": 0, "right": 0, "n": 0, "real_called_ai": 0}
    cutoffs = []
    for train, test in ((a, b), (b, a)):
        c = pick_cutoff(train, name)
        cutoffs.append(c)
        total["n"] += len(test)
        if c is None:
            continue
        s = summarise(test, detector_predict(name, c))
        for k in ("answered", "right", "real_called_ai"):
            total[k] += s[k]
    total["coverage"] = total["answered"] / total["n"] if total["n"] else 0
    total["accuracy"] = total["right"] / total["answered"] if total["answered"] else None
    total["range"] = wilson(total["right"], total["answered"])
    return total, cutoffs


def main():
    import argparse
    global RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(RESULTS))
    RESULTS = Path(ap.parse_args().results)
    rows = list(csv.DictReader((RESULTS / "results.csv").open()))
    detectors = [k[len("p_ai_"):] for k in rows[0] if k.startswith("p_ai_")]
    groups = {"Original files": [r for r in rows if r["source"] == "direct"],
              "Re-shared copies": [r for r in rows if r["source"] == "reshared"],
              "All images": rows}
    has_gemini = any(r.get("gemini_synthid") for r in rows)

    # The detector used for the "Likely" level: answers most often in cross-validation while staying above the bar.
    best, best_cov = None, -1
    for d in detectors:
        s, _ = cross_validated(rows, d)
        if s["accuracy"] is not None and s["accuracy"] >= BAR and s["coverage"] > best_cov:
            best, best_cov = d, s["coverage"]
    cut = pick_cutoff(rows, best) if best else None

    def level(r):
        p = meta_predict(r) or gemini_predict(r)
        if p:
            return "Confirmed", p
        if best and cut:
            p = detector_predict(best, cut)(r)
            if p:
                return "Likely", p
        return "Don't know", None

    counts = {(t, s): sum(1 for r in rows if r["truth"] == t and r["source"] == s) for t in ("ai", "real") for s in ("direct", "reshared")}
    L = ["# Provenance check — results", "",
         f"{len(rows)} images: AI originals {counts['ai','direct']}, AI re-shared {counts['ai','reshared']}, "
         f"real originals {counts['real','direct']}, real re-shared {counts['real','reshared']}.", "",
         f"The bar: right at least {pct(BAR)} of the time when it gives an answer.", ""]
    if len(rows) < 100:
        L += [f"*With {len(rows)} images the ranges are wide. 200 images gets them to about ±6 points.*", ""]

    # 1. The combined display
    L += ["## The combined display", "",
          "- **Confirmed:** metadata, a signed label, or Google's watermark says so.",
          (f"- **Likely:** detector `{best}` is at least {cut} confident. It's the detector that answered most often "
           f"while staying above {pct(BAR)} when tested on images it wasn't tuned on.") if best else
          f"- **Likely:** not shown. No detector stayed above {pct(BAR)} on images it wasn't tuned on.",
          "- **Don't know:** everything else.", ""]
    for gname, g in groups.items():
        L += [f"**{gname}**", "", HEADER.replace("Check", "Level")]
        for lv in ("Confirmed", "Likely"):
            L.append(line(lv, summarise(g, lambda r, lv=lv: level(r)[1] if level(r)[0] == lv else None)))
        dk = sum(1 for r in g if level(r)[0] == "Don't know")
        L.append(f"| Don't know | {dk}/{len(g)} ({pct(dk / len(g) if g else 0)}) | | |")
        L.append("")
    origins = sorted({(r.get("origin") or "").split(":")[0] or "unknown" for r in rows})
    if len(origins) > 1:
        L += ["**By where the images came from**", "",
              "| Where from | Images | Confirmed | Likely | Don't know | Wrong answers |", "|---|---|---|---|---|---|"]
        for o in origins:
            g = [r for r in rows if ((r.get("origin") or "").split(":")[0] or "unknown") == o]
            lv = [level(r) for r in g]
            c = {k: sum(1 for x in lv if x[0] == k) for k in ("Confirmed", "Likely", "Don't know")}
            bad = sum(1 for r, x in zip(g, lv) if x[1] and x[1] != r["truth"])
            dk = c["Don't know"]
            L.append(f"| {o} | {len(g)} | {c['Confirmed']} | {c['Likely']} | {dk} | {bad} |")
        L.append("")
    if best:
        L += ["*The Likely cutoff here was picked on all images, which flatters it a little. "
              "The cross-validated detector table further down is the fairer number.*", ""]

    # 2. Each check alone
    L += ["## Each check on its own", ""]
    for gname, g in groups.items():
        L += [f"**{gname}**", "", HEADER]
        L.append(line("Metadata and signed labels", summarise(g, meta_predict)))
        L.append(line("Google watermark (Gemini)", summarise(g, gemini_predict)) if has_gemini
                 else "| Google watermark (Gemini) | not run | | |")
        for d in detectors:
            L.append(line(f"Detector `{d}`, always answers", summarise(g, detector_predict(d, 0.5))))
        L.append("")

    # 3. Detectors with a confidence cutoff, cross-validated
    L += ["## Detectors, answering only when confident", "",
          f"The cutoff is the lowest confidence that was right {pct(BAR)} of the time on half the images. "
          "It's then measured on the other half, and the halves are swapped. Needs at least 10 answers in a half to pick a cutoff.", ""]
    for gname, g in groups.items():
        L += [f"**{gname}**", "", HEADER.replace("|\n|---|---|---|---|", "| Cutoffs chosen |\n|---|---|---|---|---|")]
        for d in detectors:
            s, cuts = cross_validated(g, d)
            if not any(cuts):
                L.append(f"| `{d}` | too few images, or never reached {pct(BAR)} | | | {cuts} |")
            else:
                L.append(line(f"`{d}`", s) + f" {cuts} |")
        L.append("")

    # 4. Wrong answers
    wrong = [r for r in rows if level(r)[1] and level(r)[1] != r["truth"]]
    L += ["## Wrong answers, to read one by one", ""]
    if wrong:
        L += ["| File | Level | Said | Why | Where from |", "|---|---|---|---|---|"]
        for r in wrong:
            lv, p = level(r)
            why = r["meta_reasons"] or ("Gemini found a watermark" if r.get("gemini_synthid") == "found" else f"detector `{best}`")
            src = r.get("origin_url") or r.get("origin_notes") or r.get("origin", "")
            L.append(f"| `{r['file']}` | {lv} | {p} | {why} | {r.get('origin', '')} {src} |")
    else:
        L.append("None.")
    L.append("")

    out = RESULTS / "report.md"
    out.write_text("\n".join(L))
    print(out.read_text())


if __name__ == "__main__":
    main()
