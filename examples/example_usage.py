"""
Example usage of the research pipeline.
Run with: python examples/example_usage.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetcher import fetch_pdf
from src.metadata import extract_metadata
from src.summarize import summarize
from src.synthesize import synthesize
from src.orchestrator.pipeline import run_pipeline
from src.orchestrator.agent import run_agent


PAPER_URLS = [
    "https://arxiv.org/pdf/2301.00234.pdf",
    "https://arxiv.org/pdf/2305.18290.pdf",
]


def mode_a_pipeline():
    """Sequential pipeline — no agentic reasoning."""
    print("=" * 60)
    print("Mode A: Simple Pipeline")
    print("=" * 60)
    result = run_pipeline(PAPER_URLS)
    print(json.dumps(result["synthesis"], indent=2)[:2000])


def mode_b_agent():
    """Agentic mode — LLM decides tool calling order."""
    print("=" * 60)
    print("Mode B: Agentic Orchestrator")
    print("=" * 60)
    result = run_agent(PAPER_URLS)
    print(json.dumps(result, indent=2)[:2000])


def manual_tools():
    """Call individual tools manually."""
    print("=" * 60)
    print("Manual tool usage")
    print("=" * 60)

    text = fetch_pdf(PAPER_URLS[0])
    print(f"Fetched {len(text.split())} words")

    meta = extract_metadata(text)
    print(f"Title: {meta.get('title')}")

    summary = summarize(text=text)
    print(f"Core idea: {summary.get('core_idea', '')[:120]}")

    synthesis = synthesize([summary, summary])
    print(f"Key insights: {synthesis.get('key_insights', [])}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "pipeline":
            mode_a_pipeline()
        elif mode == "agent":
            mode_b_agent()
        elif mode == "manual":
            manual_tools()
        else:
            print("Usage: python examples/example_usage.py [pipeline|agent|manual]")
    else:
        mode_a_pipeline()
