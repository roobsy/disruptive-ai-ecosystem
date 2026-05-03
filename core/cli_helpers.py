"""
CLI Helpers — Shared help system, command parser, and session tracker
======================================================================
Provides a consistent help and navigation system across all interactive CLIs.
"""

import os
import time
from dataclasses import dataclass, field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.kb import get_stats, get_venture_id

console = Console()


# ---------------------------------------------------------------------------
# Command definitions
# ---------------------------------------------------------------------------

@dataclass
class CommandDef:
    name: str
    aliases: list[str]
    short: str
    detail: str
    example: str
    category: str  # "global", "nav", "brain", "research", "domain"


GLOBAL_COMMANDS: list[CommandDef] = [
    CommandDef("help", ["?"], "Show available commands", "Show all commands for the current context. Use 'help all' for full descriptions, or 'help <cmd>' for one command.", "help | ? | help review | ?assess", "global"),
    CommandDef("status", ["stats"], "Show KB status", "Display current Knowledge Base node counts, domains, epistemic labels, and average confidence.", "status", "global"),
    CommandDef("where", ["pwd"], "Show current agent/mode", "Display which agent or mode you are currently interacting with.", "where", "global"),
    CommandDef("history", [], "Show session history", "List all commands run this session with timestamps and API costs.", "history", "global"),
    CommandDef("cost", [], "Show session API cost", "Display total API cost and call count for this session.", "cost", "global"),
    CommandDef("clear", ["cls"], "Clear the screen", "Clear the terminal screen.", "clear", "global"),
    CommandDef("quit", ["exit", "q"], "Exit the program", "End the current session and exit.", "quit", "global"),
]

NAV_COMMANDS: list[CommandDef] = [
    CommandDef("switch", [">"], "Show agents to switch to", "List all available agents and modes you can navigate to.", "switch | >", "nav"),
    CommandDef(">brain", [">master"], "Switch to Master Brain", "Navigate to Master Brain for strategic reasoning, reviews, and idea assessment.", ">brain", "nav"),
    CommandDef(">optics", [], "Switch to Optics Agent", "Navigate to the Optics Domain Agent for domain-specific questions and gap analysis.", ">optics", "nav"),
    CommandDef(">research", [], "Switch to Research Agent", "Navigate to the Research Agent for search previews, gap research, and patent lookups.", ">research", "nav"),
    CommandDef("back", [], "Return to previous agent", "Switch back to the agent you were using before the current one.", "back", "nav"),
]

BRAIN_COMMANDS: list[CommandDef] = [
    CommandDef("review", [], "Run strategic review", "Conduct a comprehensive strategic review of the venture using Opus. Analyzes KB coverage, constraints, solution paths, gaps, and recommends next actions. Takes 1-2 minutes.", "review", "brain"),
    CommandDef("assess", [], "Evaluate an idea", "Submit an idea for the Master Brain to evaluate. It will play both advocate and red team, assessing physics viability, patent risk, and competitive exposure.", "assess Use a Fresnel lens screen protector for coarse correction combined with software deconvolution", "brain"),
    CommandDef("gaps", [], "Show priority gaps", "Display the Master Brain's prioritized list of knowledge gaps (SHOWSTOPPER, CRITICAL, STRATEGIC).", "gaps | gaps fill GAP5", "brain"),
]

RESEARCH_COMMANDS: list[CommandDef] = [
    CommandDef("search", [], "Preview academic search", "Run a search across academic sources (Semantic Scholar, OpenAlex, CrossRef, PubMed) and display results without extracting.", "search vision correcting display MTF diopter", "research"),
    CommandDef("patents", [], "Preview patent search", "Run a search across patent sources (PatentsView, EPO, Google Patents) and display results.", "patents vision correction display precompensation", "research"),
    CommandDef("lookup", [], "Look up specific patents", "Look up one or more patents by number and display their details.", "lookup US12141346 US10234692", "research"),
    CommandDef("gap", [], "Research a specific gap", "Trigger the full research pipeline for a priority gap: query generation -> discovery -> ranking -> extraction.", "gap GAP4 | gap GAP1", "research"),
    CommandDef("auto", [], "Auto-research SHOWSTOPPER gaps", "Automatically research all gaps with SHOWSTOPPER priority in sequence.", "auto", "research"),
    CommandDef("priorities", [], "Show priority gaps table", "Display the prioritized gap table with IDs, severity, and titles.", "priorities", "research"),
]

DOMAIN_COMMANDS: list[CommandDef] = [
    CommandDef("gaps", [], "Run gap analysis", "Ask the domain agent to analyze the KB and identify knowledge gaps in its domain.", "gaps", "domain"),
    CommandDef("complex", [], "Toggle Opus mode", "Switch between Sonnet (fast, standard) and Opus (deep reasoning) for domain questions.", "complex", "domain"),
]


# Map of mode -> available command lists
MODE_COMMANDS = {
    "brain": [GLOBAL_COMMANDS, NAV_COMMANDS, BRAIN_COMMANDS],
    "optics": [GLOBAL_COMMANDS, NAV_COMMANDS, DOMAIN_COMMANDS],
    "research": [GLOBAL_COMMANDS, NAV_COMMANDS, RESEARCH_COMMANDS],
}

MODE_COLORS = {
    "brain": "magenta",
    "optics": "green",
    "research": "cyan",
}

MODE_LABELS = {
    "brain": "Master Brain",
    "optics": "Optics Agent",
    "research": "Research",
}


# ---------------------------------------------------------------------------
# Session tracker
# ---------------------------------------------------------------------------

@dataclass
class SessionEntry:
    timestamp: float
    command: str
    mode: str
    cost: float = 0.0
    note: str = ""


@dataclass
class Session:
    start_time: float = field(default_factory=time.time)
    entries: list[SessionEntry] = field(default_factory=list)
    total_cost: float = 0.0
    api_calls: int = 0

    def log(self, command: str, mode: str, cost: float = 0.0, note: str = ""):
        self.entries.append(SessionEntry(time.time(), command, mode, cost, note))
        if cost > 0:
            self.total_cost += cost
            self.api_calls += 1

    def add_cost(self, cost: float):
        self.total_cost += cost
        self.api_calls += 1


session = Session()


# ---------------------------------------------------------------------------
# Help display functions
# ---------------------------------------------------------------------------

def _all_commands_for_mode(mode: str) -> list[CommandDef]:
    """Return a flat list of all commands available in the given mode."""
    result = []
    for cmd_list in MODE_COMMANDS.get(mode, MODE_COMMANDS["brain"]):
        result.extend(cmd_list)
    return result


def _find_command(name: str, mode: str) -> CommandDef | None:
    """Find a command by name or alias."""
    name = name.lower().strip()
    for cmd in _all_commands_for_mode(mode):
        if cmd.name == name or name in cmd.aliases:
            return cmd
    return None


def show_help_brief(mode: str):
    """Show compact command list for current mode."""
    table = Table(title=f"Commands ({MODE_LABELS.get(mode, mode)})", show_lines=False, padding=(0, 2))
    table.add_column("Command", style="bold cyan", min_width=16)
    table.add_column("Aliases", style="dim", min_width=10)
    table.add_column("Description", min_width=30)

    for cmd in _all_commands_for_mode(mode):
        aliases = ", ".join(cmd.aliases) if cmd.aliases else ""
        table.add_row(cmd.name, aliases, cmd.short)

    console.print()
    console.print(table)
    console.print("\n[dim]Type[/dim] [bold]?<cmd>[/bold] [dim]for details, or[/dim] [bold]help all[/bold] [dim]for everything.[/dim]")


def show_help_full(mode: str):
    """Show full help with descriptions and examples."""
    categories = [
        ("Global", GLOBAL_COMMANDS),
        ("Navigation", NAV_COMMANDS),
    ]
    if mode == "brain":
        categories.append(("Master Brain", BRAIN_COMMANDS))
    elif mode == "research":
        categories.append(("Research", RESEARCH_COMMANDS))
    elif mode == "optics":
        categories.append(("Domain Agent", DOMAIN_COMMANDS))

    lines = []
    for cat_name, cmds in categories:
        lines.append(f"\n[bold underline]{cat_name}[/bold underline]\n")
        for cmd in cmds:
            aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
            lines.append(f"  [bold cyan]{cmd.name}[/bold cyan]{aliases}")
            lines.append(f"    {cmd.detail}")
            lines.append(f"    [dim]Example: {cmd.example}[/dim]\n")

    console.print(Panel(
        "\n".join(lines),
        title="[bold]Full Command Reference[/bold]",
        style="blue",
        padding=(1, 2),
    ))


def show_help_command(name: str, mode: str):
    """Show detailed help for a specific command."""
    cmd = _find_command(name, mode)
    if not cmd:
        console.print(f"[yellow]Unknown command '{name}'. Type ? for help.[/yellow]")
        return

    aliases = f"  Aliases: {', '.join(cmd.aliases)}" if cmd.aliases else ""
    console.print(Panel(
        f"[bold cyan]{cmd.name}[/bold cyan]{aliases}\n\n"
        f"{cmd.detail}\n\n"
        f"[dim]Example:[/dim] {cmd.example}",
        style="blue",
        padding=(1, 2),
    ))


# ---------------------------------------------------------------------------
# Status and info commands
# ---------------------------------------------------------------------------

def show_status():
    """Display KB status."""
    venture_id = get_venture_id()
    stats = get_stats(venture_id)
    console.print(Panel(
        f"[bold]Knowledge Base[/bold]\n"
        f"Total nodes: {stats.get('total', 0)}\n"
        f"Labels: {stats.get('by_label', {})}\n"
        f"Domains: {stats.get('by_domain', {})}\n"
        f"Avg confidence: {stats.get('avg_confidence', 0):.1f}",
        style="blue", title="KB Status",
    ))


def show_where(mode: str):
    """Show current mode."""
    label = MODE_LABELS.get(mode, mode)
    color = MODE_COLORS.get(mode, "white")
    console.print(f"[{color}]Currently in: [bold]{label}[/bold][/{color}]")


def show_history():
    """Show session history."""
    if not session.entries:
        console.print("[dim]No commands in this session yet.[/dim]")
        return

    table = Table(title="Session History", show_lines=False)
    table.add_column("Time", style="dim", width=10)
    table.add_column("Mode", width=14)
    table.add_column("Command", min_width=30)
    table.add_column("Cost", justify="right", width=10)

    for entry in session.entries:
        elapsed = entry.timestamp - session.start_time
        mins, secs = divmod(int(elapsed), 60)
        time_str = f"+{mins:02d}:{secs:02d}"
        cost_str = f"${entry.cost:.4f}" if entry.cost > 0 else ""
        mode_label = MODE_LABELS.get(entry.mode, entry.mode)
        table.add_row(time_str, mode_label, entry.command, cost_str)

    console.print(table)
    console.print(f"\n[bold]Total: ${session.total_cost:.4f} ({session.api_calls} API calls)[/bold]")


def show_cost():
    """Show session cost summary."""
    console.print(f"Session cost: [bold]${session.total_cost:.4f}[/bold] ({session.api_calls} API calls)")


def show_switch_menu(current_mode: str):
    """Show available agents to switch to."""
    console.print("\n[bold]Available agents:[/bold]")
    for mode, label in MODE_LABELS.items():
        color = MODE_COLORS[mode]
        marker = " [dim](current)[/dim]" if mode == current_mode else ""
        console.print(f"  [bold {color}]>{mode}[/bold {color}]  {label}{marker}")
    console.print()


# ---------------------------------------------------------------------------
# Spinner helper
# ---------------------------------------------------------------------------

def run_with_spinner(func, message="Thinking...", *args, **kwargs):
    """Run a function with a spinner indicator."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold magenta]{message}"),
        console=console,
    ) as progress:
        task = progress.add_task(message, total=None)
        result = func(*args, **kwargs)
        progress.update(task, completed=True)
    return result


def display_response(response, title="Response", style="magenta"):
    """Display an agent response in a Rich panel."""
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

    session.add_cost(response.cost_estimate)
    return response.cost_estimate


# ---------------------------------------------------------------------------
# Command parser
# ---------------------------------------------------------------------------

def parse_input(raw: str, mode: str) -> tuple[str, str]:
    """Parse user input into (command, args). Returns ("unknown", raw) for unrecognized commands.

    Returns ("question", raw) for free-text questions that should be sent to the agent.
    """
    text = raw.strip()
    if not text:
        return ("empty", "")

    lower = text.lower()

    # --- Help variants ---
    if lower in ("?", "help"):
        return ("help", "")
    if lower in ("??", "help all"):
        return ("help_all", "")
    if lower.startswith("?") and len(lower) > 1 and lower[1] != "?":
        return ("help_cmd", text[1:].strip())
    if lower.startswith("help ") and lower != "help all":
        return ("help_cmd", text[5:].strip())

    # --- Global commands ---
    if lower in ("quit", "exit", "q"):
        return ("quit", "")
    if lower in ("status", "stats"):
        return ("status", "")
    if lower in ("where", "pwd"):
        return ("where", "")
    if lower == "history":
        return ("history", "")
    if lower == "cost":
        return ("cost", "")
    if lower in ("clear", "cls"):
        return ("clear", "")

    # --- Navigation ---
    if lower in (">", "switch"):
        return ("switch", "")
    if lower in (">brain", ">master"):
        return ("nav", "brain")
    if lower == ">optics":
        return ("nav", "optics")
    if lower == ">research":
        return ("nav", "research")
    if lower == "back":
        return ("back", "")

    # --- Mode-specific commands ---
    if mode == "brain":
        if lower == "review":
            return ("review", "")
        if lower.startswith("assess"):
            return ("assess", text[6:].strip())
        if lower == "gaps":
            return ("gaps", "")
        if lower.startswith("gaps fill "):
            return ("gaps_fill", text[10:].strip())

    if mode == "research":
        if lower == "priorities":
            return ("priorities", "")
        if lower.startswith("search "):
            return ("search", text[7:].strip())
        if lower.startswith("patents "):
            return ("patents", text[8:].strip())
        if lower.startswith("lookup "):
            return ("lookup", text[7:].strip())
        if lower.startswith("gap "):
            return ("gap", text[4:].strip())
        if lower == "gaps":
            return ("priorities", "")
        if lower == "auto":
            return ("auto", "")

    if mode == "optics":
        if lower == "gaps":
            return ("gaps", "")
        if lower == "complex":
            return ("complex", "")

    # --- Check if it looks like an unknown command (starts with known prefix) ---
    # Single-word inputs that aren't recognized commands get sent as questions
    # Multi-word inputs that start with a command keyword are handled above
    # Everything else is a question for the agent
    return ("question", text)


def handle_global_command(cmd: str, args: str, mode: str) -> bool:
    """Handle global commands. Returns True if the command was handled."""
    if cmd == "help":
        show_help_brief(mode)
        return True
    if cmd == "help_all":
        show_help_full(mode)
        return True
    if cmd == "help_cmd":
        show_help_command(args, mode)
        return True
    if cmd == "status":
        show_status()
        return True
    if cmd == "where":
        show_where(mode)
        return True
    if cmd == "history":
        show_history()
        return True
    if cmd == "cost":
        show_cost()
        return True
    if cmd == "clear":
        os.system("cls" if os.name == "nt" else "clear")
        return True
    if cmd == "quit":
        return True  # caller checks for quit
    return False


def get_prompt(mode: str) -> str:
    """Return the formatted prompt string for the given mode."""
    label = MODE_LABELS.get(mode, mode)
    color = MODE_COLORS.get(mode, "white")
    return f"[bold {color}]{label} > [/bold {color}]"
