import os
import subprocess
import tempfile
from pathlib import Path

import requests
import trafilatura


def _extract_pdf_file(pdf_path: str) -> str:
    """Extract text from a local PDF file. Used internally by fetch_pdf and extract_local."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    try:
        import fitz
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        if text.strip():
            return text.strip()
    except ImportError:
        pass

    raise RuntimeError(
        "No PDF text extraction method available. "
        "Install poppler-utils or PyMuPDF."
    )


def fetch_pdf(url: str, timeout: int = 60) -> str:
    """Download a PDF from *url* and return extracted text."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(resp.content)
        pdf_path = tmp.name

    try:
        return _extract_pdf_file(pdf_path)
    finally:
        os.unlink(pdf_path)


def scrape_webpage(url: str, timeout: int = 60) -> str:
    """Extract main text content from a webpage using trafilatura."""
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "ResearchAgent/1.0"})
    resp.raise_for_status()
    text = trafilatura.extract(resp.text, include_tables=True, include_links=False)
    if not text:
        raise RuntimeError(f"Failed to extract text from webpage: {url}")
    return text.strip()


def extract_local(path: str) -> str:
    """Extract text from a local file (PDF, HTML, or TXT)."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_file(path)
    if ext in (".html", ".htm"):
        text = trafilatura.extract(Path(path).read_text(encoding="utf-8"),
                                   include_tables=True, include_links=False)
        if not text:
            raise RuntimeError(f"Failed to extract text from HTML file: {path}")
        return text.strip()
    return Path(path).read_text(encoding="utf-8").strip()


def fetch_content(url_or_path: str, timeout: int = 60) -> str:
    """Auto-detect URL vs local file, PDF vs webpage, and return extracted text."""
    if url_or_path.startswith(("http://", "https://")):
        url = url_or_path
        if url.lower().endswith(".pdf"):
            return fetch_pdf(url, timeout)
        try:
            resp = requests.head(url, timeout=max(timeout // 2, 10), allow_redirects=True)
            ct = resp.headers.get("Content-Type", "")
            if "pdf" in ct:
                return fetch_pdf(url, timeout)
        except requests.RequestException:
            pass
        return scrape_webpage(url, timeout)
    else:
        return extract_local(url_or_path)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    url_or_path = sys.argv[1]
    text = fetch_content(url_or_path)
    print(text[:2000])
