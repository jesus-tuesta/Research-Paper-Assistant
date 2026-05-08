import sys
import json
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

ARXIV_API = "http://export.arxiv.org/api/query"


def search_arxiv(query, max_results=5, retries=2):
    params = {
        "search_query": f"all:{query}",
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.get(ARXIV_API, params=params,
                                headers={"User-Agent": "ResearchAgent/1.0"},
                                timeout=15)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            print(f"arXiv search failed: {e}", file=sys.stderr)
            return []

    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    papers = []
    for entry in root.findall("a:entry", ns):
        paper_id = entry.find("a:id", ns).text.strip()
        title = "".join(entry.find("a:title", ns).itertext()).strip().replace("\n", " ")
        summary = "".join(entry.find("a:summary", ns).itertext()).strip().replace("\n", " ")
        authors = [a.find("a:name", ns).text for a in entry.findall("a:author", ns)]
        link = paper_id.replace("http://", "https://") + ".pdf"
        papers.append({
            "title": title[:200],
            "authors": authors[:5],
            "abstract": summary[:500],
            "link": link,
            "id": paper_id.split("/")[-1],
        })
    return papers


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "machine learning"
    results = search_arxiv(query)
    print(json.dumps(results, indent=2))
