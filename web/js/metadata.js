// Labels in the file: the same checks as the Python tool (check_metadata.py),
// run in the browser. Nothing leaves the visitor's machine.
//   - C2PA signed labels ("Content Credentials"), read and validated with c2pa-web
//   - the IPTC "made by AI" tag (DigitalSourceType) in the file's XMP text
//   - generator settings that Stable Diffusion / ComfyUI / Flux save in PNG text chunks
//   - generator names in software fields
// Camera details are reported but never decide the verdict: they're easy to fake.

import { createC2pa, Reader } from "../vendor/c2pa.js";
import exifr from "../vendor/exifr.mjs";

const AI_SOURCE_TYPES = new Set(["trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia", "algorithmicMedia"]);
const CAPTURE_SOURCE_TYPES = new Set(["digitalCapture", "negativeFilm", "positiveFilm", "print", "minorHumanEdits", "computationalCapture"]);
const GENERATOR_WORDS = /\b(?:midjourney|dall[-·\s]?e|openai|chatgpt|stable diffusion|sdxl|comfyui|automatic1111|invokeai|novelai|firefly|imagen|gemini|nano banana|flux|leonardo|ideogram|runway|sora|veo|kling)\b/i;
const GENERATOR_PNG_KEYS = new Set(["parameters", "prompt", "workflow", "invokeai_metadata", "sd-metadata", "Dream"]);
const SOURCE_TYPE_NAMES = {
  trainedAlgorithmicMedia: "made by generative AI",
  compositeWithTrainedAlgorithmicMedia: "a real image with AI-generated parts",
  algorithmicMedia: "made by an algorithm",
};

let c2paPromise = null;
function c2pa() {
  c2paPromise ??= createC2pa({ wasmSrc: new URL("../vendor/c2pa_bg.wasm", import.meta.url).href });
  return c2paPromise;
}

const lastPart = (u) => (u ? String(u).replace(/\/$/, "").split("/").pop() : null);

async function readC2pa(file) {
  try {
    const reader = await Reader.fromBlob(await c2pa(), file.type || undefined, file);
    if (!reader) return null;
    const store = await reader.manifestStore();
    const active = store.manifests?.[store.active_manifest] || {};
    let gen = active.claim_generator || "";
    if (!gen && Array.isArray(active.claim_generator_info))
      gen = active.claim_generator_info.map((i) => [i.name, i.version].filter(Boolean).join(" ")).join(", ");
    const types = new Set();
    for (const m of Object.values(store.manifests || {}))
      for (const a of m.assertions || [])
        if (String(a.label).startsWith("c2pa.actions"))
          for (const act of a.data?.actions || []) { const t = lastPart(act.digitalSourceType); if (t) types.add(t); }
    return { generator: gen, signer: active.signature_info?.issuer || active.signature_info?.common_name || "", validation: store.validation_state, types: [...types] };
  } catch (e) {
    return { error: String(e?.message || e) };
  }
}

function pngTextChunks(bytes) {
  const out = [];
  if (!(bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47)) return out;
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const dec = new TextDecoder("latin1");
  let p = 8;
  while (p + 8 <= bytes.length) {
    const len = dv.getUint32(p), type = dec.decode(bytes.subarray(p + 4, p + 8));
    if (["tEXt", "iTXt", "zTXt"].includes(type)) {
      const data = bytes.subarray(p + 8, p + 8 + len), z = data.indexOf(0);
      out.push({ key: dec.decode(data.subarray(0, z)), value: new TextDecoder("utf-8").decode(data.subarray(z + 1, Math.min(data.length, z + 4000))) });
    }
    if (type === "IEND") break;
    p += 12 + len;
  }
  return out;
}

export async function checkMetadata(file) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  const text = new TextDecoder("latin1").decode(bytes);
  const c = await readC2pa(file);
  const c2paOk = c && !c.error && (c.validation === "Valid" || c.validation === "Trusted");

  const iptc = new Set();
  for (const m of text.matchAll(/digitalsourcetype\/([A-Za-z]+)|DigitalSourceType["'>=\s]+([A-Za-z]+)/g)) iptc.add(m[1] || m[2]);

  let exif = {};
  try { exif = (await exifr.parse(file, { pick: ["Make", "Model", "Software"] })) || {}; } catch { /* no EXIF */ }
  const camera = [exif.Make, exif.Model].filter(Boolean).join(" ").trim() || null;

  const chunks = pngTextChunks(bytes);
  const pngKeys = chunks.filter((c) => GENERATOR_PNG_KEYS.has(c.key)).map((c) => c.key);
  const tools = [...text.matchAll(/(?:CreatorTool|softwareAgent|Software)\s*=\s*"([^"]*)"|<(?:xmp:CreatorTool|stEvt:softwareAgent|tiff:Software)>([^<]*)</gi)].map((m) => m[1] || m[2]);
  const hits = new Set();
  for (const s of [exif.Software, ...tools, ...chunks.map((c) => `${c.key} ${c.value}`)]) {
    const h = s && GENERATOR_WORDS.exec(s); if (h) hits.add(h[0].toLowerCase());
  }

  let verdict = "none", reason = "";
  const cAi = c2paOk ? c.types.filter((t) => AI_SOURCE_TYPES.has(t)) : [];
  const iAi = [...iptc].filter((t) => AI_SOURCE_TYPES.has(t));
  if (cAi.length) { verdict = "ai"; reason = `A valid signed label (Content Credentials) says it was ${SOURCE_TYPE_NAMES[cAi[0]]}${c.generator ? `, by ${c.generator}` : ""}.`; }
  else if (iAi.length) { verdict = "ai"; reason = `The file's standard "made by AI" tag says it was ${SOURCE_TYPE_NAMES[iAi[0]]}.`; }
  else if (pngKeys.length) { verdict = "ai"; reason = `The file contains the settings an AI image generator saves (${pngKeys.join(", ")}).`; }
  else if (hits.size) { verdict = "ai"; reason = `The file's metadata names an AI tool: ${[...hits].join(", ")}.`; }
  else if (c2paOk && c.types.some((t) => CAPTURE_SOURCE_TYPES.has(t))) { verdict = "real"; reason = `A valid signed label says it was captured by a camera${c.generator ? ` (${c.generator})` : ""}, with no AI step recorded.`; }

  return {
    verdict, reason, camera,
    c2pa: c && !c.error ? { validation: c.validation, generator: c.generator, types: c.types } : null,
    c2paInvalid: c && !c.error && !c2paOk ? c.validation || "unreadable" : null,
  };
}
