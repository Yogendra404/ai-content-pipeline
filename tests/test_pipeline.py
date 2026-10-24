"""Offline tests of the plumbing using the mock provider (no API key needed). Run: pytest"""
import sys; sys.path.insert(0, ".")
import guardrails as gr
from pipeline import Config, run

def test_pipeline_runs_and_passes(tmp_path):
    rep = run(Config("Test topic", 800, provider="mock", out_dir=str(tmp_path)))
    assert rep["guardrails"]["passed"], rep["guardrails"]
    assert (tmp_path / "test-topic" / "3_final.md").exists()

def test_guardrails_catch_outline_echo():
    outline = "Title\nHeading one\npoint alpha beta gamma\nHeading two\npoint delta epsilon zeta"
    doc = "# Title\n\n## Heading one\n\npoint alpha beta gamma\n\n## Heading two\n\npoint delta epsilon zeta\n\n## Conclusion\n\nx"
    assert not gr.check(doc, outline, 800)["passed"]

def test_guardrails_catch_repetition_and_short():
    doc = "# T\n\n## H\n\n" + ("the same sentence repeated again and again here. " * 40)
    res = gr.check(doc, "outline", 2000)
    assert not res["checks"]["low_repetition (4-gram<=0.10, no duplicate sentences)"]
    assert not res["checks"]["min_length (>=80% of target)"]
