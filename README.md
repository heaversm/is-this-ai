# Is this image AI?

An honest AI-image checker that runs entirely in your browser, and the tests behind it.

- **Try it:** https://is-this-image-ai.netlify.app
- **The findings:** https://is-this-image-ai.netlify.app/findings/
- **The models:** https://huggingface.co/mikemoz/is-this-ai-models

Drop in an image. The checker looks for proof inside the file (signed C2PA Content Credentials, the IPTC "made by AI" tag, settings that AI generators save), then runs a free AI detector on your own machine. You get **Confirmed AI**, **Likely AI**, or **Don't know**, and nothing is uploaded.

## What we found

**Images** (363 images, 123 of them viral and fact-checked):

- The best of four free detectors caught **9 of 59** viral AI fakes. It called 39 of them real.
- Labels in the file were certain when present, but no re-shared or viral image kept one.
- Google's invisible SynthID watermark survived sharing. Fact-checkers found it in 12 viral fakes that every detector missed.
- An honest display answers "don't know" for **93%** of viral images. "Likely AI" was right 98 of 103 times; "likely real" was wrong too often to show.

**AI answers' citations** (30 Perplexity answers, 86 cited claims):

- 0 of 50 cited links were dead or led to a homepage.
- A person reading the sources judged 7 of 25 claims only **partly** backed. The common problem was overreach, not fake sources.
- A local AI checker agreed with that person 24 of 25 times if "partly" counts as support, but only 19 of 25 on the strict question.

## What's here

| Folder | What it is |
|---|---|
| `web/` | The live site: the browser checker (`index.html`, `js/`) and the findings page (`findings/`). Static files; deploy as-is |
| `web-convert/` | Converts the four detectors to ONNX for the browser (`export.py`) and checks them against the originals on the test images (`verify.py`) |
| `image-test/` | The image test: label checks, the four detectors, Google's watermark via Gemini, collectors for the test images, a local drag-and-drop checker, and the results. See `image-test/README.md` |
| `citation-test/` | The citation test: Perplexity answers, claim splitting, source fetching, a local-model checker, a hand-labeling page, and the results |

The test images themselves aren't included, since they belong to their creators. `image-test/collect/` re-downloads them from Wikimedia Commons, and its CSV files list every source.

## Running it

- **The browser checker:** serve `web/` with any static server, for example `python3 -m http.server -d web`.
- **The image test:** Python 3.11. `cd image-test && pip install -r requirements.txt`, then follow `image-test/README.md`.
- **The citation test:** Python 3.11 plus [Ollama](https://ollama.com) with `qwen3:14b`. `cd citation-test && pip install -r requirements.txt`. Then run, in order: `collect_perplexity.py`, `claims.py`, `fetch_sources.py`, `judge.py`, `label_server.py`.

## What's weak

- 123 viral images from 8 fact-check outlets, mostly US and English-language. Fact-check verdicts were taken as the answer.
- The re-shared copies are simulations of Instagram, WhatsApp and screenshots, not real trips through those apps.
- The citation test covers one AI tool, one person's judgments, and 25 hand-checked claims. "Partly" is a judgment call.
- Detectors are a moving target: new generators arrive every few months.

## Licences

The code is MIT (see `LICENSE`). The detector models keep their original licences, listed in `web-convert/MODELS-README.md`. The SDXL detector's licence is non-commercial. `image-test/vendor/commfor/` is from [Community Forensics](https://github.com/JeongsooP/Community-Forensics) (MIT).

A personal research prototype by Mike Heavers. It can be wrong; its "don't know" is an honest answer, not a failure.
