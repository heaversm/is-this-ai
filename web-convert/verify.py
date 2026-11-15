"""Check that a converted model gives the same answers as the original on the 363
test images: how far its scores drift, and how many verdicts change at the 95% line.

    .venv/bin/python verify.py swinv2 model_int8.onnx
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

HERE = Path(__file__).parent
PROV = HERE.parent / "image-test"  # this repo's image test (images/ must be collected first)
COL = {"swinv2": "haywoodsloan_swinv2", "siglip": "ateeqq_siglip", "sdxl": "organika_sdxl", "commfor": "commfor_vit384"}


def prep(img, p):
    img = ImageOps.exif_transpose(img).convert("RGB")  # same as the original tool: apply camera rotation first
    if "resize_exact" in p:
        h, w = p["resize_exact"]
        img = img.resize((w, h), Image.Resampling(p["resample"]))
        a = np.asarray(img, dtype=np.float32) * p["rescale"]
    else:  # Community Forensics: shortest side to 440, centre crop 384
        # torchvision's rules: the long side is truncated, not rounded; the crop offset is rounded
        s = p["resize_short"]; W, H = img.size
        nw, nh = (s, int(s * H / W)) if W <= H else (int(s * W / H), s)
        img = img.resize((nw, nh), Image.BILINEAR)
        W, H = img.size; c = p["crop"]; l, t = int(round((W - c) / 2.0)), int(round((H - c) / 2.0))
        a = np.asarray(img.crop((l, t, l + c, t + c)), dtype=np.float32) / 255.0
    a = (a - np.array(p["mean"], dtype=np.float32)) / np.array(p["std"], dtype=np.float32)
    return a.transpose(2, 0, 1)[None]


def side(v):
    return "ai" if v >= 0.95 else "real" if v <= 0.05 else "none"


def main():
    name, fname = sys.argv[1], sys.argv[2]
    d = HERE / "out" / name
    p = json.loads((d / "prep.json").read_text())
    sess = ort.InferenceSession(str(d / fname), providers=["CPUExecutionProvider"])
    rows = list(csv.DictReader((PROV / "results" / "results.csv").open()))
    diffs, flips, out = [], [], {}
    for r in rows:
        img = Image.open(PROV / "images" / r["file"])
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
        v = float(sess.run(None, {"pixel_values": prep(img, p)})[0][0])
        ref = float(r[f"p_ai_{COL[name]}"])
        diffs.append(abs(v - ref)); out[r["file"]] = v
        if side(v) != side(ref):
            flips.append((r["file"], round(ref, 3), round(v, 3)))
    diffs = np.array(diffs)
    print(f"{name}/{fname}: {len(rows)} images | median drift {np.median(diffs):.4f} | 95th pct {np.percentile(diffs, 95):.4f} | max {diffs.max():.3f}")
    print(f"  verdicts changed at the 95% line: {len(flips)}")
    for f in flips[:12]:
        print("   ", f)
    (d / f"verify_{fname}.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
