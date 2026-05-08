import sys
import json
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.__init__ import get_client, get_model

EXTRACTION_PROMPT = """You are a research paper analyst. Extract key information from the following paper text.

RULES:
- Only use information present in the provided text
- Do NOT hallucinate citations, data, or claims
- If a field cannot be determined, use "Not specified in provided text"
- Be concise but specific

Paper text:
---
{paper_text}
---

Extract the following fields as valid JSON:
{{
  "title": "paper title if available",
  "core_idea": "1-2 sentences on the main contribution",
  "methodology": "approach, techniques, model architecture, or experimental design",
  "dataset": "data used for experiments or evaluation",
  "key_results": ["result 1", "result 2", ...],
  "limitations": ["limitation 1", "limitation 2", ...],
  "novelty": "what is new or different compared to prior work",
  "contributions": ["contribution 1", "contribution 2", ...],
  "key_equations": ["equation description 1", ...],
  "pseudocode": "description of algorithm if relevant, otherwise 'Not applicable'",
  "assumptions": ["key assumption 1", ...],
  "executive_summary": "3-4 sentence overview for a researcher deciding whether to read the full paper"
}}

Return ONLY the JSON object, nothing else."""

MERGE_PROMPT = """You are merging multiple partial extractions from chunks of the SAME research paper.
Combine them into a single coherent structured summary.

RULES:
- Deduplicate and reconcile conflicting information (prefer more specific details)
- Do NOT hallucinate anything not present in the chunk summaries
- If a field cannot be determined from any chunk, use "Not specified in provided text"
- Keep key_results, limitations, assumptions, contributions, key_equations as arrays
- Return valid JSON only

Chunk summaries to merge:
---
{chunk_summaries}
---

Return the merged summary as this JSON structure (same fields as individual extractions):
{{
  "title": "paper title",
  "core_idea": "...",
  "methodology": "...",
  "dataset": "...",
  "key_results": ["...", ...],
  "limitations": ["...", ...],
  "novelty": "...",
  "contributions": ["...", ...],
  "key_equations": ["...", ...],
  "pseudocode": "...",
  "assumptions": ["...", ...],
  "executive_summary": "..."
}}

Return ONLY the JSON object."""


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


def summarize_single(text, model):
    prompt = EXTRACTION_PROMPT.format(paper_text=text)
    return extract_json(call_llm(prompt, model))


def summarize_chunks(chunks, model):
    chunk_summaries = []
    for chunk in chunks:
        prompt = EXTRACTION_PROMPT.format(paper_text=chunk)
        response = call_llm(prompt, model)
        try:
            chunk_summaries.append(extract_json(response))
        except json.JSONDecodeError:
            chunk_summaries.append({"raw_response": response})

    merged_text = json.dumps(chunk_summaries, indent=2)
    merge_prompt = MERGE_PROMPT.format(chunk_summaries=merged_text)
    return extract_json(call_llm(merge_prompt, model))


def summarize(text=None, chunks=None, model=None):
    model = model or get_model()

    if chunks:
        return summarize_chunks(chunks, model)

    if text:
        if len(text.split()) > 3000:
            from src.chunker import chunk_text
            return summarize_chunks(chunk_text(text), model)
        return summarize_single(text, model)

    raise ValueError("Provide either text or chunks")


def main():
    parser = argparse.ArgumentParser(description="Summarize research paper")
    parser.add_argument("--input", type=str, help="JSON with paper data (or use stdin)")
    parser.add_argument("--text", type=str, help="Raw paper text")
    parser.add_argument("--chunks", type=str, help="JSON array of text chunks")
    parser.add_argument("--model", type=str, default=None, help="Model override")
    args = parser.parse_args()

    model = args.model or get_model()

    if args.input:
        data = json.loads(args.input)
    elif not sys.stdin.isatty():
        data = json.loads(sys.stdin.read())
    else:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    if args.chunks:
        chunks = json.loads(args.chunks)
        result = summarize_chunks(chunks, model)
    elif args.text:
        result = summarize(text=args.text, model=model)
    elif "text" in data:
        result = summarize(text=data["text"], model=model)
    elif "chunks" in data:
        result = summarize(chunks=data["chunks"], model=model)
    else:
        print(json.dumps({"error": "No paper text or chunks provided"}))
        sys.exit(1)

    result["paper_id"] = data.get("paper_id", "unknown")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
