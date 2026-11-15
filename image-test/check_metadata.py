"""Metadata checks: signed origin labels (C2PA), the IPTC "made by AI" tag,
generator settings saved in the file, and camera details.

Runs locally. Nothing leaves the machine.

    .venv/bin/python check_metadata.py path/to/image.jpg
"""

import json
import re
import sys
from pathlib import Path

import c2pa
from PIL import Image, ExifTags

# IPTC digital source types (https://cv.iptc.org/newscodes/digitalsourcetype/)
AI_SOURCE_TYPES = {
    "trainedAlgorithmicMedia",             # made by generative AI
    "compositeWithTrainedAlgorithmicMedia", # real image with AI parts
    "algorithmicMedia",                    # made by an algorithm, no training data
}
CAPTURE_SOURCE_TYPES = {"digitalCapture", "negativeFilm", "positiveFilm", "print", "minorHumanEdits", "computationalCapture"}

# Words that generators leave in Software tags or PNG text fields.
GENERATOR_WORDS = re.compile(
    r"\b(?:midjourney|dall[-·\s]?e|openai|chatgpt|stable diffusion|sdxl|comfyui|automatic1111|"
    r"invokeai|novelai|firefly|imagen|gemini|nano banana|flux|leonardo|ideogram|runway|sora|veo|kling)\b",
    re.I,
)
XMP_TOOL_FIELDS = re.compile(r"(?:CreatorTool|softwareAgent|Software)\s*=\s*\"([^\"]*)\"|<(?:xmp:CreatorTool|stEvt:softwareAgent|tiff:Software)>([^<]*)<", re.I)
# PNG text keys that Stable Diffusion tools write.
GENERATOR_PNG_KEYS = {"parameters", "prompt", "workflow", "invokeai_metadata", "sd-metadata", "Dream"}


def _source_type_name(url):
    return url.rstrip("/").split("/")[-1] if url else None


def read_c2pa(path):
    """Return a dict describing the signed origin label, or None if there isn't one."""
    try:
        with c2pa.Reader(str(path)) as reader:
            store = json.loads(reader.json())
    except Exception as e:  # no label, or a format the library can't read
        if "ManifestNotFound" in type(e).__name__ or "JUMBF" in str(e):
            return None
        return {"error": f"{type(e).__name__}: {e}"}

    manifest = store["manifests"][store["active_manifest"]]
    gen = manifest.get("claim_generator") or ""
    info = manifest.get("claim_generator_info") or []
    if info and not gen:
        gen = " ".join(f"{i.get('name', '')}/{i.get('version', '')}" for i in info)

    source_types, actions = set(), []
    # Look through every manifest in the chain, not only the latest one:
    # an AI step earlier in the edit history still counts.
    for m in store["manifests"].values():
        for a in m.get("assertions", []):
            if a["label"].startswith("c2pa.actions"):
                for act in a["data"].get("actions", []):
                    actions.append(act.get("action"))
                    st = _source_type_name(act.get("digitalSourceType"))
                    if st:
                        source_types.add(st)

    sig = manifest.get("signature_info") or {}
    return {
        "generator": gen,
        "signer": sig.get("issuer") or sig.get("common_name"),
        "validation": store.get("validation_state"),  # Invalid / Valid / Trusted
        "source_types": sorted(source_types),
        "actions": actions,
    }


def read_iptc_source_type(path):
    """The IPTC tag lives in XMP, which is plain text inside the file. A byte search
    finds it in JPEG, PNG, WebP and TIFF without a separate XMP parser."""
    data = Path(path).read_bytes()
    found = set()
    for m in re.finditer(rb"digitalsourcetype/([A-Za-z]+)|DigitalSourceType[\"'>=\s]+([A-Za-z]+)", data):
        found.add((m.group(1) or m.group(2)).decode())
    return sorted(found)


def read_exif_and_text(path):
    out = {"camera": None, "software": None, "png_generator_keys": [], "text_hits": []}
    try:
        img = Image.open(path)
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out

    exif = img.getexif()
    tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    make, model = str(tags.get("Make", "")).strip(), str(tags.get("Model", "")).strip()
    if make or model:
        out["camera"] = f"{make} {model}".strip()
    if tags.get("Software"):
        out["software"] = str(tags["Software"]).strip()

    # PNG text chunks (Stable Diffusion, ComfyUI) and other format-level info
    info = getattr(img, "text", None) or img.info or {}
    for k, v in info.items():
        if not isinstance(v, (str, bytes)):
            continue
        if k in GENERATOR_PNG_KEYS:
            out["png_generator_keys"].append(k)
        sv = v.decode(errors="ignore") if isinstance(v, bytes) else v
        if k.lower() in ("xmp", "xml:com.adobe.xmp"):
            # XMP holds lots of unrelated fields; only read the ones that name software.
            sv = " ".join(a or b for a, b in XMP_TOOL_FIELDS.findall(sv))
        hit = GENERATOR_WORDS.search(f"{k} {sv[:2000]}")
        if hit:
            out["text_hits"].append(hit.group(0))
    if out["software"]:
        hit = GENERATOR_WORDS.search(out["software"])
        if hit:
            out["text_hits"].append(hit.group(0))
    out["text_hits"] = sorted(set(h.lower() for h in out["text_hits"]))
    return out


def check(path):
    """Run every metadata check on one file and give a verdict.

    verdict:
      ai       - a label or tag says AI made it (near-certain, unless someone faked an AI label)
      real     - a valid signed label says it was captured by a camera, with no AI step
      none     - no metadata that says either way
    camera_hint is reported separately: camera details suggest a real photo but are easy to fake,
    so they never decide the verdict.
    """
    path = Path(path)
    c = read_c2pa(path)
    iptc = read_iptc_source_type(path)
    ex = read_exif_and_text(path)

    reasons = []
    verdict = "none"

    c2pa_ok = c and not c.get("error") and c.get("validation") in ("Valid", "Trusted")
    if c2pa_ok and AI_SOURCE_TYPES & set(c["source_types"]):
        verdict = "ai"
        reasons.append(f"signed label: {', '.join(sorted(AI_SOURCE_TYPES & set(c['source_types'])))} ({c['generator']})")
    elif AI_SOURCE_TYPES & set(iptc):
        verdict = "ai"
        reasons.append(f"IPTC tag: {', '.join(sorted(AI_SOURCE_TYPES & set(iptc)))}")
    elif ex["png_generator_keys"]:
        verdict = "ai"
        reasons.append(f"generator settings in file: {', '.join(ex['png_generator_keys'])}")
    elif ex["text_hits"]:
        verdict = "ai"
        reasons.append(f"generator named in metadata: {', '.join(ex['text_hits'])}")
    elif c2pa_ok and CAPTURE_SOURCE_TYPES & set(c["source_types"]):
        verdict = "real"
        reasons.append(f"signed label: captured ({c['generator']})")

    if c and not c2pa_ok:
        reasons.append(f"signed label present but not valid: {c.get('validation') or c.get('error')}")

    return {
        "file": str(path),
        "meta_verdict": verdict,
        "meta_reasons": "; ".join(reasons),
        "c2pa_present": bool(c and not c.get("error")),
        "c2pa_validation": (c or {}).get("validation"),
        "c2pa_generator": (c or {}).get("generator"),
        "c2pa_source_types": ",".join((c or {}).get("source_types", [])),
        "iptc_source_types": ",".join(iptc),
        "camera": ex["camera"],
        "software": ex["software"],
        "camera_hint": bool(ex["camera"]) and verdict == "none",
    }


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(json.dumps(check(p), indent=2))
