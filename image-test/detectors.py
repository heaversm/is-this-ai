"""Free AI-image detectors that guess from the pixels. Each returns p_ai, the
model's probability (0-1) that the image is AI-generated.

All run locally on the Mac (Apple GPU if available). Model weights download
from Hugging Face on first use, then are cached.

    .venv/bin/python detectors.py path/to/image.jpg
"""

import os
import sys
from pathlib import Path

# Hugging Face's newer "xet" downloader stalled on these models (Nov 2026); plain HTTP works.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import torch
from PIL import Image

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

# Ready-made detectors on Hugging Face. "ai_labels" lists which output labels mean AI.
PIPELINE_DETECTORS = {
    "ateeqq_siglip": ("Ateeqq/ai-vs-human-image-detector", {"ai"}),
    "haywoodsloan_swinv2": ("haywoodsloan/ai-image-detector-deploy", {"artificial"}),
    "organika_sdxl": ("Organika/sdxl-detector", {"artificial"}),
}
# Community Forensics (CVPR 2025): trained on images from thousands of generators,
# which is the main thing that helps a detector cope with generators it hasn't seen.
COMMFOR = "commfor_vit384"

ALL = list(PIPELINE_DETECTORS) + [COMMFOR]

_loaded = {}


def _load_pipeline(name):
    from transformers import pipeline
    repo, ai_labels = PIPELINE_DETECTORS[name]
    pipe = pipeline("image-classification", model=repo, device=DEVICE)
    return pipe, ai_labels


def _load_commfor():
    sys.path.insert(0, str(Path(__file__).parent / "vendor" / "commfor"))
    from models import ViTClassifier  # vendored from github.com/JeongsooP/Community-Forensics (MIT)
    from torchvision import transforms

    model = ViTClassifier.from_pretrained("OwensLab/commfor-model-384", device=DEVICE).to(DEVICE).eval()
    # Test-time preprocessing, copied from the repo's dataloader.get_transform(mode="test")
    tf = transforms.Compose([
        transforms.Resize(440),
        transforms.CenterCrop(384),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return model, tf


def p_ai(name, img):
    """Probability the image is AI-generated, according to detector `name`."""
    if name not in _loaded:
        _loaded[name] = _load_commfor() if name == COMMFOR else _load_pipeline(name)
    if name == COMMFOR:
        model, tf = _loaded[name]
        with torch.no_grad():
            x = tf(img).unsqueeze(0).to(DEVICE)
            return float(torch.sigmoid(model(x)).squeeze().cpu())
    pipe, ai_labels = _loaded[name]
    scores = pipe(img, top_k=None)
    return float(sum(s["score"] for s in scores if s["label"].lower() in ai_labels))


def open_image(path):
    img = Image.open(path)
    if getattr(img, "n_frames", 1) > 1:  # animated GIF/WebP: use the first frame
        img.seek(0)
    return img.convert("RGB")


def run_all(path, names=ALL):
    img = open_image(path)
    return {n: p_ai(n, img) for n in names}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, {k: round(v, 3) for k, v in run_all(p).items()})
