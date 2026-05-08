"""
Agentic orchestrator — uses OpenCode (big-pickle) to dynamically decide
which tool to call, when to chunk, summarize, and synthesize.
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.__init__ import get_client, get_model

# ---------------------------------------------------------------------------
# Tool implementations (called by the agent)
# ---------------------------------------------------------------------------
from src.fetcher import fetch_content as _fetch_content
from src.metadata import extract_metadata as _extract_metadata
from src.chunker import chunk_text as _chunk_text
from src.summarize import summarize as _summarize
from src.synthesize import synthesize as _synthesize


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_pdf",
            "description": "Download a PDF or webpage from a URL and extract its text content",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "PDF URL"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_metadata",
            "description": "Extract title, authors, year, venue from paper text",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Raw paper text"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "chunk",
            "description": "Split long text into overlapping chunks (use if text > ~150k tokens)",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Long text to split"},
                    "chunk_size": {"type": "integer", "description": "Target chunk size in words", "default": 3000},
                    "overlap": {"type": "integer", "description": "Overlap in words", "default": 500},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize",
            "description": "Extract structured JSON summary from paper text or chunk list",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Full paper text (if fits in context)"},
                    "chunks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of text chunks (if text was chunked)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize",
            "description": "Compare multiple paper summaries and produce cross-paper analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "papers": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of structured paper summaries",
                    },
                },
                "required": ["papers"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a research paper analysis agent.

You have 5 tools:

1. **fetch_pdf(url)** — Download a PDF or webpage and extract its text.
2. **extract_metadata(text)** — Extract title, authors, year, venue.
3. **chunk(text)** — Split very long text into overlapping chunks (only if text > ~150k tokens).
4. **summarize(text or chunks)** — Extract structured JSON summary.
5. **synthesize(papers)** — Compare multiple paper summaries.

**Rules:**
- Analyse papers one at a time: fetch -> extract_metadata -> summarize for each paper.
- Prefer whole-paper summarization. Only chunk if the text is very long.
- After ALL papers are summarized, call synthesize.
- When done, present the final output as a JSON object with keys: "papers", "synthesis".
- Minimise tool calls — do not re-fetch or re-summarize unnecessarily.
"""


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------
TOOL_REGISTRY = {
    "fetch_pdf": lambda **kw: _fetch_content(**kw),
    "extract_metadata": lambda **kw: _extract_metadata(**kw),
    "chunk": lambda **kw: _chunk_text(**kw),
    "summarize": lambda **kw: _summarize(**kw),
    "synthesize": lambda **kw: _synthesize(**kw),
}


def _execute_tool(name: str, args: dict):
    fn = TOOL_REGISTRY[name]
    result = fn(**args)
    return json.dumps(result, indent=2) if not isinstance(result, str) else result


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------
def run_agent(urls: list[str], model: str = None, max_steps: int = 30) -> dict:
    client = get_client()
    model = model or get_model()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyse these papers:\n" + "\n".join(f"- {u}" for u in urls)},
    ]

    paper_store = {}

    for step in range(max_steps):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.1,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            final = msg.content
            try:
                return json.loads(final)
            except (json.JSONDecodeError, TypeError):
                return {"result": final}

        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)

            # Inject stored paper text into summarize if needed
            if name == "summarize":
                if "chunks" in args and isinstance(args["chunks"], list):
                    pass
                elif "text" not in args or not args["text"]:
                    paper_id = args.get("paper_id", list(paper_store.keys())[-1] if paper_store else None)
                    if paper_id and paper_id in paper_store:
                        args["text"] = paper_store[paper_id]

            result_text = _execute_tool(name, args)

            # Save fetched text for later use
            if name == "fetch_pdf":
                key = args.get("url", f"paper_{len(paper_store)}")
                paper_store[key] = result_text
                paper_store[f"paper_{len(paper_store)}"] = result_text

            if name == "extract_metadata":
                try:
                    meta = json.loads(result_text)
                    print(f"  Metadata: {meta.get('title', '?')[:60]}", file=sys.stderr)
                except json.JSONDecodeError:
                    pass

            messages.append(msg)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text[:8000],
            })

    raise RuntimeError("Agent reached max steps without completing")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Research agent (agentic mode)")
    parser.add_argument("urls", nargs="+", help="PDF URLs to analyse")
    parser.add_argument("--model", type=str, default=None, help="Model override")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file")
    args = parser.parse_args()

    result = run_agent(args.urls, model=args.model)
    output = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
