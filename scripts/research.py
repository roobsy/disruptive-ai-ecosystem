#!/usr/bin/env python3
"""
Research ��� Autonomous Multi-Tier Knowledge Acquisition
=========================================================
Searches across ALL data sources (academic, patent, web),
ranks results, and extracts into the Knowledge Base.

Usage:
    python -m scripts.research                           # Interactive mode
    python -m scripts.research --priorities              # Show Master Brain's gap priorities
    python -m scripts.research --search "query"          # Preview search (no extraction)
    python -m scripts.research --gap-id GAP1             # Research a priority gap
    python -m scripts.research --gap "description"       # Research a custom gap
    python -m scripts.research --auto                    # Auto-research all SHOWSTOPPER gaps
    python -m scripts.research --patents "query"         # Patent-only search preview
    python -m scripts.research --lookup US12141346       # Look up a specific patent
"""

import argparse
from rich.table import Table

from agents.research_agent import research_gap, research_multiple_gaps
from agents.master_brain import MasterBrain
from agents.domain_agent import OpticsAgent
from extraction.source_router import search_academic, search_patents, lookup_known_patents
from core.cli_helpers import (
    console, session,
    parse_input, handle_global_command, get_prompt,
    show_status, display_response, run_with_spinner,
    show_switch_menu, MODE_LABELS, MODE_COLORS,
)

# ── Master Brain's Priority Gaps ──
PRIORITY_GAPS = [
    {"id": "GAP1", "priority": "SHOWSTOPPER", "title": "Patent Landscape -- Vision Correcting Displays",
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
        pdf = "Y" if r.has_open_access else ""
        table.add_row(str(i), stype, str(r.year or "?"), str(r.citation_count),
                     pdf, r.source_api[:12], r.title[:50])
    console.print(table)


def patent_lookup(patent_numbers: list[str]):
    from rich.panel import Panel
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


def interactive_mode():
    """Interactive research mode with full help and navigation."""
    brain = MasterBrain()
    optics_agent = OpticsAgent()

    console.print(f"\n[dim]Type [bold]?[/bold] for help, or enter a command.[/dim]\n")

    mode = "research"
    mode_history = []

    while True:
        console.print()
        try:
            raw = console.input(get_prompt(mode)).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if not raw:
            continue

        cmd, args = parse_input(raw, mode)

        # --- Quit ---
        if cmd == "quit":
            console.print("[dim]Session ended.[/dim]")
            break

        # --- Global commands ---
        if handle_global_command(cmd, args, mode):
            session.log(raw, mode)
            continue

        # --- Navigation ---
        if cmd == "switch":
            show_switch_menu(mode)
            session.log(raw, mode)
            continue

        if cmd == "nav":
            target = args
            if target == mode:
                console.print(f"[dim]Already in {MODE_LABELS[mode]}.[/dim]")
            else:
                mode_history.append(mode)
                mode = target
                color = MODE_COLORS[mode]
                console.print(f"[{color}]Switched to {MODE_LABELS[mode]}.[/{color}]")
            session.log(raw, mode)
            continue

        if cmd == "back":
            if mode_history:
                mode = mode_history.pop()
                color = MODE_COLORS[mode]
                console.print(f"[{color}]Back to {MODE_LABELS[mode]}.[/{color}]")
            else:
                console.print("[dim]No previous mode to return to.[/dim]")
            session.log(raw, mode)
            continue

        # --- Brain-specific commands ---
        if mode == "brain":
            if cmd == "review":
                session.log("review", mode)
                response = run_with_spinner(brain.strategic_review, "Conducting strategic review (this may take 1-2 minutes)...")
                display_response(response, "Strategic Review", "yellow")
                if response.success:
                    session.log("review (done)", mode, cost=response.cost_estimate)
                continue

            if cmd == "assess":
                idea = args
                if not idea:
                    idea = console.input("[bold yellow]Describe the idea to evaluate: [/bold yellow]").strip()
                if idea:
                    session.log(f"assess {idea[:50]}...", mode)
                    response = run_with_spinner(brain.assess_idea, "Evaluating idea...", idea)
                    display_response(response, "Idea Assessment", "yellow")
                    if response.success:
                        session.log("assess (done)", mode, cost=response.cost_estimate)
                continue

            if cmd == "gaps":
                show_priorities()
                session.log("gaps", mode)
                continue

            if cmd == "gaps_fill":
                gap_id = args.upper()
                gap = next((g for g in PRIORITY_GAPS if g["id"] == gap_id), None)
                if gap:
                    session.log(f"gaps fill {gap_id}", mode)
                    research_gap(gap["description"], max_papers=5)
                else:
                    console.print(f"[red]Gap '{args}' not found. Type 'gaps' to see options.[/red]")
                continue

        # --- Research-specific commands ---
        if mode == "research":
            if cmd == "priorities":
                show_priorities()
                session.log("priorities", mode)
                continue

            if cmd == "search":
                session.log(f"search {args[:40]}...", mode)
                search_preview(args, "academic")
                continue

            if cmd == "patents":
                session.log(f"patents {args[:40]}...", mode)
                search_preview(args, "patent")
                continue

            if cmd == "lookup":
                nums = args.split()
                if nums:
                    session.log(f"lookup {' '.join(nums)}", mode)
                    patent_lookup(nums)
                else:
                    console.print("[yellow]Usage: lookup US12141346 US10234692[/yellow]")
                continue

            if cmd == "gap":
                gap_id = args.upper()
                gap = next((g for g in PRIORITY_GAPS if g["id"] == gap_id), None)
                if gap:
                    session.log(f"gap {gap_id}", mode)
                    research_gap(gap["description"], max_papers=5)
                else:
                    console.print(f"[red]Gap '{args}' not found. Type 'priorities' to see options.[/red]")
                continue

            if cmd == "auto":
                session.log("auto", mode)
                showstoppers = [g["description"] for g in PRIORITY_GAPS if g["priority"] == "SHOWSTOPPER"]
                research_multiple_gaps(showstoppers, max_papers_per_gap=5)
                continue

        # --- Optics-specific commands ---
        if mode == "optics":
            if cmd == "gaps":
                session.log("gaps", mode)
                response = run_with_spinner(optics_agent.identify_gaps, "Analyzing knowledge coverage...")
                display_response(response, "Knowledge Gap Analysis", "yellow")
                if response.success:
                    session.log("gaps (done)", mode, cost=response.cost_estimate)
                continue

        # --- Free-text question ---
        if cmd == "question":
            session.log(f"Q: {raw[:50]}...", mode)
            if mode == "brain":
                response = run_with_spinner(brain.think, "Thinking across domains...", raw)
                display_response(response, "Master Brain", "magenta")
            elif mode == "optics":
                response = run_with_spinner(optics_agent.ask, "Analyzing...", raw)
                display_response(response, "Optics Agent", "green")
            elif mode == "research":
                console.print("[yellow]Research mode accepts commands, not free questions. Type ? for help.[/yellow]")
                continue
            if response.success:
                session.log("(answered)", mode, cost=response.cost_estimate)
            continue

        # --- Unknown ---
        console.print("[yellow]Unknown command. Type ? for help.[/yellow]")
        session.log(f"unknown: {raw[:30]}", mode)


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
        show_status()
        interactive_mode()


if __name__ == "__main__":
    main()
