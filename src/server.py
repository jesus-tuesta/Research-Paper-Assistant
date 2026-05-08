import json
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from src.fetcher import fetch_content as _fetch_content
from src.metadata import extract_metadata as _extract_metadata
from src.chunker import chunk_text, chunk_by_sections
from src.summarize import summarize as _summarize
from src.synthesize import synthesize as _synthesize

app = FastAPI(title="Research Pipeline API")


# ── Request models ──────────────────────────────────────────────────────

class FetchContentRequest(BaseModel):
    url_or_path: str

class MetadataRequest(BaseModel):
    text: str

class ChunkRequest(BaseModel):
    text: str
    chunk_size: int = Field(default=3000, ge=500, le=8000)
    overlap: int = Field(default=500, ge=100, le=2000)
    sections: bool = False

class SummarizeRequest(BaseModel):
    text: Optional[str] = None
    chunks: Optional[list[str]] = None

class SynthesizeRequest(BaseModel):
    papers: list[dict]

class RunPipelineRequest(BaseModel):
    urls: list[str]
    mode: str = "pipeline"

class ReportRequest(BaseModel):
    urls: list[str]
    search: Optional[str] = None


# ── Tool endpoints ──────────────────────────────────────────────────────

@app.post("/fetch-content")
def fetch_content(req: FetchContentRequest):
    try:
        text = _fetch_content(req.url_or_path)
        return {"text": text, "word_count": len(text.split())}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/extract-metadata")
def extract_metadata(req: MetadataRequest):
    try:
        from dotenv import load_dotenv
        load_dotenv()
        meta = _extract_metadata(req.text)
        return meta
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chunk")
def chunk(req: ChunkRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No input text provided")

    if req.sections:
        chunks = chunk_by_sections(req.text, req.chunk_size, req.overlap)
    else:
        chunks = chunk_text(req.text, req.chunk_size, req.overlap)

    return {
        "chunks": chunks,
        "num_chunks": len(chunks),
        "total_words": len(req.text.split()),
    }


@app.post("/summarize")
def summarize(req: SummarizeRequest):
    from dotenv import load_dotenv
    load_dotenv()

    try:
        if req.chunks:
            result = _summarize(chunks=req.chunks)
        elif req.text:
            result = _summarize(text=req.text)
        else:
            raise HTTPException(status_code=400, detail="Provide either text or chunks")
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    try:
        from dotenv import load_dotenv
        load_dotenv()
        result = _synthesize(req.papers)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Orchestrator endpoints ─────────────────────────────────────────────

@app.post("/run")
def run_pipeline(req: RunPipelineRequest):
    if req.mode == "agent":
        from src.orchestrator.agent import run_agent
        try:
            return run_agent(req.urls)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    from src.orchestrator.pipeline import run_pipeline as _run_pipeline
    try:
        return _run_pipeline(req.urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report")
def generate_report(req: ReportRequest):
    from src.orchestrator.pipeline import run_pipeline as _run_pipeline
    from src.report import generate_report as _generate_report

    try:
        result = _run_pipeline(req.urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")

    try:
        buf = BytesIO()
        _generate_report(result, buf, search_query=req.search)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=literature_review.docx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
