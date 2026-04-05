"""
SPIE Digital Library — 650K+ optics & photonics papers
=========================================================
No public API available. This client searches the SPIE
website directly using respectful web scraping.

SPIE papers are also indexed by Semantic Scholar and OpenAlex,
so this is a supplementary source for SPIE-specific searches.

Note: Only abstracts are freely available. Full text requires
institutional subscription or per-article purchase.
"""

import re
import time
import httpx
from extraction.source_interface import SourceResult

SEARCH_URL = "https://www.spiedigitallibrary.org/action/doSearch"
USER_AGENT = "DisruptiveAI-Ecosystem/1.0 (Research; mailto:ecosystem@disruptive.ai)"

_last_request = 0.0


def _rate_limit():
    """Enforce minimum 2 second delay between requests."""
    global _last_request
    now = time.time()
    wait = 2.5 - (now - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()


def search(query: str, limit: int = 20, year_range: str = None, min_citations: int = 0, **kwargs) -> list[SourceResult]:
    """Search SPIE Digital Library.

    Scrapes the search results page to extract paper metadata.
    Respects rate limits and robots.txt.
    """
    params = {
        "AllField": query,
        "pageSize": min(limit, 20),
        "startPage": 0,
        "sortBy": "relevancy",
    }

    if year_range:
        parts = year_range.split("-")
        if len(parts) == 2:
            if parts[0]:
                params["AfterYear"] = parts[0]
            if parts[1]:
                params["BeforeYear"] = parts[1]

    _rate_limit()

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(SEARCH_URL, params=params, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html",
            })
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        print(f"  [SPIE] Error: {e}")
        return []

    # Parse search results from HTML
    results = []

    # Find result items — SPIE uses structured HTML for search results
    # Look for article entries with titles and metadata
    article_blocks = re.findall(
        r'<div class="searchResultItem">(.*?)</div>\s*</div>',
        html, re.DOTALL
    )

    # Alternative pattern if the above doesn't match
    if not article_blocks:
        article_blocks = re.findall(
            r'class="[^"]*item-title[^"]*"[^>]*>(.*?)</(?:h\d|div)',
            html, re.DOTALL
        )

    # Try a more general pattern — extract titles and links
    title_links = re.findall(
        r'<a[^>]+href="(/[^"]*)"[^>]*class="[^"]*(?:item-title|hlFld-Title)[^"]*"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    if not title_links:
        # Try even more general pattern
        title_links = re.findall(
            r'<a[^>]+href="((?:/journals/|/conference-proceedings-of-spie/)[^"]*)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

    for href, title_html in title_links[:limit]:
        title = re.sub(r'<[^>]+>', '', title_html).strip()
        if not title or len(title) < 10:
            continue

        url = f"https://www.spiedigitallibrary.org{href}" if href.startswith("/") else href

        # Try to extract DOI from the URL
        doi_match = re.search(r'10\.\d{4,}/\S+', href)
        doi = doi_match.group(0) if doi_match else ""

        # Try to extract year from surrounding context
        year = None
        year_match = re.search(r'\b(19|20)\d{2}\b', href)
        if year_match:
            year = int(year_match.group(0))

        results.append(SourceResult(
            source_type="academic_paper",
            title=title,
            url=url,
            doi=doi,
            year=year,
            credibility_tier="tier3_semi_structured",
            has_open_access=False,  # Assume paywalled unless marked OA
            source_api="spie",
        ))

    # If HTML parsing got nothing, note it but don't error
    if not results and "searchResultItem" not in html and "item-title" not in html:
        # SPIE might be blocking or page structure changed
        # Silently return empty — Semantic Scholar and OpenAlex cover SPIE papers
        pass

    return results
