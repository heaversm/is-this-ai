// Image resizing that matches Python's PIL (Pillow) library, which the detectors
// were tested with. The browser's own canvas resizing gives slightly different
// pixels, and those differences moved some detector scores by up to 0.26.
//
// Port of Pillow's ImagingResample: separable convolution, horizontal pass then
// vertical, with the filter widened when shrinking (antialiasing) and each pass
// rounded to 8-bit, like Pillow does.

const FILTERS = {
  bicubic: { support: 2, f: (x) => {
    const a = -0.5; x = Math.abs(x);
    if (x < 1) return ((a + 2) * x - (a + 3)) * x * x + 1;
    if (x < 2) return (((x - 5) * x + 8) * x - 4) * a;
    return 0;
  } },
  bilinear: { support: 1, f: (x) => { x = Math.abs(x); return x < 1 ? 1 - x : 0; } },
};

function coeffs(inSize, outSize, filter) {
  const scale = inSize / outSize;
  const fscale = Math.max(scale, 1);
  const support = filter.support * fscale;
  const bounds = new Int32Array(outSize * 2);
  const ksize = Math.ceil(support) * 2 + 1;
  const k = new Float64Array(outSize * ksize);
  for (let i = 0; i < outSize; i++) {
    const center = (i + 0.5) * scale;
    let xmin = Math.trunc(center - support + 0.5); if (xmin < 0) xmin = 0;
    let xmax = Math.trunc(center + support + 0.5); if (xmax > inSize) xmax = inSize;
    xmax -= xmin;
    let ww = 0;
    for (let x = 0; x < xmax; x++) {
      const w = filter.f((x + xmin - center + 0.5) / fscale);
      k[i * ksize + x] = w; ww += w;
    }
    if (ww !== 0) for (let x = 0; x < xmax; x++) k[i * ksize + x] /= ww;
    bounds[i * 2] = xmin; bounds[i * 2 + 1] = xmax;
  }
  return { bounds, k, ksize };
}

const clip8 = (v) => (v <= 0 ? 0 : v >= 255 ? 255 : Math.round(v));

// rgba: Uint8ClampedArray (w*h*4) -> Uint8ClampedArray of RGB (ow*oh*3)
export function resizeRGB(rgba, w, h, ow, oh, kind = "bicubic") {
  const filter = FILTERS[kind];
  // horizontal pass: w x h -> ow x h
  const hc = coeffs(w, ow, filter);
  const tmp = new Uint8ClampedArray(ow * h * 3);
  for (let y = 0; y < h; y++) {
    for (let i = 0; i < ow; i++) {
      const xmin = hc.bounds[i * 2], n = hc.bounds[i * 2 + 1], kb = i * hc.ksize;
      let r = 0, g = 0, b = 0;
      for (let x = 0; x < n; x++) {
        const p = ((y * w) + xmin + x) * 4, c = hc.k[kb + x];
        r += rgba[p] * c; g += rgba[p + 1] * c; b += rgba[p + 2] * c;
      }
      const o = (y * ow + i) * 3; tmp[o] = clip8(r); tmp[o + 1] = clip8(g); tmp[o + 2] = clip8(b);
    }
  }
  // vertical pass: ow x h -> ow x oh
  const vc = coeffs(h, oh, filter);
  const out = new Uint8ClampedArray(ow * oh * 3);
  for (let j = 0; j < oh; j++) {
    const ymin = vc.bounds[j * 2], n = vc.bounds[j * 2 + 1], kb = j * vc.ksize;
    for (let i = 0; i < ow; i++) {
      let r = 0, g = 0, b = 0;
      for (let y = 0; y < n; y++) {
        const p = ((ymin + y) * ow + i) * 3, c = vc.k[kb + y];
        r += tmp[p] * c; g += tmp[p + 1] * c; b += tmp[p + 2] * c;
      }
      const o = (j * ow + i) * 3; out[o] = clip8(r); out[o + 1] = clip8(g); out[o + 2] = clip8(b);
    }
  }
  return out;
}

// Turn resized RGB into the normalized NCHW float32 tensor the models expect
export function toTensor(rgb, w, h, mean, std, scale = 1 / 255) {
  const n = w * h, x = new Float32Array(3 * n);
  for (let i = 0; i < n; i++) for (let k = 0; k < 3; k++) x[k * n + i] = (rgb[i * 3 + k] * scale - mean[k]) / std[k];
  return x;
}

// Pillow's resample codes, as saved in each model's prep.json
export const RESAMPLE = { 0: "nearest", 1: "lanczos", 2: "bilinear", 3: "bicubic" };
