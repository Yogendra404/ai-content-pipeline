"""3-stage pipeline:  (1) research/outline  ->  (2) section-by-section draft  ->  (3) refine (+fact-check) -> guardrails."""
import json, re, time
from dataclasses import dataclass, asdict
from pathlib import Path
import guardrails as gr
import prompts as P
from llm import LLM

@dataclass
class Config:
    topic: str
    length: int = 1000                       # target words
    tone: str = "beginner-friendly"          # e.g. beginner-friendly | technical | casual | professional
    audience: str = "general readers"
    source_path: str = None                  # optional text file used for research + fact-checking
    provider: str = None
    model: str = None
    out_dir: str = "outputs"

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]

def _strip_fences(t):
    return re.sub(r"^```[a-z]*\n|\n```$", "", t.strip())

def _first_sentence(t):
    return re.split(r"(?<=[.!?])\s", t.strip())[0][:160]

# ---------------- Stage 1 ----------------
def make_outline(llm, cfg, source):
    n = max(3, min(7, round(cfg.length / 250)))
    sb = P.SOURCE_BLOCK.format(source=source[:12000]) if source else ""
    prompt = P.OUTLINE.format(topic=cfg.topic, tone=cfg.tone, audience=cfg.audience,
                              length=cfg.length, n=n, source_block=sb)
    for _ in range(3):
        raw = llm.generate(prompt, P.SYSTEM, "outline")
        try:
            data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            if len(data["sections"]) >= 3 and all(s.get("heading") for s in data["sections"]):
                return data
        except (ValueError, KeyError, json.JSONDecodeError):
            pass
    raise RuntimeError("Could not obtain a valid outline from the model")

def outline_text(o):
    parts = [o["title"], o.get("hook", "")]
    for s in o["sections"]:
        parts += [s["heading"]] + s.get("key_points", [])
    return "\n".join(parts + o.get("conclusion_points", []))

# ---------------- Stage 2 ----------------
def write_part(llm, cfg, outline, part, heading, points, words, covered, source):
    sb = P.SOURCE_BLOCK.format(source=source[:12000]) if source else ""
    prompt = P.SECTION.format(title=outline["title"], tone=cfg.tone, audience=cfg.audience, part=part,
                              heading=heading, points="\n".join(f"- {p}" for p in points),
                              words=words, covered="\n".join(covered) or "(nothing yet)", source_block=sb)
    return _strip_fences(llm.generate(prompt, P.SYSTEM, "section")).strip()

def make_draft(llm, cfg, outline, source):
    L, secs = cfg.length, outline["sections"]
    body_words = round(0.8 * L / len(secs))
    covered, out = [], [f"# {outline['title']}\n"]
    intro = write_part(llm, cfg, outline, "intro", "Introduction", [outline.get("hook", "")], round(0.1 * L), covered, source)
    out.append(intro + "\n"); covered.append(f"Intro: {_first_sentence(intro)}")
    for s in secs:
        text = write_part(llm, cfg, outline, "body", s["heading"], s.get("key_points", []), body_words, covered, source)
        out.append(f"## {s['heading']}\n\n{text}\n"); covered.append(f"{s['heading']}: {_first_sentence(text)}")
    concl = write_part(llm, cfg, outline, "conclusion", "Conclusion", outline.get("conclusion_points", []), round(0.1 * L), covered, source)
    out.append(f"## Conclusion\n\n{concl}\n")
    return "\n".join(out)

# ---------------- Stage 3 ----------------
def fact_check(llm, doc, source):
    raw = llm.generate(P.FACTCHECK.format(source=source[:12000], doc=doc), P.SYSTEM, "factcheck")
    if "===REVISED===" not in raw:
        return doc, ["(fact-check reply was malformed; draft kept unchanged)"]
    issues, revised = raw.split("===REVISED===", 1)
    issues = [l.strip("- ").strip() for l in issues.replace("ISSUES:", "").splitlines() if l.strip()]
    return _strip_fences(revised).strip() + "\n", issues

def edit(llm, cfg, doc, extra=""):
    return _strip_fences(llm.generate(P.EDIT.format(tone=cfg.tone, audience=cfg.audience, length=cfg.length,
                                                    extra=extra, doc=doc), P.SYSTEM, "edit")).strip() + "\n"

def refine(llm, cfg, draft, source):
    doc, issues = (fact_check(llm, draft, source) if source else (draft, []))
    return edit(llm, cfg, doc), issues

# ---------------- Orchestration ----------------
def run(cfg: Config):
    t0 = time.time()
    llm = LLM(cfg.provider, cfg.model)
    source = Path(cfg.source_path).read_text(encoding="utf-8") if cfg.source_path else ""
    out = Path(cfg.out_dir) / slug(cfg.topic); out.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Outline: {cfg.topic}")
    outline = make_outline(llm, cfg, source)
    otext = outline_text(outline)
    (out / "1_outline.json").write_text(json.dumps(outline, indent=2), encoding="utf-8")

    print(f"[2/3] Draft ({len(outline['sections']) + 2} parts)")
    draft = make_draft(llm, cfg, outline, source)
    (out / "2_draft.md").write_text(draft, encoding="utf-8")

    print("[3/3] Refine" + (" + fact-check" if source else ""))
    final, issues = refine(llm, cfg, draft, source)
    result = gr.check(final, otext, cfg.length)
    retries = 0
    while not result["passed"] and retries < 2:           # guardrail feedback loop
        retries += 1
        fails = gr.failures(result)
        print(f"   guardrails failed: {fails} -> retry {retries}")
        extra = ("A quality check failed: " + "; ".join(fails) + ". Fix these. If too short, expand with new "
                 "concrete detail (not repetition). If repetitive, rewrite the repeated parts.")
        final = edit(llm, cfg, final, extra)
        result = gr.check(final, otext, cfg.length)
    (out / "3_final.md").write_text(final, encoding="utf-8")

    report = {"config": asdict(cfg), "model": f"{llm.provider}/{llm.model}", "llm_calls": llm.calls,
              "seconds": round(time.time() - t0, 1), "fact_check_issues": issues, "guardrail_retries": retries,
              "draft_metrics": gr.metrics(draft), "final_metrics": result["metrics"],
              "draft_vs_final_similarity": round(gr.similarity(draft, final), 3),
              "draft_outline_overlap": round(gr.outline_overlap(otext, draft), 3),
              "guardrails": {"passed": result["passed"], "checks": result["checks"]}}
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"   done -> {out}  | guardrails passed: {result['passed']} | words: {result['metrics']['words']}")
    return report
