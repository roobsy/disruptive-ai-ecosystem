#!/usr/bin/env python3
"""
Research — Autonomous Multi-Tier Knowledge Acquisition
=========================================================
Searches across ALL data sources (academic, patent, web),
ranks results, and extracts into the Knowledge Base.

Usage:
    python -m scripts.research --priorities           # Show Master Brain's gap priorities
    python -m scripts.research --search "query"       # Preview search (no extraction)
    python -m scripts.research --gap-id GAP1          # Research a priority gap
    python -m scripts.research --gap "description"    # Research a custom gap
    python -m scripts.research --auto                 # Auto-research all SHOWSTOPPER gaps
    python -m scripts.research --patents "query"      # Patent-only search preview
    python -m scripts.research --lookup US12141346    # Look up a specific patent
"""

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents.research_agent import research_gap, research_multiple_gaps
from extraction.source_router import search_academic, search_patents, lookup_known_patents
from core.kb import get_venture_id, get_stats

console = Console()

# ── Master Brain's Priority Gaps ──
PRIORITY_GAPS = [
    {"id": "GAP1", "priority": "SHOWSTOPPER", "title": "Patent Landscape — Vision Correcting Displays",
     "description": "Systematic patent search for vision correcting display technology. Key terms: 'vision correcting display', 'pre-distortion refractive error', 'computational vision correction display', 'light field vision correction'. Key assignees: UC Berkeley, Stanford, MIT, Microsoft, Apple, Samsung, Meta, Google, Nvidia. Must find patents related to: Huang et al. Berkeley SIGGRAPH 2014, Pamplona et al. MIT, Wetzstein Stanford Computational Imaging Lab, Rabbit Eyes (US Patent 12,141,346)."},
    {"id": "GAP2", "priority": "SHOWSTOPPER", "title": "Ophthalmology & Eye Aberration Modeling",
     "description": "Human eye aberration modeling with Zernike polynomials. Population statistics of refractive errors by severity. MTF of human eye as function of refractive error and pupil size. Key papers: Thibos et al. 'Statistical variation of aberration structure' (JOSA A 2002), Applegate papers on Zernike aberrations and visual acuity. PSF computation from standard optometric prescription data."},
    {"id": "GAP3", "priority": "SHOWSTOPPER", "title": "Human Perceptual Validation of Pre-Distorted Displays",
     "description": "Psychophysics of pre-distorted display perception. Contrast sensitivity functions and how they interact with pre-distortion. Visual fatigue and discomfort from vision-correcting displays. Perceptual quality metrics for pre-distorted images. Binocular vision considerations."},
    {"id": "GAP4", "priority": "CRITICAL", "title": "Quantitative Limits of Software Pre-Distortion",
     "description": "Quantitative feasibility bounds for software-only vision correction. At what diopter level does the eye's MTF hit zero within display Nyquist frequency? Blur kernel radius vs diopter and viewing distance. Effective resolution after pre-distortion. Comparison: Wiener vs Richardson-Lucy vs learned filters. Noise amplification and ringing artifacts."},
    {"id": "GAP5", "priority": "CRITICAL", "title": "Real-Time Processing Architecture",
     "description": "GPU benchmarks for real-time Wiener deconvolution at 60fps+ for 4K. Mobile GPU capabilities for per-frame PSF processing. Latency budgets for vision correction. Software architecture for display-level processing on Android and iOS."},
    {"id": "GAP6", "priority": "STRATEGIC", "title": "Regulatory Classification",
     "description": "FDA classification of software-based vision aids. Is vision-correcting display software a medical device? Precedent: reading glasses vs software vision correction. FDA guidance on wellness vs medical device. CE marking for EU. Regulatory pathway: Class I vs 510(k) vs De Novo."},
]


def show_priorities():
    table = Table(title="Master Brain Priority Gaps", show_lines=True)
    table.add_column("ID", width=6)
    table.add_column("Priority", width=14)
    table.add_column("Title", width=50)
    colors = {"SHOWSTOPPER": "red", "CRITICAL": "yellow", "STRATEGIC": "blue"}
    for g in PRIORITY_GAPS:
        c = colors.get(g["priority"], "white")
        table.add_row(g["id"], f"[{c}]{g['priority']}[/{c}]", g["title"])
    console.print(table)


def search_preview(query: str, search_type: str = "academic"):
    console.print(f"\n[bold]Search preview: \"{query}\" ({search_type})[/bold]\n")
    if search_type == "patent":
        results = search_patents(query, limit_per_source=10)
    elif search_type == "all":
        from extraction.source_router import search_all
        results = search_all(query, limit_per_source=6)
    else:
        results = search_academic(query, limit_per_source=10, enrich_oa=False)

    if not results:
        console.print("  [yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Results ({len(results)})", show_lines=True)
    table.add_column("#", width=4)
    table.add_column("Type", width=8)
    table.add_column("Year", width=6)
    table.add_column("Cites", width=6, justify="right")
    table.add_column("PDF", width=5)
    table.add_column("Source", width=12)
    table.add_column("Title", width=50)

    for i, r in enumerate(results[:25], 1):
        stype = "Paper" if r.source_type == "academic_paper" else "Patent"
        pdf = "✓" if r.has_open_access else ""
        table.add_row(str(i), stype, str(r.year or "?"), str(r.citation_count),
                     pdf, r.source_api[:12], r.title[:50])
    console.print(table)


def patent_lookup(patent_numbers: list[str]):
    console.print(f"\n[bold]Looking up {len(patent_numbers)} patents...[/bold]\n")
    results = lookup_known_patents(patent_numbers)
    for r in results:
        console.print(Panel(
            f"[bold]{r.title}[/bold]\n\n"
            f"Year: {r.year}\n"
            f"Inventors: {', '.join(r.authors[:5])}\n"
            f"URL: {r.url}\n\n"
            f"Abstract: {r.abstract[:300]}",
            style="blue",
        ))


def main():
    parser = argparse.ArgumentParser(description="Autonomous Multi-Tier Research")
    parser.add_argument("--gap", "-g", help="Research a custom gap")
    parser.add_argument("--gap-id", "-id", help="Research a priority gap by ID")
    parser.add_argument("--search", "-s", help="Academic search preview")
    parser.add_argument("--patents", help="Patent search preview")
    parser.add_argument("--search-all", help="Search all sources preview")
    parser.add_argument("--lookup", nargs="+", help="Look up specific patent numbers")
    parser.add_argument("--priorities", "-p", action="store_true", help="Show priority gaps")
    parser.add_argument("--auto", "-a", action="store_true", help="Auto-research SHOWSTOPPER gaps")
    parser.add_argument("--max-papers", "-n", type=int, default=5, help="Max papers per gap")
    args = parser.parse_args()

    if args.priorities:
        show_priorities()
    elif args.search:
        search_preview(args.search, "academic")
    elif args.patents:
        search_preview(args.patents, "patent")
    elif args.search_all:
        search_preview(args.search_all, "all")
    elif args.lookup:
        patent_lookup(args.lookup)
    elif args.gap:
        research_gap(args.gap, max_papers=args.max_papers)
    elif args.gap_id:
        gap = next((g for g in PRIORITY_GAPS if g["id"].upper() == args.gap_id.upper()), None)
        if gap:
            research_gap(gap["description"], max_papers=args.max_papers)
        else:
            console.print(f"[red]Gap '{args.gap_id}' not found. Use --priorities to see options.[/red]")
    elif args.auto:
        showstoppers = [g["description"] for g in PRIORITY_GAPS if g["priority"] == "SHOWSTOPPER"]
        research_multiple_gaps(showstoppers, max_papers_per_gap=args.max_papers)
    else:
        show_priorities()
        console.print("\n[bold]Actions:[/bold]")
        console.print("  1. Research a priority gap (enter ID)")
        console.print("  2. Auto-research all SHOWSTOPPER gaps")
        console.print("  3. Search preview (academic)")
        console.print("  4. Search preview (patents)")
        console.print("  5. Look up specific patents")
        choice = console.input("\n[bold cyan]Choice (1-5): [/bold cyan]").strip()
        if choice == "1":
            gid = console.input("[bold]Gap ID: [/bold]").strip()
            gap = next((g for g in PRIORITY_GAPS if g["id"].upper() == gid.upper()), None)
            if gap:
                research_gap(gap["description"], max_papers=args.max_papers)
        elif choice == "2":
            showstoppers = [g["description"] for g in PRIORITY_GAPS if g["priority"] == "SHOWSTOPPER"]
            research_multiple_gaps(showstoppers, max_papers_per_gap=args.max_papers)
        elif choice == "3":
            q = console.input("[bold]Query: [/bold]").strip()
            if q: search_preview(q, "academic")
        elif choice == "4":
            q = console.input("[bold]Query: [/bold]").strip()
            if q: search_preview(q, "patent")
        elif choice == "5":
            nums = console.input("[bold]Patent numbers (space-separated): [/bold]").strip().split()
            if nums: patent_lookup(nums)


if __name__ == "__main__":
    main()
