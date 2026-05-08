import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.__init__ import get_client, get_model


METADATA_PROMPT = """Extract metadata from the following research paper text.

Return ONLY valid JSON with these fields:
{{
  "title": "paper title",
  "authors": ["author 1", "author 2"],
  "year": "publication year",
  "venue": "conference or journal name",
  "abstract": "abstract text if available"
}}

Rules:
- Use "Not specified" for any field not found
- Return ONLY the JSON object

Paper text:
---
{text}
---"""


def extract_metadata(text: str, model: str = None) -> dict:
    client = get_client()
    model = model or get_model()

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": METADATA_PROMPT.format(text=text[:5000])}],
        temperature=0.0,
        max_tokens=8000,
    )

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        lines = [l for l in content.split("\n") if not l.startswith("```")]
        content = "\n".join(lines)

    return json.loads(content)


if __name__ == "__main__":
    import sys
    text = sys.stdin.read()
    meta = extract_metadata(text)
    print(json.dumps(meta, indent=2))
