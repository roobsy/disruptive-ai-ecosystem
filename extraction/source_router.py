"""
Source Router — Unified Multi-Tier Data Acquisition
======================================================
Orchestrates all four tiers of data sources from the Blueprint.
The Research Agent calls this instead of individual sources.

Tier 1: Academic APIs (Semantic Scholar, OpenAlex, CrossRef, PubMed, Unpaywall)
Tier 2: Patent APIs (PatentsView, EPO, Google Patents)
Tier 3: Semi-structured (IEEE, SPIE — via web scraper when no API)
Tier 4: Web scraper fallback

The router handles:
- Multi-source parallel search
- Result deduplication across sources
- Open-access PDF enrichment via Unpaywall
- Source-appropriate credibility tier assignment
"""

import time
from typing import Optional
from rich.console import Console
from extraction.source_interface import SourceResult

# Import all source clients
from extraction.sources import semantic_scholar
from extraction.sources import openalex
from extraction.sources import crossref
from extraction.sources import pubmed
from extraction.sources import unpaywall
from extraction.sources import patents_view
from extraction.sources import epo
from extraction.sources import google_patents
from extraction.sources import web_scraper
from extraction.sources import ieee
from extraction.sources import spie

console = Console()


# ── Source Registry ───────────────────────────────────────
ACADEMIC_SOURCES = [
    {"name": "Semantic Scholar", "module": semantic_scholar, "tier": 1},
    {"name": "OpenAlex", "module": openalex, "tier": 1},
    {"name": "CrossRef", "module": crossref, "tier": 1},
    {"name": "PubMed", "module": pubmed, "tier": 1},
]

PATENT_SOURCES = [
    {"name": "PatentsView (USPTO)", "module": patents_view, "tier": 2},
    {"name": "EPO", "module": epo, "tier": 2},
]

TIER3_SOURCES = [
    {"name": "IEEE Xplore", "module": ieee, "tier": 3},
    {"name": "SPIE", "module": spie, "tier": 3},
]


# ── Deduplication ─────────────────────────────────────────
def _deduplicate(results: list[SourceResult]) -> list[SourceResult]:
    """Remove duplicate results across sources using DOI, ArXiv ID, or title similarity."""
    seen_dois = set()
    seen_arxiv = set()
    seen_titles = set()
    unique = []

    for r in results:
        # Check DOI
        if r.doi:
            doi_key = r.doi.lower().strip()
            if doi_key in seen_dois:
                continue
            seen_dois.add(doi_key)

        # Check ArXiv ID
        if r.arxiv_id:
            arxiv_key = r.arxiv_id.split("v")[0]  # Strip version
            if arxiv_key in seen_arxiv:
                continue
            seen_arxiv.add(arxiv_key)

        # Check patent number
        if r.patent_number:
            if r.patent_number in seen_titles:
                continue
            seen_titles.add(r.patent_number)

        # Fuzzy title check (normalized)
        title_key = re.sub(r"[^a-z0-9]", "", r.title.lower())[:60]
        if title_key and len(title_key) > 10 and title_key in seen_titles:
            continue
        if title_key and len(title_key) > 10:
            seen_titles.add(title_key)

        unique.append(r)

    return unique


import re  # For the dedup function above


# ── Academic Search ───────────────────────────────────────
def search_academic(
    query: str,
    limit_per_source: int = 10,
    year_range: str = None,
    min_citations: int = 0,
    sources: list[str] = None,
    enrich_oa: bool = True,
) -> list[SourceResult]:
    """Search across all Tier 1 academic sources.

    Args:
        query: Search terms
        limit_per_source: Max results per source
        year_range: e.g., "2014-2026"
        min_citations: Minimum citation count filter
        sources: Optional list of source names to use (default: all)
        enrich_oa: Whether to check Unpaywall for open access PDFs

    Returns:
        Deduplicated, sorted list of SourceResults
    """
    all_results = []
    active_sources = ACADEMIC_SOURCES
    if sources:
        active_sources = [s for s in ACADEMIC_SOURCES if s["name"] in sources]

    for src in active_sources:
        name = src["name"]
        mod = src["module"]
        console.print(f"  [blue]Searching {name}...[/blue]", end="")

        try:
            results = mod.search(
                query=query,
                limit=limit_per_source,
                year_range=year_range,
                min_citations=min_citations,
            )
            console.print(f" → {len(results)} results")
            all_results.extend(results)
        except Exception as e:
            console.print(f" → [red]Error: {e}[/red]")

        time.sleep(0.3)  # Polite delay between sources

    # Deduplicate
    unique = _deduplicate(all_results)
    console.print(f"  [dim]{len(all_results)} total → {len(unique)} unique after dedup[/dim]")

    # Enrich with open access PDFs
    if enrich_oa:
        no_pdf = [r for r in unique if r.doi and not r.pdf_url]
        if no_pdf:
            console.print(f"  [blue]Checking Unpaywall for {len(no_pdf)} papers without PDFs...[/blue]")
            unpaywall.enrich_results_with_oa(no_pdf[:10], delay=0.3)  # Limit to 10 to be polite
            found = sum(1 for r in no_pdf if r.pdf_url)
            console.print(f"  [dim]Found {found} additional open-access PDFs[/dim]")

    # Sort by citation count (descending)
    unique.sort(key=lambda r: r.citation_count, reverse=True)

    return unique


# ── Patent Search ─────────────────────────────────────────
def search_patents(
    query: str,
    limit_per_source: int = 10,
    year_range: str = None,
    assignees: list[str] = None,
) -> list[SourceResult]:
    """Search across all Tier 2 patent sources.

    Args:
        query: Search terms
        limit_per_source: Max results per source
        year_range: e.g., "2014-2026"
        assignees: Optional list of assignee names to search specifically

    Returns:
        Deduplicated patent results
    """
    all_results = []

    for src in PATENT_SOURCES:
        name = src["name"]
        mod = src["module"]
        console.print(f"  [blue]Searching {name}...[/blue]", end="")

        try:
            results = mod.search(query=query, limit=limit_per_source, year_range=year_range)
            console.print(f" → {len(results)} results")
            all_results.extend(results)
        except Exception as e:
            console.print(f" → [red]Error: {e}[/red]")

        time.sleep(0.3)

    # Search by assignee if specified
    if assignees:
        for assignee in assignees:
            console.print(f"  [blue]PatentsView assignee: {assignee}...[/blue]", end="")
            try:
                results = patents_view.search_by_assignee(assignee, limit=limit_per_source)
                console.print(f" → {len(results)} results")
                all_results.extend(results)
            except Exception as e:
                console.print(f" → [red]Error: {e}[/red]")
            time.sleep(0.3)

    unique = _deduplicate(all_results)
    console.print(f"  [dim]{len(all_results)} total → {len(unique)} unique after dedup[/dim]")

    return unique


# ── Known Patent Lookup ───────────────────────────────────
def lookup_known_patents(patent_numbers: list[str]) -> list[SourceResult]:
    """Look up specific known patents by number."""
    results = []
    for pat_num in patent_numbers:
        console.print(f"  [blue]Looking up {pat_num}...[/blue]", end="")
        result = google_patents.lookup_patent(pat_num)
        if result:
            results.append(result)
            console.print(f" → {result.title[:60]}")
        else:
            console.print(f" → [yellow]Not found[/yellow]")
        time.sleep(1)
    return results


# ── Web Scrape (Tier 4) ──────────────────────────────────
def scrape_url(url: str) -> Optional[SourceResult]:
    """Scrape a specific URL as a Tier 4 fallback."""
    console.print(f"  [yellow]Tier 4 scrape: {url}[/yellow]")
    return web_scraper.scrape_to_result(url)


# ── Tier 3: Semi-Structured Sources ──────────────────────
def search_tier3(
    query: str,
    limit_per_source: int = 10,
    year_range: str = None,
    min_citations: int = 0,
) -> list[SourceResult]:
    """Search across Tier 3 sources (IEEE, SPIE).

    IEEE requires IEEE_API_KEY in .env (register free at developer.ieee.org).
    SPIE is searched via web scraping — no key needed.
    """
    all_results = []

    for src in TIER3_SOURCES:
        name = src["name"]
        mod = src["module"]
        console.print(f"  [blue]Searching {name}...[/blue]", end="")

        try:
            results = mod.search(
                query=query,
                limit=limit_per_source,
                year_range=year_range,
                min_citations=min_citations,
            )
            console.print(f" → {len(results)} results")
            all_results.extend(results)
        except Exception as e:
            console.print(f" → [red]Error: {e}[/red]")

        time.sleep(0.5)

    unique = _deduplicate(all_results)
    return unique


# ── Universal Search ──────────────────────────────────────
def search_all(
    query: str,
    include_academic: bool = True,
    include_patents: bool = True,
    include_tier3: bool = True,
    limit_per_source: int = 8,
    year_range: str = None,
    min_citations: int = 0,
    patent_assignees: list[str] = None,
) -> list[SourceResult]:
    """Search across ALL tiers simultaneously.

    This is the main entry point for the Research Agent.
    """
    all_results = []

    if include_academic:
        console.print("\n[bold]Tier 1: Academic Sources[/bold]")
        academic = search_academic(
            query=query,
            limit_per_source=limit_per_source,
            year_range=year_range,
            min_citations=min_citations,
        )
        all_results.extend(academic)

    if include_patents:
        console.print("\n[bold]Tier 2: Patent Sources[/bold]")
        patents = search_patents(
            query=query,
            limit_per_source=limit_per_source,
            year_range=year_range,
            assignees=patent_assignees,
        )
        all_results.extend(patents)

    if include_tier3:
        console.print("\n[bold]Tier 3: Semi-Structured Sources[/bold]")
        tier3 = search_tier3(
            query=query,
            limit_per_source=limit_per_source,
            year_range=year_range,
            min_citations=min_citations,
        )
        all_results.extend(tier3)

    # Sort: academic by citations, patents by date
    academic_results = [r for r in all_results if r.source_type == "academic_paper"]
    patent_results = [r for r in all_results if r.source_type == "patent"]
    academic_results.sort(key=lambda r: r.citation_count, reverse=True)
    patent_results.sort(key=lambda r: r.year or 0, reverse=True)

    return academic_results + patent_results
