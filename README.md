# Research Paper Agent

A fully Python-native research-paper assistant using **OpenCode (big-pickle)** as the reasoning engine. Fetches papers from PDF URLs, webpages, or local files — extracts metadata, generates structured summaries, synthesizes cross-paper insights, and produces Word reports.

No n8n. No visual workflows. Everything in Python.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│              CLI / Script                     │
│  pipeline.py │ agent.py │ report.py          │
└──────┬───────────────────────┬───────────────┘
       │                       │
       ▼                       ▼
┌──────────────┐   ┌──────────────────────┐
│   Pipeline   │   │  FastAPI Server      │
│  (sequential)│   │  /fetch-content      │
│              │   │  /extract-metadata   │
│              │   │  /summarize          │
│              │   │  /synthesize         │
│              │   │  /run  /report       │
│              │   │  /health             │
└──────┬───────┘   └──────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│              Tool Modules                    │
│  fetcher.py │ metadata.py │ chunker.py       │
│  summarize.py │ synthesize.py │ arxiv_search │
└──────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│           OpenCode Zen API (big-pickle)       │
│         (LLM calls for all reasoning)         │
└──────────────────────────────────────────────┘
```

---

## Features

- **Auto-detect input type** — PDF URLs, webpage URLs, or local files (.pdf / .html / .txt) — all handled transparently
- **Graceful error handling** — failed URLs are logged and skipped; the pipeline finishes and the report still generates
- **Structured summaries** — each paper gets a 12-field JSON summary (core idea, methodology, results, limitations, novelty, etc.)
- **Cross-paper synthesis** — compares similarities, differences, contradictions across papers; ranks usefulness; recommends reading order
- **Word report generation** — full `.docx` report with executive summary, per-paper sections, deep-dive recommendations table, and suggested further reading
- **arXiv search** — automatically finds related papers based on the synthesis
- **Web scraping** — uses `trafilatura` to extract main content from any webpage (not just PDFs)
- **Two orchestrator modes** — simple sequential pipeline or agentic function-calling loop
- **FastAPI server** — exposes everything as REST endpoints

---

## Project Structure

```
├── pyproject.toml              # Poetry project config
├── papers.txt                  # Sample input (one URL per line)
├── README.md                   # ← you are here
├── .env                        # API keys (OPENAI_API_KEY, etc.)
├── src/
│   ├── __init__.py             # LLM client config (get_client, get_model)
│   ├── server.py               # FastAPI exposing all tools + /report
│   ├── fetcher.py              # PDF download + webpage scrape + local file
│   ├── metadata.py             # Title/authors/year/venue extraction
│   ├── chunker.py              # Text chunking with overlap
│   ├── summarize.py            # Per-paper structured summarization
│   ├── synthesize.py           # Cross-paper comparison + synthesis
│   ├── arxiv_search.py         # arXiv API search for related papers
│   ├── report.py               # Word document report generator
│   └── orchestrator/
│       ├── pipeline.py         # Sequential pipeline (fetch → metadata → summarize → synthesize)
│       └── agent.py            # Agentic loop (LLM decides tool order via function calling)
├── configs/
│   └── default.json
├── examples/
│   └── example_usage.py
└── tests/
    └── test_tools.py
```

---

## Quick Start

### 1. Install dependencies

```bash
# Install Poetry (if not already)
pip install poetry

# Install all dependencies
poetry install

# Activate the virtual environment
poetry shell
```

Also install **poppler-utils** for PDF text extraction (PyMuPDF is the fallback):

```bash
# Ubuntu/Debian
sudo apt install poppler-utils

# macOS
brew install poppler

# Windows (via Scoop)
scoop install poppler
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your OpenCode Zen API key:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://opencode.ai/zen/v1/chat/completions
OPENAI_MODEL=big-pickle
```

> **Note:** The model `big-pickle` is a reasoning model that needs ample `max_tokens`. The tool modules use generous budgets (metadata: 8000, summarize: 12000, synthesize: 12000). If you use a different model, adjust accordingly in each module.

### 3. Run a pipeline

```bash
# One paper (PDF URL)
poetry run python src/orchestrator/pipeline.py https://arxiv.org/pdf/2301.00234.pdf

# Multiple papers — mixed PDFs, webpages, local files
poetry run python src/orchestrator/pipeline.py \
    https://arxiv.org/pdf/2301.00234.pdf \
    https://arxiv.org/abs/2310.06825 \
    /path/to/local_paper.pdf

# Save output to file
poetry run python src/orchestrator/pipeline.py \
    https://arxiv.org/pdf/2301.00234.pdf \
    --output results.json
```

### 4. Generate a Word report

```bash
# From a file with one URL per line
poetry run python src/report.py papers.txt -o report.docx

# With arXiv search for related papers
poetry run python src/report.py papers.txt -o report.docx -s "in-context learning"

# Pipe URLs directly
echo "https://arxiv.org/pdf/2301.00234.pdf" | poetry run python src/report.py /dev/stdin -o report.docx
```

Sample `papers.txt`:

```
# arXiv PDF
https://arxiv.org/pdf/2301.00234.pdf
# arXiv abstract page (auto-detected as webpage)
https://arxiv.org/abs/2310.06825
# Local file (downloaded PDF or HTML)
/home/me/papers/my_paper.pdf
/home/me/papers/saved_article.html
```

### 5. Start the API server

```bash
poetry run python src/server.py --port 8000

# In another terminal:
curl http://localhost:8000/health

# Fetch content (auto-detects PDF vs webpage)
curl -X POST http://localhost:8000/fetch-content \
  -H "Content-Type: application/json" \
  -d '{"url_or_path": "https://arxiv.org/pdf/2301.00234.pdf"}'

# Run full pipeline
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://arxiv.org/pdf/2301.00234.pdf"]}'

# Download a Word report
curl -o review.docx -X POST http://localhost:8000/report \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://arxiv.org/pdf/2301.00234.pdf"]}'
```

---

## Input Auto-Detection

| Input | Detection | Handler |
|---|---|---|
| `https://...pdf` | starts with `http`, ends `.pdf` | `fetch_pdf()` — download + extract |
| `https://...` | starts with `http`, not `.pdf` | HEAD check → PDF or `scrape_webpage()` via trafilatura |
| `/path/to/file.pdf` | local path, `.pdf` | `_extract_pdf_file()` — pdftotext / PyMuPDF |
| `/path/to/file.html` | local path, `.html`/`.htm` | trafilatura on file content |
| `/path/to/file.txt` | local path, anything else | raw text read |

For blocked/scraping-prohibited sites, download the page first and pass the local path instead.

---

## Orchestrator Modes

| Mode | File | Description |
|---|---|---|
| **Pipeline** | `src/orchestrator/pipeline.py` | Sequential: fetch → metadata → summarize → synthesize. Best for batch processing. |
| **Agentic** | `src/orchestrator/agent.py` | LLM (big-pickle) uses function calling to decide tool order dynamically. More flexible, more LLM calls. |
| **API** | `src/server.py` | FastAPI server exposing all tools as REST endpoints. |

### Pipeline mode (default)
Simple, predictable, efficient. Processes papers one by one, merges everything at the end.

### Agentic mode
The LLM itself decides which tool to call next — it could re-fetch, re-summarize, or change strategy mid-way. Useful for open-ended exploration but uses ~2x the LLM calls.

---

## What Happens Per Paper

Each paper goes through these stages:

1. **Fetch** — download/extract text (PDF, webpage, or local file)
2. **Metadata** — LLM extracts title, authors, year, venue, abstract
3. **Summarize** — LLM produces structured 12-field JSON summary
4. **Synthesize** — after all papers, LLM compares them and produces cross-paper analysis

If any stage fails, it's logged to stderr and skipped — the pipeline continues.

---

## Output Format

### Per-Paper Summary
```json
{
  "title": "...",
  "core_idea": "...",
  "methodology": "...",
  "dataset": "...",
  "key_results": ["..."],
  "limitations": ["..."],
  "novelty": "...",
  "contributions": ["..."],
  "key_equations": ["..."],
  "pseudocode": "...",
  "assumptions": ["..."],
  "executive_summary": "..."
}
```

### Cross-Paper Synthesis
```json
{
  "cross_paper_comparison": {
    "similarities": ["..."],
    "differences": ["..."],
    "contradictions": ["..."],
    "methodology_comparison": "...",
    "dataset_comparison": "..."
  },
  "key_insights": ["..."],
  "novelty_analysis": [...],
  "usefulness_ranking": [{"rank": 1, "paper": "...", "reason": "..."}],
  "recommended_reading_order": ["..."],
  "gaps_and_future_work": ["..."],
  "practical_takeaways": ["..."],
  "executive_synthesis": "..."
}
```

### Word Report Structure

The generated `.docx` contains:
1. **Title page** — papers analyzed, generation metadata
2. **Failed URLs** (if any) — what failed and why
3. **Executive Summary** — 2–3 paragraph synthesis
4. **Key Insights** — bullet points
5. **Paper Summaries** — one section per paper with title, authors, core idea, results, novelty
6. **Cross-Paper Analysis** — similarities, differences, contradictions
7. **Practical Takeaways**
8. **Deep-Dive Recommendations** — table with paper name, why to study further, key question
9. **Suggested Further Reading** — arXiv search results (auto-queried based on synthesis)
10. **Appendix** — table of all processed papers

---

## API Endpoints

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/health` | GET | — | `{"status": "ok"}` |
| `/fetch-content` | POST | `{"url_or_path": "..."}` | `{"text": "...", "word_count": N}` |
| `/extract-metadata` | POST | `{"text": "..."}` | `{"title": "...", "authors": [...], ...}` |
| `/chunk` | POST | `{"text": "...", "chunk_size": 3000, "overlap": 500}` | `{"chunks": [...], "num_chunks": N}` |
| `/summarize` | POST | `{"text": "..."}` or `{"chunks": [...]}` | Structured 12-field summary |
| `/synthesize` | POST | `{"papers": [...]}` | Cross-paper analysis |
| `/run` | POST | `{"urls": [...], "mode": "pipeline"}` | Full pipeline output |
| `/report` | POST | `{"urls": [...], "search": "..."}` | `.docx` file download |

---

## Environment Variables

All loaded from `.env` by `python-dotenv`:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Zen API key (required) |
| `OPENAI_BASE_URL` | `https://opencode.ai/zen/v1/chat/completions` | Zen API endpoint |
| `OPENAI_MODEL` | `big-pickle` | Model name |

---

## Testing

```bash
poetry run pytest tests/
```

---

## Key Principles

- **Prefer whole-paper summarization** — only chunk if text > ~150k tokens
- **Minimize tool calls** — the agent avoids re-fetching or re-summarizing
- **Ground in extracted text** — no hallucinated citations or claims
- **Graceful degradation** — a failed URL never kills the whole run
- **Deterministic structured output** — always valid JSON from every module
