#!/usr/bin/env python3
"""
Ask Agent — Interactive Domain Agent Query
=============================================
Ask questions to Domain Agents, grounded in the Knowledge Base.

Usage:
    # Interactive mode (conversation)
    python -m scripts.ask_agent

    # Single question
    python -m scripts.ask_agent --question "What are the fundamental limits of software-only vision correction?"

    # Use Opus for complex reasoning
    python -m scripts.ask_agent --question "..." --complex

    # Run gap analysis
    python -m scripts.ask_agent --gaps
"""

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from agents.domain_agent import OpticsAgent
from core.kb import get_stats, get_venture_id

console = Console()


def show_kb_status():
    """Display current Knowledge Base status."""
    venture_id = get_venture_id()
    stats = get_stats(venture_id)
    console.print(Panel(
        f"[bold]Knowledge Base[/bold]\n"
        f"Total nodes: {stats.get('total', 0)}\n"
        f"Labels: {stats.get('by_label', {})}\n"
        f"Domains: {stats.get('by_domain', {})}\n"
        f"Avg confidence: {stats.get('avg_confidence', 0):.1f}",
        style="blue",
        title="Spine Status",
    ))


def ask_question(agent, question: str, complexity: str = "standard"):
    """Ask a single question and display the response."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"{'Deep thinking' if complexity == 'complex' else 'Analyzing'}...",
            total=None
        )
        response = agent.ask(question, complexity=complexity)
        progress.update(task, completed=True)

    if not response.success:
        console.print(f"\n[red]Error:[/red] {response.error}")
        return

    # Display the response
    console.print()
    console.print(Panel(
        Markdown(response.content),
        title=f"[bold]{agent.display_name}[/bold]",
        subtitle=f"[dim]{response.model} | {response.input_tokens:,}+{response.output_tokens:,} tokens | ${response.cost_estimate:.4f} | {response.duration_ms/1000:.1f}s[/dim]",
        style="green",
        padding=(1, 2),
    ))


def run_gap_analysis(agent):
    """Run gap analysis on the Knowledge Base."""
    console.print("\n[bold blue]Running gap analysis on the Knowledge Base...[/bold blue]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing knowledge coverage...", total=None)
        response = agent.identify_gaps()
        progress.update(task, completed=True)

    if not response.success:
        console.print(f"\n[red]Error:[/red] {response.error}")
        return

    console.print()
    console.print(Panel(
        Markdown(response.content),
        title="[bold]Knowledge Gap Analysis[/bold]",
        subtitle=f"[dim]{response.model} | ${response.cost_estimate:.4f}[/dim]",
        style="yellow",
        padding=(1, 2),
    ))


def interactive_mode(agent, complexity: str = "standard"):
    """Interactive conversation with the Domain Agent."""
    console.print(Panel(
        f"[bold]Interactive Mode — {agent.display_name}[/bold]\n\n"
        f"Ask questions grounded in your Knowledge Base.\n"
        f"The agent will cite facts with confidence levels and flag knowledge gaps.\n\n"
        f"Commands:\n"
        f"  [bold]gaps[/bold]     — Run gap analysis on the Knowledge Base\n"
        f"  [bold]stats[/bold]    — Show Knowledge Base status\n"
        f"  [bold]complex[/bold]  — Toggle Opus mode for deeper reasoning\n"
        f"  [bold]quit[/bold]     — Exit",
        style="blue",
        title="Optics Agent",
    ))

    current_complexity = complexity

    while True:
        console.print()
        try:
            question = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not question:
            continue

        lower = question.lower()

        if lower in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break
        elif lower == "gaps":
            run_gap_analysis(agent)
            continue
        elif lower == "stats":
            show_kb_status()
            continue
        elif lower == "complex":
            if current_complexity == "standard":
                current_complexity = "complex"
                console.print("[yellow]Switched to Opus (complex reasoning mode)[/yellow]")
            else:
                current_complexity = "standard"
                console.print("[green]Switched to Sonnet (standard mode)[/green]")
            continue

        ask_question(agent, question, current_complexity)


def main():
    parser = argparse.ArgumentParser(description="Query the Optics Domain Agent")
    parser.add_argument("--question", "-q", help="Single question (non-interactive)")
    parser.add_argument("--complex", "-c", action="store_true",
                       help="Use Opus for deeper reasoning")
    parser.add_argument("--gaps", "-g", action="store_true",
                       help="Run gap analysis on the Knowledge Base")

    args = parser.parse_args()

    # Initialize the agent
    agent = OpticsAgent()

    # Show KB status
    show_kb_status()

    complexity = "complex" if args.complex else "standard"

    if args.gaps:
        run_gap_analysis(agent)
    elif args.question:
        ask_question(agent, args.question, complexity)
    else:
        interactive_mode(agent, complexity)


if __name__ == "__main__":
    main()
