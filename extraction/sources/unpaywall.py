"""
Unpaywall — Open Access PDF Finder, free
============================================
Given a DOI, finds legal open-access versions of papers.
Essential for getting full-text PDFs without paywalls.
Docs: https://unpaywall.org/products/api
"""

import httpx
from typing import Optional

MAILTO = "ecosystem@disruptive.ai"
BASE = "https://api.unpaywall.org/v2"


def find_open_access(doi: str) -> Optional[dict]:
    """Check if an open-access version exists for a DOI.

    Returns dict with pdf_url and metadata, or None if no OA version found.
    """
    if not doi:
        return None

    clean_doi = doi.strip().replace("https://doi.org/", "")

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{BASE}/{clean_doi}", params={"email": MAILTO})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        return None

    if not data.get("is_oa"):
        return None

    best = data.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf") or best.get("url") or ""

    return {
        "is_oa": True,
        "pdf_url": pdf_url,
        "oa_status": data.get("oa_status", ""),
        "journal": data.get("journal_name", ""),
        "publisher": data.get("publisher", ""),
        "title": data.get("title", ""),
        "year": data.get("year"),
    }


def enrich_results_with_oa(results: list, delay: float = 0.2) -> list:
    """Take a list of SourceResults and add open-access PDF URLs where available.

    Modifies results in-place and returns the list.
    """
    import time
    for r in results:
        if r.doi and not r.pdf_url:
            oa = find_open_access(r.doi)
            if oa and oa.get("pdf_url"):
                r.pdf_url = oa["pdf_url"]
                r.has_open_access = True
            time.sleep(delay)  # Rate limiting
    return results
