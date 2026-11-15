// Is this image AI? — everything runs in the visitor's browser.
// Models download once from Hugging Face, are kept in the browser's cache, and run
// with onnxruntime-web (WebGPU where available, otherwise WebAssembly).

import * as ort from "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.31.1/dist/ort.all.min.mjs";
import { resizeRGB, toTensor, RESAMPLE } from "./resize.js";
import { checkMetadata } from "./metadata.js";

ort.env.wasm.wasmPaths = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.31.1/dist/";

const params = new URLSearchParams(location.search);
const MODEL_BASE = params.get("models") || "https://huggingface.co/mikemoz/is-this-ai-models/resolve/main";
const CACHE = "is-this-ai-models-v1";
const LIKELY = 0.95;

// In-our-test context for each detector: on viral, fact-checked images, counting
// only answers where it was at least 95% sure. [right, total]
export const DETECTORS = [
  { k: "swinv2", name: "SwinV2", who: "haywoodsloan · Hugging Face", href: "https://huggingface.co/haywoodsloan/ai-image-detector-deploy",
    note: "Did best overall in our test. The verdict above uses this one.", mb: 393, ai: [9, 9], real: [60, 99] },
  { k: "siglip", name: "SigLIP", who: "Ateeqq · Hugging Face", href: "https://huggingface.co/Ateeqq/ai-vs-human-image-detector",
    note: "Catches more fakes, but often calls real photos AI.", mb: 172, ai: [28, 49], real: [37, 63] },
  { k: "sdxl", name: "SDXL detector", who: "Organika · Hugging Face", href: "https://huggingface.co/Organika/sdxl-detector",
    note: "Trained on Stable Diffusion XL images; weaker on others.", mb: 178, ai: [18, 30], real: [35, 60] },
  { k: "commfor", name: "Community Forensics", who: "CVPR 2025 research model", href: "https://arxiv.org/abs/2411.04125",
    note: "Trained on images from thousands of generators.", mb: 44, ai: [3, 3], real: [57, 100] },
];

const sessions = {}, preps = {};
let backend = null;

async function cachedFetch(url, onProgress) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(url);
  if (hit) { onProgress?.(1, 1, true); return hit.arrayBuffer(); }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Couldn't download ${url.split("/").slice(-2).join("/")} (HTTP ${res.status})`);
  const total = +res.headers.get("content-length") || 0;
  const reader = res.body.getReader(), parts = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value); got += value.length; onProgress?.(got, total, false);
  }
  const blob = new Blob(parts);
  try { await cache.put(url, new Response(blob, { headers: { "content-type": "application/octet-stream" } })); } catch { /* storage full: still works this visit */ }
  return blob.arrayBuffer();
}

export async function isCached(k) {
  const cache = await caches.open(CACHE);
  return !!(await cache.match(`${MODEL_BASE}/${k}/model_fp16.onnx`));
}

export async function loadDetector(k, onProgress) {
  if (sessions[k]) return;
  preps[k] = JSON.parse(new TextDecoder().decode(await cachedFetch(`${MODEL_BASE}/${k}/prep.json`)));
  const buf = await cachedFetch(`${MODEL_BASE}/${k}/model_fp16.onnx`, onProgress);
  onProgress?.(1, 1, "starting");
  const tryEps = backend ? [backend] : (navigator.gpu ? ["webgpu", "wasm"] : ["wasm"]);
  let lastErr;
  for (const ep of tryEps) {
    try { sessions[k] = await ort.InferenceSession.create(buf, { executionProviders: [ep] }); backend = ep; return; }
    catch (e) { lastErr = e; }
  }
  throw lastErr;
}

export const usingGpu = () => backend === "webgpu";

// Decode like the Python tool (PIL): apply camera rotation, but no colour-profile
// conversion. Browsers normally convert colour profiles, and that alone moved one
// detector score by 0.86 in testing.
export async function decode(file) {
  const bmp = await createImageBitmap(file, { colorSpaceConversion: "none", imageOrientation: "from-image", premultiplyAlpha: "none" });
  const c = new OffscreenCanvas(bmp.width, bmp.height), g = c.getContext("2d", { colorSpace: "srgb" });
  g.drawImage(bmp, 0, 0);
  return { w: bmp.width, h: bmp.height, rgba: g.getImageData(0, 0, bmp.width, bmp.height).data };
}

function prepare(img, p) {
  if (p.resize_exact) {
    const [h, w] = p.resize_exact;
    const rgb = resizeRGB(img.rgba, img.w, img.h, w, h, RESAMPLE[p.resample] || "bicubic");
    return { x: toTensor(rgb, w, h, p.mean, p.std, p.rescale), w, h };
  }
  // Community Forensics, with torchvision's rules: shortest side to 440 (long side
  // truncated), bilinear, then a centred 384 crop (offset rounded)
  const s = p.resize_short, c = p.crop;
  const [nw, nh] = img.w <= img.h ? [s, Math.trunc((s * img.h) / img.w)] : [Math.trunc((s * img.w) / img.h), s];
  const rgb = resizeRGB(img.rgba, img.w, img.h, nw, nh, "bilinear");
  const l = Math.round((nw - c) / 2), t = Math.round((nh - c) / 2), crop = new Uint8ClampedArray(c * c * 3);
  for (let y = 0; y < c; y++) crop.set(rgb.subarray(((t + y) * nw + l) * 3, ((t + y) * nw + l + c) * 3), y * c * 3);
  return { x: toTensor(crop, c, c, p.mean, p.std, 1 / 255), w: c, h: c };
}

// One model run at a time: overlapping runs on the same session can fail or hang
let queue = Promise.resolve();
export function score(k, img) {
  const job = queue.then(async () => {
    const { x, w, h } = prepare(img, preps[k]);
    const out = await sessions[k].run({ pixel_values: new ort.Tensor("float32", x, [1, 3, h, w]) });
    return out.p_ai.data[0];
  });
  queue = job.catch(() => {});
  return job;
}

export function verdict(meta, pSwin) {
  if (meta.verdict === "ai") return "confirmed_ai";
  if (meta.verdict === "real") return "confirmed_real";
  if (pSwin != null && pSwin >= LIKELY) return "likely_ai";
  return "dont_know";
}

export { checkMetadata };
