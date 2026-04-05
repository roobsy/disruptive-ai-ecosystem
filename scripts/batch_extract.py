#!/usr/bin/env python3
"""
Batch Extract — Load Multiple Papers into the Knowledge Base
================================================================
Extracts a curated list of papers relevant to the venture.

Usage:
    python -m scripts.batch_extract
    python -m scripts.batch_extract --list  # Show papers without extracting
"""

import argparse
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scripts.extract_paper import extract_paper

console = Console()

# ── Curated paper list for Vision Correction Display venture ──
VISION_CORRECTION_PAPERS = [
    {
        "id": "2501.01450",
        "context": "Real-time computational VCD, PSF deconvolution, Wiener filter, YUV color space optimization",
        "note": "Dec 2024 — Real-time deconvolution-based VCD prototype",
    },
    {
        "id": "1407.7079",
        "context": "Light field display vision correction, computational prefiltering, pinhole array, MIT Berkeley SIGGRAPH",
        "note": "2014 — Seminal MIT/Berkeley eyeglasses-free display paper",
    },
    {
        "id": "2010.04770",
        "context": "Neural display optimization, learned optics, end-to-end display design, differentiable rendering",
        "note": "2020 — Neural approaches to computational display design",
    },
    {
        "id": "1801.07478",
        "context": "Deep optics, end-to-end camera lens design with neural networks, computational imaging",
        "note": "2018 — Deep optics: joint lens and image processing optimization",
    },
    {
        "id": "2012.07928",
        "context": "Learned vision correction, neural aberration correction, wavefront sensing",
        "note": "2020 — Learned approach to vision aberration correction",
    },
    {
        "id": "2309.09928",
        "context": "Smartphone eye tracking, gaze estimation, mobile devices, front camera",
        "note": "2023 — Eye tracking on smartphones using front camera",
    },
    {
        "id": "1903.10860",
        "context": "Holographic near-eye display, vision correction, VR AR head-mounted display",
        "note": "2019 — Holographic display for vision correction",
    },
]


def show_list():
    table = Table(title="Curated Papers for Vision Correction Venture", show_lines=True)
    table.add_column("ArXiv ID", style="cyan", width=14)
    table.add_column("Description", width=55)
    table.add_column("Focus Context", width=40)

    for paper in VISION_CORRECTION_PAPERS:
        table.add_row(
            paper["id"],
            paper["note"],
            paper["context"][:40] + "..." if len(paper["context"]) > 40 else paper["context"],
        )

    console.print(table)
    console.print(f"\n  [bold]{len(VISION_CORRECTION_PAPERS)} papers total[/bold]")


def run_batch():
    console.print(Panel(
        f"[bold]Batch Extraction — {len(VISION_CORRECTION_PAPERS)} papers[/bold]\n\n"
        f"This will extract and epistemically label each paper.\n"
        f"Estimated cost: ${len(VISION_CORRECTION_PAPERS) * 0.15:.2f} - ${len(VISION_CORRECTION_PAPERS) * 0.30:.2f}\n"
        f"Estimated time: {len(VISION_CORRECTION_PAPERS) * 1.5:.0f} - {len(VISION_CORRECTION_PAPERS) * 2.5:.0f} minutes",
        style="blue",
    ))

    proceed = console.input("\n[bold]Proceed? (y/n): [/bold]").strip().lower()
    if proceed != "y":
        console.print("[dim]Cancelled.[/dim]")
        return

    succeeded = 0
    failed = 0
    total_cost = 0.0

    for i, paper in enumerate(VISION_CORRECTION_PAPERS, 1):
        console.print(f"\n{'='*60}")
        console.print(f"[bold cyan]Paper {i}/{len(VISION_CORRECTION_PAPERS)}:[/bold cyan] {paper['note']}")
        console.print(f"{'='*60}")

        try:
            extract_paper(paper["id"], context=paper["context"])
            succeeded += 1
        except Exception as e:
            console.print(f"  [red]Failed:[/red] {e}")
            failed += 1

        # Brief pause between extractions to be polite to APIs
        if i < len(VISION_CORRECTION_PAPERS):
            time.sleep(2)

    console.print(f"\n{'='*60}")
    console.print(Panel(
        f"[bold]Batch Complete[/bold]\n\n"
        f"Succeeded: {succeeded}\n"
        f"Failed: {failed}\n"
        f"Total: {succeeded + failed}",
        style="green" if failed == 0 else "yellow",
    ))


def main():
    parser = argparse.ArgumentParser(description="Batch extract papers")
    parser.add_argument("--list", "-l", action="store_true", help="Show paper list without extracting")
    args = parser.parse_args()

    if args.list:
        show_list()
    else:
        run_batch()


if __name__ == "__main__":
    main()
