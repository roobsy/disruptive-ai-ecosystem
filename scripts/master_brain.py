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

# Import PRIORITY_GAPS from research script for gap fill
from scripts.research import PRIORITY_GAPS, show_priorities, search_preview, patent_lookup


def interactive_mode(brain, optics_agent):
    console.print(f"\n[dim]Type [bold]?[/bold] for help, or ask a question.[/dim]\n")

    mode = "brain"
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
                session.log("review (done)", mode, cost=response.cost_estimate if response.success else 0)
                continue

            if cmd == "assess":
                idea = args
                if not idea:
                    idea = console.input("[bold yellow]Describe the idea to evaluate: [/bold yellow]").strip()
                if idea:
                    session.log(f"assess {idea[:50]}...", mode)
                    response = run_with_spinner(brain.assess_idea, "Evaluating idea...", idea)
                    display_response(response, "Idea Assessment", "yellow")
                    session.log("assess (done)", mode, cost=response.cost_estimate if response.success else 0)
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

            if cmd == "complex":
                # Toggle is tracked per-question, not globally in this unified interface
                console.print("[dim]In unified mode, Opus is used for Master Brain and Sonnet for agents by default.[/dim]")
                session.log("complex", mode)
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
