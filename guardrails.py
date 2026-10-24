"""Quality guardrails + simple text metrics."""
import re
from collections import Counter

BANNED = re.compile(r"(as an ai|language model|here is the|here's the|\bTODO\b|lorem ipsum|\[insert|\[\.\.\.\])", re.I)

def words(t):
    return re.findall(r"[A-Za-z0-9']+", t.lower())

def word_count(t):
    return len(words(t))

def repetition_ratio(text, n=4):
    """Share of 4-grams that are repeats. Normal prose is ~0.01-0.06."""
    w = words(text)
    grams = [tuple(w[i:i + n]) for i in range(len(w) - n + 1)]
    if not grams:
        return 0.0
    c = Counter(grams)
    return sum(v - 1 for v in c.values() if v > 1) / len(grams)

def repeated_sentences(text):
    sents = [" ".join(words(s)) for s in re.split(r"(?<=[.!?])\s+", re.sub(r"#+ .*", "", text)) if len(words(s)) > 5]
    return sum(v - 1 for v in Counter(sents).values() if v > 1)

def shingles(text, n=3):
    w = words(text)
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}

def outline_overlap(outline_text, doc):
    """Fraction of outline 3-grams that appear verbatim in the doc (high => doc just echoes outline)."""
    o = shingles(outline_text)
    return len(o & shingles(doc)) / len(o) if o else 0.0

def paragraphs(doc):
    return [b.strip() for b in re.split(r"\n\s*\n", doc) if b.strip() and not b.strip().startswith("#")]

def similarity(a, b):
    sa, sb = shingles(a), shingles(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0

def metrics(doc):
    paras = paragraphs(doc)
    sents = [s for s in re.split(r"(?<=[.!?])\s+", doc) if s.strip()]
    return {"words": word_count(doc),
            "headings": len(re.findall(r"^##\s", doc, re.M)),
            "paragraphs": len(paras),
            "avg_paragraph_words": round(sum(map(word_count, paras)) / max(1, len(paras)), 1),
            "max_paragraph_words": max(map(word_count, paras), default=0),
            "avg_sentence_words": round(word_count(doc) / max(1, len(sents)), 1),
            "repetition_ratio": round(repetition_ratio(doc), 4),
            "repeated_sentences": repeated_sentences(doc)}

def check(doc, outline_text, target):
    m = metrics(doc)
    ov = outline_overlap(outline_text, doc)
    ow = max(1, word_count(outline_text))
    checks = {
        "min_length (>=80% of target)": m["words"] >= 0.8 * target,
        "max_length (<=140% of target)": m["words"] <= 1.4 * target,
        "structure (title + >=3 '##' headings)": doc.lstrip().startswith("# ") and m["headings"] >= 3,
        "paragraphs (avg>=25, max<=180 words)": m["avg_paragraph_words"] >= 25 and m["max_paragraph_words"] <= 180,
        "not_outline_copy (overlap<0.5, >=3x outline)": ov < 0.5 and m["words"] >= 3 * ow,
        "low_repetition (4-gram<=0.10, no duplicate sentences)": m["repetition_ratio"] <= 0.10 and m["repeated_sentences"] == 0,
        "clean_output (no AI boilerplate/placeholders)": not BANNED.search(doc),
    }
    return {"passed": all(checks.values()), "checks": checks, "outline_overlap": round(ov, 3), "metrics": m}

def failures(result):
    return [k for k, v in result["checks"].items() if not v]
