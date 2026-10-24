import argparse, sys
from pipeline import Config, run

ap = argparse.ArgumentParser(description="AI content pipeline: topic -> outline -> draft -> refined blog post")
ap.add_argument("--topic", required=True)
ap.add_argument("--length", type=int, default=1000, help="target words")
ap.add_argument("--tone", default="beginner-friendly", help="beginner-friendly | technical | casual | professional ...")
ap.add_argument("--audience", default="general readers")
ap.add_argument("--source", default=None, help="text file for research + fact-checking")
ap.add_argument("--provider", default=None, help="gemini | openai | anthropic")
ap.add_argument("--model", default=None)
ap.add_argument("--out", default="outputs")
a = ap.parse_args()
rep = run(Config(a.topic, a.length, a.tone, a.audience, a.source, a.provider, a.model, a.out))
sys.exit(0 if rep["guardrails"]["passed"] else 2)
