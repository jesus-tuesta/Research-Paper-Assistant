"""
Unit tests for the research pipeline tools.
Run with: python -m pytest tests/
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chunker import chunk_text, chunk_by_sections


SAMPLE_TEXT = """
Abstract
This is a test paper about machine learning.

Introduction
We propose a new method for text classification.

Methodology
Our approach uses a transformer architecture with 12 layers
and 768 hidden dimensions. We train on the GLUE benchmark.

Results
Our method achieves 92% accuracy on MNLI and 91% on QQP.

Conclusion
We presented a novel approach for text classification.
"""


def test_chunk_text_basic():
    chunks = chunk_text(SAMPLE_TEXT, chunk_size=50, overlap=10)
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)
    assert all(len(c.split()) <= 55 for c in chunks)  # allow small overflow


def test_chunk_text_small_text():
    chunks = chunk_text("Short text.", chunk_size=100, overlap=20)
    assert len(chunks) == 1
    assert "Short text." in chunks[0]


def test_chunk_by_sections():
    chunks = chunk_by_sections(SAMPLE_TEXT, chunk_size=200, overlap=20)
    assert len(chunks) >= 1


def test_chunk_empty():
    chunks = chunk_text("", chunk_size=100, overlap=20)
    assert chunks == []


def test_chunk_whitespace():
    chunks = chunk_text("   \n\n  ", chunk_size=100, overlap=20)
    assert chunks == []


def test_chunk_multi_paragraph():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three.\n\n" * 50
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1


def test_extract_json():
    from src.summarize import extract_json
    result = extract_json('{"key": "value"}')
    assert result == {"key": "value"}

    result = extract_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}
