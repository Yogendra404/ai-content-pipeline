"""Thin provider-agnostic LLM client (plain REST, no SDKs). Providers: gemini, openai, anthropic, mock."""
import os, re, time, random
import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODELS = {"gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini",
                  "anthropic": "claude-sonnet-5-5", "mock": "mock"}

class LLM:
    def __init__(self, provider=None, model=None, temperature=0.7):
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[self.provider]
        self.temperature = temperature
        self.calls = 0

    def generate(self, prompt, system="", stage="", max_tokens=4096):
        self.calls += 1
        if self.provider == "mock":
            return _mock(prompt, stage)
        last = None
        for attempt in range(4):                      # retry with backoff (rate limits etc.)
            try:
                return getattr(self, f"_{self.provider}")(prompt, system, max_tokens)
            except Exception as e:
                last = e
                time.sleep(2 ** attempt * 2)
        raise RuntimeError(f"LLM call failed after retries: {last}")

    def _gemini(self, prompt, system, max_tokens):
        key = os.environ["GEMINI_API_KEY"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": self.temperature, "maxOutputTokens": max_tokens}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        r = requests.post(url, params={"key": key}, json=body, timeout=120)
        r.raise_for_status()
        return "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])

    def _openai(self, prompt, system, max_tokens):
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                          json={"model": self.model, "temperature": self.temperature,
                                "max_tokens": max_tokens,
                                "messages": [{"role": "system", "content": system},
                                             {"role": "user", "content": prompt}]}, timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _anthropic(self, prompt, system, max_tokens):
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                   "anthropic-version": "2023-06-01"},
                          json={"model": self.model, "max_tokens": max_tokens,
                                "temperature": self.temperature, "system": system,
                                "messages": [{"role": "user", "content": prompt}]}, timeout=120)
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"])


# ---------- offline mock, ONLY for unit-testing the plumbing (never used for the submitted posts) ----------
def _mock(prompt, stage):
    rnd = random.Random(len(prompt))
    def para(n):
        return " ".join("".join(rnd.choice("abcdefghijklmnoprstuv") for _ in range(rnd.randint(3, 9))) for _ in range(n)) + "."
    if stage == "outline":
        n = int(re.search(r"NUM_SECTIONS: (\d+)", prompt).group(1))
        import json
        return json.dumps({"title": "Mock Title", "hook": "hook",
                           "sections": [{"heading": f"Section {i+1} topic", "key_points": [f"pt{i}a", f"pt{i}b"]} for i in range(n)],
                           "conclusion_points": ["wrap"]})
    if stage == "section":
        words = int(re.search(r"TARGET_WORDS: (\d+)", prompt).group(1))
        return "\n\n".join(para(70) for _ in range(max(1, round(words / 70))))
    m = re.search(r"<<<DOCUMENT>>>\n(.*?)\n<<<END>>>", prompt, re.S)
    doc = m.group(1) if m else ""
    return "ISSUES:\n- none\n===REVISED===\n" + doc if stage == "factcheck" else doc
