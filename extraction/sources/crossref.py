"""
CrossRef — 130M+ DOI-registered works, free
===============================================
Citation verification, reference chains, publication metadata.
Docs: https://api.crossref.org/
"""

import httpx
from extraction.source_interface import SourceResult

BASE = "https://api.crossref.org"
MAILTO = "ecosystem@disruptive.ai"


def search(query: str, limit: int = 20, year_range: str = None, min_citations: int = 0) -> list[SourceResult]:
    params = {
        "query": query,
        "rows": min(limit, 50),
        "sort": "relevance",
        "order": "desc",
        "mailto": MAILTO,
    }
    if year_range:
        parts = year_range.split("-")
        if len(parts) == 2:
            filt = ""
            if parts[0]:
                filt += f"from-pub-date:{parts[0]}"
            if parts[1]:
                filt += f",until-pub-date:{parts[1]}" if filt else f"until-pub-date:{parts[1]}"
            if filt:
                params["filter"] = filt

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{BASE}/works", params=params)
            resp.raise_for_status()
            items = resp.json().get("message", {}).get("items", [])
    except httpx.HTTPError as e:
        print(f"  [CrossRef] Error: {e}")
        return []

    results = []
    for item in items:
        cites = item.get("is-referenced-by-count", 0)
        if min_citations and cites < min_citations:
            continue

        # Authors
        authors = []
        for a in (item.get("author") or [])[:10]:
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if name:
                authors.append(name)

        # Year
        date_parts = (item.get("published-print") or item.get("published-online") or {}).get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None

        # Title
        titles = item.get("title") or []
        title = titles[0] if titles else ""

        # Abstract
        abstract = item.get("abstract") or ""
        # CrossRef abstracts often have JATS XML tags
        import re
        abstract = re.sub(r"<[^>]+>", "", abstract)[:500]

        # URL
        doi = item.get("DOI", "")
        url = f"https://doi.org/{doi}" if doi else ""

        # Open access via license
        licenses = item.get("license") or []
        is_oa = any("open" in (lic.get("URL") or "").lower() or "creativecommons" in (lic.get("URL") or "").lower()
                     for lic in licenses)

        results.append(SourceResult(
            source_type="academic_paper", title=title,
            authors=authors, year=year, abstract=abstract,
            url=url, doi=doi, citation_count=cites,
            credibility_tier="tier1_academic",
            has_open_access=is_oa,
            source_api="crossref", raw_data=item,
        ))
    return results


def get_by_doi(doi: str) -> SourceResult | None:
    """Look up a specific work by DOI."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{BASE}/works/{doi}", params={"mailto": MAILTO})
            resp.raise_for_status()
            item = resp.json().get("message", {})
    except httpx.HTTPError:
        return None

    results = search.__wrapped__(item) if hasattr(search, '__wrapped__') else None
    # Simplified single-item return
    titles = item.get("title") or []
    return SourceResult(
        source_type="academic_paper", title=titles[0] if titles else "",
        doi=item.get("DOI", ""), url=f"https://doi.org/{item.get('DOI', '')}",
        citation_count=item.get("is-referenced-by-count", 0),
        source_api="crossref", credibility_tier="tier1_academic",
    )
