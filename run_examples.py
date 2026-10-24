"""Runs the pipeline on 3 different topics / tones / lengths and prints a comparison table."""
import argparse
from pipeline import Config, run

EXAMPLES = [
    Config("How HTTPS keeps your data safe", 900, "beginner-friendly", "non-technical internet users"),
    Config("Retrieval-Augmented Generation (RAG) explained for engineers", 1400, "technical",
           "software engineers new to LLM applications"),
    Config("Git branching strategies for small teams", 1000, "professional", "team leads and developers",
           source_path="sources/git_branching.txt"),
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider"); ap.add_argument("--model")
    a = ap.parse_args()
    rows = []
    for c in EXAMPLES:
        c.provider, c.model = a.provider, a.model
        rows.append((c, run(c)))
    print("\n| Topic | Target | Draft words | Final words | Repetition draft->final | Guardrails |")
    print("|---|---|---|---|---|---|")
    for c, r in rows:
        print(f"| {c.topic[:40]} | {c.length} | {r['draft_metrics']['words']} | {r['final_metrics']['words']} | "
              f"{r['draft_metrics']['repetition_ratio']} -> {r['final_metrics']['repetition_ratio']} | "
              f"{'PASS' if r['guardrails']['passed'] else 'FAIL'} |")
