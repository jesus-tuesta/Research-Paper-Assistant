import sys
import json
import argparse
import re


def chunk_text(text, chunk_size=3000, overlap=500):
    """Split text into chunks by paragraphs with overlap."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = len(para.split())

        if current_length + para_len > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            overlap_words = []
            overlap_count = 0
            for p in reversed(current_chunk):
                words = p.split()
                if overlap_count + len(words) > overlap:
                    overlap_words.insert(0, " ".join(words[-(overlap - overlap_count):]))
                    break
                overlap_words.insert(0, p)
                overlap_count += len(words)
            current_chunk = overlap_words
            current_length = overlap_count

        current_chunk.append(para)
        current_length += para_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def chunk_by_sections(text, chunk_size=3000, overlap=500):
    """Try to respect section boundaries; fall back to paragraph chunking."""
    section_pattern = re.compile(
        r'^(?:\d+\.\s+)?(?:Abstract|Introduction|Related Work|Methodology|'
        r'Methods|Experiments|Results|Discussion|Conclusion|References|'
        r'Bibliography|Acknowledgments|Appendix)',
        re.MULTILINE | re.IGNORECASE
    )

    sections = section_pattern.split(text)
    if len(sections) > 1:
        result = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            if len(section.split()) > chunk_size:
                result.extend(chunk_text(section, chunk_size, overlap))
            else:
                result.append(section)
        return result

    return chunk_text(text, chunk_size, overlap)


def main():
    parser = argparse.ArgumentParser(description="Chunk text for LLM processing")
    parser.add_argument("--text", type=str, help="Text to chunk (or use stdin)")
    parser.add_argument("--chunk-size", type=int, default=3000, help="Target chunk size in words")
    parser.add_argument("--overlap", type=int, default=500, help="Overlap between chunks in words")
    parser.add_argument("--sections", action="store_true", help="Try to respect section boundaries")
    args = parser.parse_args()

    text = args.text or sys.stdin.read()
    if not text.strip():
        print(json.dumps({"error": "No input text provided"}))
        sys.exit(1)

    if args.sections:
        chunks = chunk_by_sections(text, args.chunk_size, args.overlap)
    else:
        chunks = chunk_text(text, args.chunk_size, args.overlap)

    output = {
        "chunks": chunks,
        "num_chunks": len(chunks),
        "total_words": len(text.split()),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
