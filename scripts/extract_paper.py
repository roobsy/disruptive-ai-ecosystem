#!/usr/bin/env python3
"""
Extract Paper — Phase 0 Main Script
=====================================
Takes an ArXiv URL or paper ID, downloads the PDF,
runs it through the Epistemic Filter, and stores
labeled knowledge nodes in the Supabase Knowledge Base.

Usage:
    python -m scripts.extract_paper 2501.01450
    python -m scripts.extract_paper https://arxiv.org/abs/2501.01450
    python -m scripts.extract_paper 2501.01450 --context "Vision correction display research"
"""

import sys
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.epistemic_filter import extract_from_pdf
from core.kb import (
    get_venture_id,
    store_node,
    store_provenance,
    log_extraction,
    check_already_extracted,
    get_stats,
)
from extraction.sources.arxiv import download_pdf, get_paper_metadata

console = Console()


def extract_paper(paper_id: str, context: str = "", force: bool = False):
    """Full pipeline: download -> label -> store."""

    console.print(Panel(
        f"[bold]Extracting:[/bold] {paper_id}",
        title="Epistemic Extraction Engine",
        style="blue",
    ))

    # ── Step 1: Get venture ID ────────────────────────────
    with console.status("[bold blue]Connecting to Knowledge Base..."):
        try:
            venture_id = get_venture_id()
            console.print(f"  [green]OK[/green] Connected to venture")
        except Exception as e:
            console.print(f"  [red]FAIL Failed:[/red] {e}")
            console.print("\n  [yellow]Have you run setup_supabase.sql?[/yellow]")
            return

    # ── Step 2: Check if already extracted ────────────────
    metadata = get_paper_metadata(paper_id)
    source_url = metadata.get("url", paper_id)

    if not force and check_already_extracted(venture_id, source_url):
        console.print(f"  [yellow]\u26A0[/yellow] Already extracted: {source_url}")
        console.print("  Use --force to re-extract.")
        return

    # Show metadata
    if metadata.get("title"):
        console.print(f"\n  [bold]Title:[/bold] {metadata['title']}")
    if metadata.get("authors"):
        console.print(f"  [bold]Authors:[/bold] {', '.join(metadata['authors'][:5])}")
    if metadata.get("year"):
        console.print(f"  [bold]Year:[/bold] {metadata['year']}")
    console.print()

    # ── Step 3: Download PDF ──────────────────────────────
    log_extraction(venture_id, source_url, status="processing")

    with console.status("[bold blue]Downloading PDF..."):
        pdf_path = download_pdf(paper_id)
        if not pdf_path:
            console.print("  [red]FAIL Download failed[/red]")
            log_extraction(venture_id, source_url, status="failed",
                         error_message="PDF download failed")
            return
        console.print(f"  [green]OK[/green] PDF downloaded: {pdf_path}")

    # ── Step 4: Run Epistemic Filter ──────────────────────
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running Epistemic Filter (this may take 30-60 seconds)...", total=None)
        response = extract_from_pdf(str(pdf_path), extra_context=context)
        progress.update(task, completed=True)

    if not response.success:
        console.print(f"\n  [red]FAIL Extraction failed:[/red] {response.error}")
        log_extraction(venture_id, source_url, status="failed",
                     error_message=response.error,
                     cost_input_tokens=response.input_tokens,
                     cost_output_tokens=response.output_tokens)
        return

    console.print(f"  [green]OK[/green] Epistemic analysis complete")
    console.print(f"  [dim]Model: {response.model} | "
                  f"Tokens: {response.input_tokens:,} in / {response.output_tokens:,} out | "
                  f"Cost: ${response.cost_estimate:.4f} | "
                  f"Time: {response.duration_ms / 1000:.1f}s[/dim]")

    if not response.parsed:
        console.print(f"\n  [red]FAIL Could not parse JSON response[/red]")
        console.print(f"  Raw response:\n{response.content[:500]}")
        log_extraction(venture_id, source_url, status="failed",
                     error_message="JSON parse failed",
                     cost_input_tokens=response.input_tokens,
                     cost_output_tokens=response.output_tokens)
        return

    # ── Step 5: Store in Knowledge Base ──────────────────
    nodes_data = response.parsed.get("nodes", [])
    source_summary = response.parsed.get("source_summary", "")
    source_type = response.parsed.get("source_type", "academic_paper")

    console.print(f"\n  [bold]Source summary:[/bold] {source_summary[:200]}")
    console.print(f"  [bold]Nodes extracted:[/bold] {len(nodes_data)}")
    console.print()

    stored_count = 0
    with console.status("[bold blue]Storing knowledge nodes..."):
        for node_data in nodes_data:
            try:
                # Store the knowledge node
                node = store_node(
                    venture_id=venture_id,
                    epistemic_label=node_data.get("epistemic_label", "cognitive_framework"),
                    content=node_data.get("content", ""),
                    summary=node_data.get("summary"),
                    confidence=node_data.get("confidence", 50),
                    decay_rate=node_data.get("decay_rate", 365),
                    domain=node_data.get("domain"),
                    tags=node_data.get("tags", []),
                    created_by="extraction_engine",
                )

                # Store provenance
                if node:
                    store_provenance(
                        node_id=node["id"],
                        source_type=source_type,
                        source_url=source_url,
                        source_title=metadata.get("title"),
                        source_authors=metadata.get("authors", []),
                        source_doi=metadata.get("arxiv_id"),
                        source_year=metadata.get("year"),
                        credibility_tier="tier1_academic",
                    )
                    stored_count += 1

            except Exception as e:
                console.print(f"  [yellow]\u26A0 Failed to store node:[/yellow] {e}")

    # ── Step 6: Log the extraction ────────────────────────
    log_extraction(
        venture_id=venture_id,
        source_url=source_url,
        source_type=source_type,
        status="completed",
        nodes_created=stored_count,
        cost_input_tokens=response.input_tokens,
        cost_output_tokens=response.output_tokens,
        processing_time_ms=response.duration_ms,
    )

    # ── Step 7: Display results ───────────────────────────
    console.print(f"\n  [green]OK[/green] Stored {stored_count} knowledge nodes\n")

    # Show a summary table
    table = Table(title="Extracted Knowledge Nodes", show_lines=True)
    table.add_column("Label", style="bold", width=20)
    table.add_column("Conf.", width=6, justify="right")
    table.add_column("Domain", width=14)
    table.add_column("Summary", width=50)

    label_colors = {
        "axiomatic_fact": "green",
        "experimental_result": "yellow",
        "cognitive_framework": "red",
        "experience_data": "blue",
    }

    for node_data in nodes_data:
        label = node_data.get("epistemic_label", "unknown")
        color = label_colors.get(label, "white")
        table.add_row(
            f"[{color}]{label}[/{color}]",
            str(node_data.get("confidence", "?")),
            node_data.get("domain", ""),
            node_data.get("summary", "")[:50],
        )

    console.print(table)

    # Show KB stats
    console.print()
    stats = get_stats(venture_id)
    console.print(Panel(
        f"[bold]Knowledge Base Status[/bold]\n"
        f"Total nodes: {stats.get('total', 0)}\n"
        f"By label: {stats.get('by_label', {})}\n"
        f"By domain: {stats.get('by_domain', {})}\n"
        f"Avg confidence: {stats.get('avg_confidence', 0):.1f}",
        style="green",
    ))


def main():
    parser = argparse.ArgumentParser(
        description="Extract and epistemically label an ArXiv paper"
    )
    parser.add_argument(
        "paper",
        help="ArXiv paper ID or URL (e.g., 2501.01450 or https://arxiv.org/abs/2501.01450)"
    )
    parser.add_argument(
        "--context", "-c",
        default="",
        help="Additional context to guide extraction (e.g., 'Focus on optical physics')"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-extraction even if paper was already processed"
    )

    args = parser.parse_args()
    extract_paper(args.paper, context=args.context, force=args.force)


if __name__ == "__main__":
    main()
