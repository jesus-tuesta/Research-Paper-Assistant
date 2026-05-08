import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.fetcher import fetch_content
from src.metadata import extract_metadata
from src.chunker import chunk_text
from src.summarize import summarize
from src.synthesize import synthesize


def run_pipeline(urls, chunk_if_longer_than=3000, model=None):
    """Simple sequential pipeline: fetch -> metadata -> chunk? -> summarize -> synthesize."""

    paper_summaries = []
    failed = []

    for i, url in enumerate(urls):
        print(f"[{i+1}/{len(urls)}] Fetching: {url}", file=sys.stderr)
        try:
            text = fetch_content(url)
        except Exception as e:
            print(f"  !! FAILED: {e}", file=sys.stderr)
            failed.append({"url": url, "error": str(e)})
            continue

        print(f"  -> extracted {len(text.split())} words", file=sys.stderr)

        try:
            meta = extract_metadata(text, model=model)
        except Exception as e:
            print(f"  !! metadata extraction failed: {e}", file=sys.stderr)
            meta = {}

        print(f"  -> title: {meta.get('title', '?')[:60]}", file=sys.stderr)

        try:
            result = summarize(text=text, model=model)
        except Exception as e:
            print(f"  !! summarization failed: {e}", file=sys.stderr)
            result = {"core_idea": "", "executive_summary": ""}

        result["url"] = url
        result["metadata"] = meta
        paper_summaries.append(result)
        print(f"  -> summarized OK", file=sys.stderr)

    print(f"\nSynthesizing {len(paper_summaries)} papers...", file=sys.stderr)
    synthesis = synthesize(paper_summaries, model=model) if paper_summaries else {}

    return {
        "papers": paper_summaries,
        "synthesis": synthesis,
        "failed": failed,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Research pipeline (sequential)")
    parser.add_argument("urls", nargs="+", help="PDF URLs to analyze")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file")
    args = parser.parse_args()

    result = run_pipeline(args.urls)
    output = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)
