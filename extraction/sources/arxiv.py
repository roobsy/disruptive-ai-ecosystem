"""
ArXiv Source — Paper Discovery and Download
=============================================
Handles searching and downloading papers from ArXiv.
"""

import re
import httpx
from pathlib import Path
from typing import Optional


ARXIV_PDF_BASE = "https://arxiv.org/pdf/"
ARXIV_ABS_BASE = "https://arxiv.org/abs/"
DOWNLOAD_DIR = Path("data/papers")


def ensure_download_dir():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def extract_arxiv_id(url_or_id: str) -> str:
    """Extract the ArXiv ID from a URL or raw ID.

    Handles:
      - 2501.01450
      - 2501.01450v1
      - https://arxiv.org/abs/2501.01450
      - https://arxiv.org/pdf/2501.01450
      - https://arxiv.org/html/2501.01450v1
    """
    # Strip URL components
    cleaned = url_or_id.strip().rstrip("/")
    # Try to find the ID pattern
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", cleaned)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract ArXiv ID from: {url_or_id}")


def download_pdf(url_or_id: str, filename: str = None) -> Optional[Path]:
    """Download a PDF from ArXiv.

    Args:
        url_or_id: ArXiv URL or paper ID (e.g., "2501.01450")
        filename: Optional custom filename. Defaults to {arxiv_id}.pdf

    Returns:
        Path to the downloaded PDF, or None if download failed.
    """
    ensure_download_dir()
    arxiv_id = extract_arxiv_id(url_or_id)
    pdf_url = f"{ARXIV_PDF_BASE}{arxiv_id}"

    if filename is None:
        safe_id = arxiv_id.replace("/", "_")
        filename = f"{safe_id}.pdf"

    output_path = DOWNLOAD_DIR / filename

    # Skip if already downloaded
    if output_path.exists() and output_path.stat().st_size > 1000:
        print(f"  Already downloaded: {output_path}")
        return output_path

    print(f"  Downloading: {pdf_url}")
    try:
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            response = client.get(pdf_url)
            response.raise_for_status()

            # Verify we got a PDF
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type and not response.content[:5] == b"%PDF-":
                print(f"  Warning: Response may not be a PDF (content-type: {content_type})")

            output_path.write_bytes(response.content)
            print(f"  Saved: {output_path} ({len(response.content):,} bytes)")
            return output_path

    except httpx.HTTPError as e:
        print(f"  Download failed: {e}")
        return None


def get_paper_metadata(url_or_id: str) -> dict:
    """Fetch basic metadata for an ArXiv paper using the ArXiv API.

    Returns dict with title, authors, abstract, published date.
    """
    arxiv_id = extract_arxiv_id(url_or_id)
    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(api_url)
            response.raise_for_status()
            xml = response.text

        # Simple XML parsing (avoiding heavy dependencies)
        def extract_tag(tag, text):
            match = re.search(f"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL)
            return match.group(1).strip() if match else ""

        # Extract authors
        authors = re.findall(r"<name>(.*?)</name>", xml)

        # Extract year from published date
        published = extract_tag("published", xml)
        year = int(published[:4]) if published else None

        return {
            "arxiv_id": arxiv_id,
            "title": extract_tag("title", xml).replace("\n", " "),
            "authors": authors,
            "abstract": extract_tag("summary", xml).replace("\n", " "),
            "published": published,
            "year": year,
            "url": f"{ARXIV_ABS_BASE}{arxiv_id}",
            "pdf_url": f"{ARXIV_PDF_BASE}{arxiv_id}",
        }

    except Exception as e:
        print(f"  Metadata fetch failed: {e}")
        return {"arxiv_id": arxiv_id, "url": f"{ARXIV_ABS_BASE}{arxiv_id}"}
