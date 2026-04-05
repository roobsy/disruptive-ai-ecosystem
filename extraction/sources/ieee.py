"""
IEEE Xplore — 6M+ engineering & CS documents
================================================
Free API for non-commercial research.
Register at: https://developer.ieee.org/
Key issued during US business hours (8am-5pm ET, Mon-Fri).
Rate limit: 200 results per query, reasonable request frequency.
"""

import os
import httpx
from extraction.source_interface import SourceResult
from dotenv import load_dotenv

load_dotenv()

BASE = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


def search(query: str, limit: int = 20, year_range: str = None, min_citations: int = 0, **kwargs) -> list[SourceResult]:
    """Search IEEE Xplore for papers.

    Requires IEEE_API_KEY in .env.
    Register free at https://developer.ieee.org/
    """
    api_key = os.getenv("IEEE_API_KEY", "")
    if not api_key:
        # Silently skip if not configured
        return []

    params = {
        "apikey": api_key,
        "querytext": query,
        "max_records": min(limit, 200),
        "sort_order": "asc",
        "sort_field": "article_number",
    }

    if year_range:
        parts = year_range.split("-")
        if len(parts) == 2:
            if parts[0]:
                params["start_year"] = parts[0]
            if parts[1]:
                params["end_year"] = parts[1]

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])
    except httpx.HTTPError as e:
        print(f"  [IEEE] Error: {e}")
        return []

    results = []
    for a in articles:
        # Title
        title = a.get("title", "")

        # Authors
        author_list = a.get("authors", {}).get("authors", [])
        authors = [auth.get("full_name", "") for auth in author_list[:10]]

        # Year
        year = a.get("publication_year")
        if year:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None

        # Abstract
        abstract = a.get("abstract", "")[:500]

        # DOI
        doi = a.get("doi", "")

        # URL
        url = a.get("html_url", "") or a.get("pdf_url", "")
        if not url and doi:
            url = f"https://doi.org/{doi}"

        # PDF
        pdf_url = a.get("pdf_url", "")

        # Open access check
        is_oa = a.get("access_type", "") == "OPEN_ACCESS"

        # Citation count (IEEE doesn't always provide this)
        citing_count = a.get("citing_paper_count", 0)
        if isinstance(citing_count, str):
            try:
                citing_count = int(citing_count)
            except ValueError:
                citing_count = 0

        if min_citations and citing_count < min_citations:
            continue

        # Publication info
        pub_title = a.get("publication_title", "")
        content_type = a.get("content_type", "")

        results.append(SourceResult(
            source_type="academic_paper",
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            url=url,
            pdf_url=pdf_url if is_oa else "",
            doi=doi,
            citation_count=citing_count,
            credibility_tier="tier3_semi_structured",
            has_open_access=is_oa,
            source_api="ieee_xplore",
            raw_data={
                "publication_title": pub_title,
                "content_type": content_type,
                "is_number": a.get("is_number", ""),
            },
        ))

    return results
