#!/usr/bin/env python3
"""
Test USPTO ODP — Smoke test for the patents_view client
=========================================================
Runs three small searches against the USPTO Open Data Portal:

  1. Free-text search:        "vision correction display"
  2. Assignee search:         "Apple"
  3. Free-text + date range:  "augmented reality" filed 2018-2024

Prints results in a table and reports gracefully when the
API key is not configured.

Usage:
    python -m scripts.test_uspto
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load .env from ecosystem root so the key is available even
# when the script is invoked from another working directory.
_ecosystem_root = Path(__file__).resolve().parents[1]
load_dotenv(_ecosystem_root / ".env")
load_dotenv()

from extraction.sources import patents_view
from extraction.source_interface import SourceResult

console = Console()


def _print_results_table(label: str, results: list[SourceResult]) -> None:
    if not results:
        console.print(f"  [yellow]No results returned for {label}.[/yellow]")
        return

    table = Table(title=f"{label} ({len(results)} results)", show_lines=False)
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Patent #", style="cyan", no_wrap=True)
    table.add_column("Year", justify="right", width=6)
    table.add_column("Title", style="white", overflow="fold")
    table.add_column("Inventor", style="magenta", overflow="fold")
    table.add_column("API", style="green", no_wrap=True)

    for i, r in enumerate(results[:15], 1):
        title = r.title or "(no title)"
        if len(title) > 80:
            title = title[:77] + "..."
        inventor = r.authors[0] if r.authors else ""
        if len(inventor) > 30:
            inventor = inventor[:27] + "..."
        table.add_row(
            str(i),
            r.patent_number or "-",
            str(r.year) if r.year else "-",
            title,
            inventor,
            r.source_api,
        )

    console.print(table)


def run_test(label: str, fn, *args, **kwargs) -> int:
    console.print(f"\n[bold blue]{label}[/bold blue]")
    console.print(f"  args={args} kwargs={kwargs}")
    try:
        results = fn(*args, **kwargs)
    except Exception as e:
        console.print(f"  [red]FAIL[/red] {type(e).__name__}: {e}")
        return 0

    if results:
        console.print(f"  [green]OK[/green] {len(results)} results returned")
    else:
        console.print(f"  [yellow]OK[/yellow] (call succeeded, 0 results)")

    _print_results_table(label, results)
    return len(results)


def main() -> int:
    console.print("[bold]USPTO ODP Smoke Test[/bold]")

    api_key = os.getenv("USPTO_ODP_API_KEY", "").strip()
    if not api_key:
        console.print(
            "[red]FAIL[/red] USPTO_ODP_API_KEY is not set in .env. "
            "Add it and rerun. The patents_view client returns [] "
            "without a key, so all tests would be vacuous."
        )
        return 1

    masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
    console.print(f"  [green]OK[/green] USPTO_ODP_API_KEY found ({masked})")

    total = 0
    total += run_test(
        "Test 1: free-text search 'vision correction display'",
        patents_view.search,
        "vision correction display",
        limit=10,
    )

    total += run_test(
        "Test 2: assignee search 'Apple'",
        patents_view.search_by_assignee,
        "Apple",
        limit=10,
    )

    total += run_test(
        "Test 3: 'augmented reality' filed 2018-2024",
        patents_view.search,
        "augmented reality",
        limit=10,
        year_range="2018-2024",
    )

    console.print(
        f"\n[bold]Done.[/bold] Total results across the three tests: {total}"
    )
    return 0 if total > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
