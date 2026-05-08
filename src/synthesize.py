import sys
import json
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.__init__ import get_client, get_model

SYNTHESIS_PROMPT = """You are a senior research analyst. You have summaries of {num_papers} papers on the same or related topic.
Produce a cross-paper synthesis that helps a researcher understand the landscape.

RULES:
- Only use information present in the provided summaries
- Do NOT hallucinate citations, claims, or data
- Be specific: reference which paper says what
- Be concise but thorough

Paper summaries:
---
{paper_summaries}
---

Produce the following analysis as valid JSON:
{{
  "cross_paper_comparison": {{
    "similarities": ["finding shared by papers X and Y: ...", ...],
    "differences": ["paper X does ... while paper Y does ...", ...],
    "contradictions": ["paper X claims ... but paper Y found ...", ...],
    "methodology_comparison": "how approaches differ across papers",
    "dataset_comparison": "how datasets differ across papers"
  }},
  "key_insights": ["insight 1", "insight 2", ...],
  "novelty_analysis": [
    {{"paper": "paper title or identifier", "novel_contribution": "what this paper adds that others don't"}},
    ...
  ],
  "novelty_map": "which papers share similar novelties and where the true breakthroughs lie",
  "usefulness_ranking": [
    {{"rank": 1, "paper": "paper title or identifier", "reason": "why this is most useful for the researcher"}},
    ...
  ],
  "recommended_reading_order": ["paper 1", "paper 2", ...],
  "gaps_and_future_work": ["research gap identified across papers", ...],
  "practical_takeaways": ["actionable insight 1", "actionable insight 2", ...],
  "executive_synthesis": "2-3 paragraph synthesis summarizing the state of research across all papers, key takeaways, and which paper(s) to prioritize"
}}

Return ONLY the JSON object, nothing else."""


def call_llm(prompt, model):
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=12000,
    )
    return response.choices[0].message.content


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def synthesize(papers, model=None):
    model = model or get_model()

    if not isinstance(papers, list):
        papers = [papers]

    summaries_text = ""
    for i, paper in enumerate(papers):
        summaries_text += f"\n\n=== PAPER {i+1} ===\n"
        summaries_text += json.dumps(paper, indent=2)
        summaries_text += "\n"

    prompt = SYNTHESIS_PROMPT.format(
        num_papers=len(papers),
        paper_summaries=summaries_text,
    )

    response = call_llm(prompt, model)
    synthesis = extract_json(response)
    synthesis["num_papers_analyzed"] = len(papers)
    return synthesis


def main():
    parser = argparse.ArgumentParser(description="Cross-paper synthesis")
    parser.add_argument("--input", type=str, help="JSON file with paper summaries (or use stdin)")
    parser.add_argument("--model", type=str, default=None, help="Model override")
    args = parser.parse_args()

    model = args.model or get_model()

    if args.input:
        with open(args.input) as f:
            papers = json.load(f)
    elif not sys.stdin.isatty():
        papers = json.loads(sys.stdin.read())
    else:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    result = synthesize(papers, model)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
