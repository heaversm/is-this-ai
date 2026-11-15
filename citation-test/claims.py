"""Split each saved answer into claims, each with the sources cited right after it.

A claim is the text since the previous citation in the same paragraph or bullet.
Sentences with no citation at all are counted, so the report can say how much of
each answer is cited.

    .venv/bin/python claims.py      ->  data/claims.jsonl
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
LINK = re.compile(r"\[([^\]]{1,80})\]\((https?://[^)\s]+)\)")
GROUP = re.compile(r"(?:\s*\[[^\]]{1,80}\]\(https?://[^)\s]+\))+")


def clean(t):
    t = re.sub(r"[*_`#>]+", "", t)          # markdown emphasis, headings
    t = re.sub(r"^\s*[-•\d.)]+\s+", "", t)   # bullet or number at line start
    return re.sub(r"\s+", " ", t).strip(" :;-")


def sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t) if len(s.split()) >= 4]


def parse(md):
    claims, uncited = [], 0
    for block in re.split(r"\n\s*\n|\n(?=\s*[-•]|\s*\d+[.)]\s)", md):
        if not block.strip() or block.lstrip().startswith("<!--"):
            continue
        pos = 0
        for g in GROUP.finditer(block):
            text = clean(block[pos:g.start()])
            urls = list(dict.fromkeys(u for _, u in LINK.findall(g.group(0))))
            if len(text.split()) >= 4:
                claims.append({"claim": text, "urls": urls})
            pos = g.end()
        rest = clean(block[pos:])
        if not rest.startswith("|"):  # skip markdown tables
            uncited += len(sentences(rest))
    return claims, uncited


def main():
    out = HERE / "data" / "claims.jsonl"
    out.parent.mkdir(exist_ok=True)
    rows, summary = [], []
    for tool_dir in sorted((HERE / "answers").iterdir()):
        for f in sorted(tool_dir.glob("*.md")):
            text = f.read_text()
            meta = json.loads(re.match(r"<!--meta (.*?) -->", text).group(1))
            claims, uncited = parse(text.split("-->", 1)[1])
            for i, c in enumerate(claims):
                rows.append({"tool": tool_dir.name, "qid": f.stem, "question": meta["question"], "cid": f"{tool_dir.name}-{f.stem}-{i:02d}", **c})
            summary.append({"tool": tool_dir.name, "qid": f.stem, "claims": len(claims), "uncited_sentences": uncited})
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (HERE / "data" / "answers_summary.json").write_text(json.dumps(summary, indent=1))
    print(f"{len(rows)} cited claims from {len(summary)} answers; {sum(s['uncited_sentences'] for s in summary)} uncited sentences")


if __name__ == "__main__":
    main()
