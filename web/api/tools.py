"""
Tool definitions for the chat agent.

Each tool exposes a backend capability to Claude. Adding a tool here
makes it instantly invocable from the chat panel.
"""

from typing import Callable
from core.kb import get_stats, get_nodes, get_venture_id


def _venture_id() -> str:
    return get_venture_id()


def tool_kb_stats(_args: dict) -> dict:
    return get_stats(_venture_id())


def tool_kb_query(args: dict) -> dict:
    nodes = get_nodes(
        _venture_id(),
        domain=args.get("domain"),
        epistemic_label=args.get("epistemic_label"),
        lifecycle_state=args.get("lifecycle_state"),
        min_confidence=float(args.get("min_confidence", 0)),
        limit=int(args.get("limit", 10)),
    )
    return {
        "count": len(nodes),
        "nodes": [
            {
                "id": n.get("id"),
                "summary": n.get("summary"),
                "epistemic_label": n.get("epistemic_label"),
                "domain": n.get("domain"),
                "confidence": n.get("confidence"),
                "lifecycle_state": n.get("lifecycle_state"),
            }
            for n in nodes
        ],
    }


# ── Schemas exposed to Claude ─────────────────────────────
TOOL_SCHEMAS = [
    {
        "name": "kb_stats",
        "description": (
            "Return summary statistics for the Knowledge Base: total node count, "
            "breakdown by epistemic label, lifecycle state, domain, and average confidence. "
            "Use this when the user asks about the overall state of the KB."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "kb_query",
        "description": (
            "Query knowledge nodes with optional filters. Returns up to `limit` nodes "
            "ordered by confidence (descending). Use when the user wants to inspect "
            "specific knowledge — e.g. 'show me high-confidence ophthalmology facts'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain filter, e.g. 'ophthalmology', 'optics', 'display_technology'.",
                },
                "epistemic_label": {
                    "type": "string",
                    "enum": ["axiomatic_fact", "experimental_result", "cognitive_framework"],
                },
                "lifecycle_state": {
                    "type": "string",
                    "enum": [
                        "discovery",
                        "under_evaluation",
                        "validated",
                        "contested",
                        "superseded",
                        "ruled_out",
                    ],
                },
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence (0–100).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max nodes to return (default 10, max 50).",
                },
            },
            "required": [],
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "kb_stats": tool_kb_stats,
    "kb_query": tool_kb_query,
}


def run_tool(name: str, args: dict) -> dict:
    """Execute a tool by name. Returns a JSON-serializable result."""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(args or {})
    except Exception as e:
        return {"error": str(e)}
