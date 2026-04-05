"""
Model Router — Standardized Agent Interface
============================================
All agent interactions flow through this interface.
It decouples agents from model implementation, enabling
future multi-model expansion via routing changes only.
"""

import os
import time
import json
from dataclasses import dataclass, field
from typing import Optional
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ── Client singleton ──────────────────────────────────────
_client: Optional[Anthropic] = None

def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


# ── Data contracts ────────────────────────────────────────
@dataclass
class AgentRequest:
    """Standardized input to any agent interaction."""
    role: str                      # "extractor", "dreamer", "judge", "domain:optics"
    complexity: str = "standard"   # "standard" (Sonnet) or "complex" (Opus)
    system_prompt: str = ""
    context: dict = field(default_factory=dict)
    input_text: str = ""
    input_documents: list = field(default_factory=list)  # For PDF/image inputs
    output_format: str = "json"    # "json" or "text"
    max_tokens: int = 4096
    temperature: float = 0.3


@dataclass
class AgentResponse:
    """Standardized output from any agent interaction."""
    content: str                   # Raw response text
    parsed: Optional[dict] = None  # Parsed JSON if output_format was "json"
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_estimate: float = 0.0     # Estimated cost in USD
    duration_ms: int = 0
    success: bool = True
    error: Optional[str] = None


# ── Cost estimation ───────────────────────────────────────
# Approximate costs per million tokens (as of April 2026)
COST_TABLE = {
    "claude-sonnet-4-6":  {"input": 3.0,  "output": 15.0},
    "claude-opus-4-6":    {"input": 15.0, "output": 75.0},
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = COST_TABLE.get(model, {"input": 10.0, "output": 50.0})
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000


# ── Model selection ───────────────────────────────────────
def select_model(complexity: str) -> str:
    """Route complexity tier to the appropriate model.

    This is the single point of change for multi-model expansion.
    In Phase 3+, this function can consider context size, role,
    and other factors to route to different providers.
    """
    if complexity == "complex":
        return os.getenv("MODEL_COMPLEX", "claude-opus-4-6")
    return os.getenv("MODEL_STANDARD", "claude-sonnet-4-6")


# ── Core execution ────────────────────────────────────────
def execute(request: AgentRequest) -> AgentResponse:
    """Execute an agent request through the model router.

    This is the ONLY function that talks to the LLM API.
    All agents call this — never the API directly.
    """
    client = get_client()
    model = select_model(request.complexity)

    # Build the messages
    user_content = []

    # Add any document inputs (PDFs sent as base64)
    for doc in request.input_documents:
        user_content.append(doc)

    # Add the text input
    if request.input_text:
        user_content.append({"type": "text", "text": request.input_text})

    # If only text, simplify
    if len(user_content) == 1 and user_content[0].get("type") == "text":
        messages = [{"role": "user", "content": request.input_text}]
    else:
        messages = [{"role": "user", "content": user_content}]

    # Execute
    start = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=request.system_prompt,
            messages=messages,
        )

        duration_ms = int((time.time() - start) * 1000)
        content = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Try to parse JSON if requested
        parsed = None
        if request.output_format == "json":
            try:
                # Handle markdown code fences
                cleaned = content.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                    cleaned = cleaned.rsplit("```", 1)[0]
                    cleaned = cleaned.strip()
                parsed = json.loads(cleaned)
            except (json.JSONDecodeError, IndexError):
                parsed = None

        return AgentResponse(
            content=content,
            parsed=parsed,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_estimate=estimate_cost(model, input_tokens, output_tokens),
            duration_ms=duration_ms,
            success=True,
        )

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return AgentResponse(
            content="",
            model=model,
            duration_ms=duration_ms,
            success=False,
            error=str(e),
        )
