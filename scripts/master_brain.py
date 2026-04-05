#!/usr/bin/env python3
"""
Master Brain — Interactive Strategic Interface
=================================================
The primary human interaction layer for the ecosystem.
Cross-domain reasoning, strategic reviews, and idea evaluation.

Usage:
    # Interactive mode
    python -m scripts.master_brain

    # Single question
    python -m scripts.master_brain --question "What is our most promising solution path?"

    # Strategic review
    python -m scripts.master_brain --review

    # Evaluate an idea
    python -m scripts.master_brain --assess "Use a Fresnel screen protector for coarse correction combined with software deconvolution for fine-tuning"
"""

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from agents.master_brain import MasterBrain
from agents.domain_agent import OpticsAgent
from core.kb import get_stats, get_venture_id

console = Console()


def show_status():
    venture_id = get_venture_id()
    stats = get_stats(venture_id)
    console.print(Panel(
        f"[bold]Knowledge Base[/bold]\n"
        f"Total nodes: {stats.get('total', 0)}\n"
        f"Labels: {stats.get('by_label', {})}\n"
        f"Domains: {stats.get('by_domain', {})}\n"
        f"Avg confidence: {stats.get('avg_confidence', 0):.1f}",
        style="blue", title="Spine Status",
    ))


def display_response(response, title="Master Brain", style="magenta"):
    if not response.success:
        console.print(f"\n[red]Error:[/red] {response.error}")
        return

    console.print()
    console.print(Panel(
        Markdown(response.content),
        title=f"[bold]{title}[/bold]",
        subtitle=f"[dim]{response.model} | {response.input_tokens:,}+{response.output_tokens:,} tokens | ${response.cost_estimate:.4f} | {response.duration_ms/1000:.1f}s[/dim]",
        style=style, padding=(1, 2),
    ))


def run_with_spinner(func, message="Thinking deeply...", *args, **kwargs):
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold magenta]{message}"),
        console=console,
    ) as progress:
        task = progress.add_task(message, total=None)
        result = func(*args, **kwargs)
        progress.update(task, completed=True)
    return result


def interactive_mode(brain, optics_agent):
    console.print(Panel(
        f"[bold]Master Brain — Tier 0 Global Orchestrator[/bold]\n\n"
        f"Strategic reasoning across all domains.\n"
        f"The Master Brain sees connections between domains and identifies gaps.\n\n"
        f"Commands:\n"
        f"  [bold]review[/bold]    — Full strategic review of the venture\n"
        f"  [bold]assess[/bold]    — Evaluate an idea (type 'assess' then describe it)\n"
        f"  [bold]optics[/bold]    — Switch to Optics Domain Agent (direct mode)\n"
        f"  [bold]brain[/bold]     — Switch back to Master Brain\n"
        f"  [bold]stats[/bold]     — Show Knowledge Base status\n"
        f"  [bold]quit[/bold]      — Exit",
        style="magenta", title="Autonomous Disruptive Intelligence Ecosystem",
    ))

    active_agent = "brain"

    while True:
        console.print()
        prompt_color = "magenta" if active_agent == "brain" else "green"
        prompt_label = "Master Brain" if active_agent == "brain" else "Optics Agent"
        try:
            question = console.input(f"[bold {prompt_color}]{prompt_label} > [/bold {prompt_color}]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if not question:
            continue

        lower = question.lower()

        if lower in ("quit", "exit", "q"):
            console.print("[dim]Session ended.[/dim]")
            break
        elif lower == "stats":
            show_status()
            continue
        elif lower == "optics":
            active_agent = "optics"
            console.print("[green]Switched to Optics Agent (direct mode). Master Brain is monitoring.[/green]")
            continue
        elif lower == "brain":
            active_agent = "brain"
            console.print("[magenta]Switched to Master Brain.[/magenta]")
            continue
        elif lower == "review":
            response = run_with_spinner(brain.strategic_review, "Conducting strategic review (this may take 1-2 minutes)...")
            display_response(response, "Strategic Review", "yellow")
            continue
        elif lower.startswith("assess"):
            idea = question[6:].strip()
            if not idea:
                idea = console.input("[bold yellow]Describe the idea to evaluate: [/bold yellow]").strip()
            if idea:
                response = run_with_spinner(brain.assess_idea, "Evaluating idea...", idea)
                display_response(response, "Idea Assessment", "yellow")
            continue

        # Regular question
        if active_agent == "brain":
            response = run_with_spinner(brain.think, "Thinking across domains...", question)
            display_response(response, "Master Brain", "magenta")
        else:
            response = run_with_spinner(optics_agent.ask, "Analyzing...", question)
            display_response(response, "Optics Agent", "green")


def main():
    parser = argparse.ArgumentParser(description="Master Brain — Strategic Interface")
    parser.add_argument("--question", "-q", help="Single strategic question")
    parser.add_argument("--review", "-r", action="store_true", help="Run strategic review")
    parser.add_argument("--assess", "-a", help="Evaluate an idea")

    args = parser.parse_args()

    brain = MasterBrain()
    optics_agent = OpticsAgent()

    show_status()

    if args.review:
        response = run_with_spinner(brain.strategic_review, "Conducting strategic review...")
        display_response(response, "Strategic Review", "yellow")
    elif args.assess:
        response = run_with_spinner(brain.assess_idea, "Evaluating idea...", args.assess)
        display_response(response, "Idea Assessment", "yellow")
    elif args.question:
        response = run_with_spinner(brain.think, "Thinking...", args.question)
        display_response(response, "Master Brain", "magenta")
    else:
        interactive_mode(brain, optics_agent)


if __name__ == "__main__":
    main()
