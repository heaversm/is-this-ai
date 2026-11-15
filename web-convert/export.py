"""Convert the four detectors to ONNX so they can run in a browser, plus smaller
float16 and int8 copies, and save each model's preprocessing settings.

    .venv/bin/python export.py            -> out/<name>/{model.onnx, model_fp16.onnx, model_int8.onnx, prep.json}
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

HERE = Path(__file__).parent
OUT = HERE / "out"
PROV = HERE.parent / "image-test"  # this repo's image test (images/ must be collected first)

HF_MODELS = {
    "swinv2": ("haywoodsloan/ai-image-detector-deploy", {"artificial"}),
    "siglip": ("Ateeqq/ai-vs-human-image-detector", {"ai"}),
    "sdxl": ("Organika/sdxl-detector", {"artificial"}),
}


class Wrap(torch.nn.Module):
    """Output one number: the probability the image is AI."""
    def __init__(self, m, ai_index=None, sigmoid=False):
        super().__init__(); self.m, self.ai, self.sig = m, ai_index, sigmoid
    def forward(self, x):
        out = self.m(x)
        logits = out.logits if hasattr(out, "logits") else out
        if self.sig:
            return torch.sigmoid(logits).reshape(-1)
        return torch.softmax(logits, dim=-1)[:, self.ai]


class Half(torch.nn.Module):
    """Half-precision weights inside, ordinary float32 in and out."""
    def __init__(self, m):
        super().__init__(); self.m = m.half()
    def forward(self, x):
        return self.m(x.half()).float()


def shrink(path):
    from onnxruntime.quantization import quantize_dynamic, QuantType
    quantize_dynamic(str(path), str(path.with_name("model_int8.onnx")), weight_type=QuantType.QInt8)


def export(name, model, size, prep):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    x = torch.rand(1, 3, size["h"], size["w"])
    torch.onnx.export(model.eval(), x, str(d / "model.onnx"), input_names=["pixel_values"], output_names=["p_ai"],
                      opset_version=17, dynamic_axes={"pixel_values": {0: "batch"}, "p_ai": {0: "batch"}}, dynamo=False)
    (d / "prep.json").write_text(json.dumps(prep, indent=1))
    shrink(d / "model.onnx")
    # Half precision exported straight from the model (converting the finished file broke SwinV2)
    import copy
    torch.onnx.export(Half(copy.deepcopy(model)).eval(), x, str(d / "model_fp16.onnx"), input_names=["pixel_values"], output_names=["p_ai"],
                      opset_version=17, dynamic_axes={"pixel_values": {0: "batch"}, "p_ai": {0: "batch"}}, dynamo=False)
    print(name, {f.name: f"{f.stat().st_size / 1e6:.0f} MB" for f in sorted(d.glob('*.onnx'))})


def main():
    only = sys.argv[1:] or [*HF_MODELS, "commfor"]
    for name in only:
        if name == "commfor":
            sys.path.insert(0, str(PROV / "vendor" / "commfor"))
            from models import ViTClassifier
            m = ViTClassifier.from_pretrained("OwensLab/commfor-model-384", device="cpu")
            prep = {"resize_short": 440, "crop": 384, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225], "resample": "bilinear"}
            export(name, Wrap(m, sigmoid=True), {"h": 384, "w": 384}, prep)
            continue
        repo, ai_labels = HF_MODELS[name]
        m = AutoModelForImageClassification.from_pretrained(repo)
        pp = AutoImageProcessor.from_pretrained(repo)
        ai = [i for i, l in m.config.id2label.items() if l.lower() in ai_labels][0]
        size = pp.size
        h = size.get("height") or size.get("shortest_edge"); w = size.get("width") or size.get("shortest_edge")
        prep = {"resize_exact": [h, w], "mean": list(pp.image_mean), "std": list(pp.image_std),
                "rescale": float(pp.rescale_factor), "resample": int(getattr(pp, "resample", 3) or 3),
                "do_center_crop": bool(getattr(pp, "do_center_crop", False)), "source": repo}
        export(name, Wrap(m, ai_index=int(ai)), {"h": h, "w": w}, prep)


if __name__ == "__main__":
    main()
