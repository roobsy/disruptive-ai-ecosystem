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

from agents.master_brain import MasterBrain
from agents.domain_agent import OpticsAgent
from agents.research_agent import research_gap, research_multiple_gaps
from extraction.source_router import search_academic, search_patents, lookup_known_patents
from core.cli_helpers import (
    console, session,
    parse_input, handle_global_command, get_prompt,
    show_status, show_help_brief, display_response, run_with_spinner,
    show_switch_menu, MODE_LABELS, MODE_COLORS,
)

from scripts.research import PRIORITY_GAPS, show_priorities, search_preview, patent_lookup


def interactive_mode(agent, brain):
    console.print(f"\n[dim]Type [bold]?[/bold] for help, or ask a question.[/dim]\n")

    mode = "optics"
    mode_history = []
    current_complexity = "standard"

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
                response = run_with_spinner(agent.identify_gaps, "Analyzing knowledge coverage...")
                display_response(response, "Knowledge Gap Analysis", "yellow")
                if response.success:
                    session.log("gaps (done)", mode, cost=response.cost_estimate)
                continue

            if cmd == "complex":
                if current_complexity == "standard":
                    current_complexity = "complex"
                    console.print("[yellow]Switched to Opus (complex reasoning mode)[/yellow]")
                else:
                    current_complexity = "standard"
                    console.print("[green]Switched to Sonnet (standard mode)[/green]")
                session.log("complex", mode)
                continue

        # --- Free-text question ---
        if cmd == "question":
            session.log(f"Q: {raw[:50]}...", mode)
            if mode == "brain":
                response = run_with_spinner(brain.think, "Thinking across domains...", raw)
                display_response(response, "Master Brain", "magenta")
            elif mode == "optics":
                response = run_with_spinner(agent.ask, "Analyzing...", raw, current_complexity)
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
    parser = argparse.ArgumentParser(description="Query the Optics Domain Agent")
    parser.add_argument("--question", "-q", help="Single question (non-interactive)")
    parser.add_argument("--complex", "-c", action="store_true",
                       help="Use Opus for deeper reasoning")
    parser.add_argument("--gaps", "-g", action="store_true",
                       help="Run gap analysis on the Knowledge Base")

    args = parser.parse_args()

    agent = OpticsAgent()
    brain = MasterBrain()

    show_status()

    complexity = "complex" if args.complex else "standard"

    if args.gaps:
        response = run_with_spinner(agent.identify_gaps, "Analyzing knowledge coverage...")
        display_response(response, "Knowledge Gap Analysis", "yellow")
    elif args.question:
        response = run_with_spinner(agent.ask, "Analyzing...", args.question, complexity)
        display_response(response, "Optics Agent", "green")
    else:
        interactive_mode(agent, brain)


if __name__ == "__main__":
    main()
