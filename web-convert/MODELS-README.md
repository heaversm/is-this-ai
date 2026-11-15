---
license: other
tags: [onnx, image-classification, ai-image-detection]
---

# Browser-ready copies of four AI-image detectors

Half-precision ONNX versions of four free AI-image detectors, converted so they run in a web browser with onnxruntime-web. Used by "Is this image AI?", a personal research prototype by Mike Heavers: https://is-this-image-ai.netlify.app (code: https://github.com/heaversm/is-this-ai).

Each folder has `model_fp16.onnx` (input `pixel_values`, NCHW float32; output `p_ai`, the probability the image is AI) and `prep.json` with the preprocessing that must be matched.

| Folder | Original model | Licence of the original |
|---|---|---|
| `swinv2` | [haywoodsloan/ai-image-detector-deploy](https://huggingface.co/haywoodsloan/ai-image-detector-deploy) | Apache-2.0 |
| `siglip` | [Ateeqq/ai-vs-human-image-detector](https://huggingface.co/Ateeqq/ai-vs-human-image-detector) | Apache-2.0 |
| `sdxl` | [Organika/sdxl-detector](https://huggingface.co/Organika/sdxl-detector) | CC BY-NC 3.0 (non-commercial) |
| `commfor` | [OwensLab/commfor-model-384](https://huggingface.co/OwensLab/commfor-model-384) ([paper](https://arxiv.org/abs/2411.04125)) | MIT |

Checked against the original PyTorch models on 363 test images: no detector's verdict at the 95%-confidence line changed, except one borderline SwinV2 image (0.933 → 0.956). The licence of each original applies to its copy here.
