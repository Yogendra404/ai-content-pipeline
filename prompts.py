SYSTEM = ("You are a senior editor and writer who produces publishable blog posts. Write clearly and "
          "concretely. Never invent statistics, quotes, studies or sources. Never mention being an AI. "
          "Follow the requested tone and audience exactly.")

SOURCE_BLOCK = "\nRESEARCH_MATERIAL (treat as ground truth; do not contradict it):\n\"\"\"\n{source}\n\"\"\"\n"

OUTLINE = """Plan a blog post.
TOPIC: {topic}
TONE: {tone}
AUDIENCE: {audience}
TARGET_WORDS: {length}
NUM_SECTIONS: {n}
{source_block}
Return ONLY valid JSON (no code fences) with this shape:
{{"title": "...", "hook": "one-sentence angle for the introduction",
 "sections": [{{"heading": "...", "key_points": ["...", "..."]}}],
 "conclusion_points": ["..."]}}
Rules: exactly NUM_SECTIONS body sections; headings must be specific (never "Introduction" or "Conclusion");
2-4 distinct key_points per section; sections must not overlap; order them from fundamentals to practical use.
If research material is given, base the key points on it."""

SECTION = """Write one part of a blog post.
TITLE: {title}
TONE: {tone}
AUDIENCE: {audience}
PART: {part}
HEADING: {heading}
KEY_POINTS:
{points}
TARGET_WORDS: {words}
ALREADY_COVERED (do not repeat these ideas):
{covered}
{source_block}
Rules: output ONLY the prose - no heading, no title. Paragraphs of 50-110 words separated by blank lines.
Be concrete (examples, analogies, specifics). Do not repeat earlier points. Avoid bullet lists unless essential.
For PART=intro open with a hook and tell the reader what they will learn. For PART=conclusion give a clear
takeaway and next step without introducing new facts."""

FACTCHECK = """Fact-check the blog post draft against the source material.
SOURCE:
\"\"\"
{source}
\"\"\"
<<<DOCUMENT>>>
{doc}
<<<END>>>
Find statements in the draft that contradict the source, or specific facts/numbers that the source does not
support and that are risky. Fix them (correct, hedge or remove). Keep headings, structure and length.
Reply in EXACTLY this format:
ISSUES:
- one line per issue found and how you fixed it (or "- none")
===REVISED===
<the full corrected markdown post>"""

EDIT = """Edit the blog post below as a meticulous editor.
TONE: {tone}   AUDIENCE: {audience}   TARGET_WORDS: about {length}
{extra}
<<<DOCUMENT>>>
{doc}
<<<END>>>
Do all of this: remove repeated ideas and repeated phrasing across sections; improve transitions between
sections; vary sentence openings; cut filler and cliches; keep every heading; keep paragraphs 50-110 words;
do not invent statistics or sources (remove any specific number you cannot justify). Stay within +/-10% of
the target length. Output ONLY the full edited markdown post."""
