"""Run every check on every image in images/ and write results/results.csv.

The folder an image sits in is its known answer:
    images/ai/direct/      AI-made, the original file from the generator
    images/ai/reshared/    AI-made, as found or re-saved on social media / chat apps / screenshots
    images/real/direct/    real photo, the original file from the camera or publisher
    images/real/reshared/  real photo, as found or re-saved on social media / chat apps / screenshots

    .venv/bin/python run.py              # metadata + the four detectors (local, free)
    .venv/bin/python run.py --gemini     # also run the Google watermark check (needs gemini_check.py --login first)

Results are cached, so adding images and re-running only checks the new ones.
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = HERE / "images"
RESULTS = HERE / "results"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff", ".gif", ".avif"}


def set_dirs(images, results):
    global IMAGES, RESULTS
    IMAGES, RESULTS = Path(images).resolve(), Path(results).resolve()


def list_images():
    out = []
    for truth in ("ai", "real"):
        for source in ("direct", "reshared"):
            for f in sorted((IMAGES / truth / source).rglob("*")):
                if f.suffix.lower() in EXTS:
                    out.append((str(f.resolve()), truth, source))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemini", action="store_true", help="also run the Gemini watermark check")
    ap.add_argument("--images", default=str(IMAGES), help="folder of labelled images (default: images/)")
    ap.add_argument("--results", default=str(RESULTS), help="output folder (default: results/)")
    args = ap.parse_args()
    set_dirs(args.images, args.results)

    images = list_images()
    if not images:
        sys.exit("No images found. Put them in images/{ai,real}/{direct,reshared}/ — see README.md.")
    print(f"{len(images)} images")
    RESULTS.mkdir(parents=True, exist_ok=True)

    from check_metadata import check
    import detectors

    cache_path = RESULTS / "detectors.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for i, (f, _, _) in enumerate(images, 1):
        if f in cache and all(n in cache[f] for n in detectors.ALL):
            continue
        try:
            cache[f] = detectors.run_all(f)
        except Exception as e:
            cache[f] = {"error": f"{type(e).__name__}: {e}"}
        print(f"  detectors [{i}/{len(images)}] {f}")
        cache_path.write_text(json.dumps(cache, indent=2))

    if args.gemini:
        subprocess.run([sys.executable, str(HERE / "gemini_check.py"), "--cache", str(RESULTS / "gemini.json"), *[f for f, _, _ in images]], cwd=HERE, check=False)
    gem_path = RESULTS / "gemini.json"
    gem = json.loads(gem_path.read_text()) if gem_path.exists() else {}

    # Where each image came from: collect/sources_*.csv, written by the collectors and the fact-check agent
    sources = {}
    for sf in sorted((HERE / "collect").glob("sources_*.csv")):
        for r in csv.DictReader(sf.open()):
            sources[r["file"]] = r

    rows = []
    for f, truth, source in images:
        m = check(f)
        m["file"] = f
        row = {"file": str(Path(f).relative_to(IMAGES)), "truth": truth, "source": source, **{k: v for k, v in m.items() if k != "file"}}
        for n in detectors.ALL:
            row[f"p_ai_{n}"] = cache.get(f, {}).get(n, "")
        row["gemini_synthid"] = gem.get(f, {}).get("synthid", "")
        src = sources.get(row["file"], {})
        if src and src.get("truth") and src["truth"] != truth:
            print(f"  WARNING: {row['file']} is in the {truth} folder but its source record says {src['truth']}")
        row["origin"] = src.get("origin", "added by hand")
        row["origin_url"] = src.get("origin_url", "")
        row["origin_notes"] = src.get("notes", "")
        # Copies of the same picture share a group, so the report never tunes on one and tests on the other
        row["group"] = src["notes"].removeprefix("copy of ") if src.get("notes", "").startswith("copy of ") else row["file"]
        rows.append(row)

    out = RESULTS / "results.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out}. Next: .venv/bin/python report.py --results {RESULTS}")


if __name__ == "__main__":
    main()
