"""
Chat endpoint with Claude tool use.

Streams Server-Sent Events back to the browser:
  event: text         → token / text delta
  event: tool_use     → {name, input}
  event: tool_result  → {name, output}
  event: done         → final usage / stop reason

Multi-turn tool loop: when Claude requests a tool, we run it, append the
result to the message history, and ask Claude again — until it stops with
end_turn.
"""

import json
import os
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from anthropic import Anthropic

from web.api.tools import TOOL_SCHEMAS, run_tool

router = APIRouter()

SYSTEM_PROMPT = """You are the chat copilot inside the Disruptive AI Ecosystem web app.

Your job is to help the user explore, observe, and operate the system. The active
venture is "Vision Correction Display" — its Prime Directive is to identify and
validate a commercially viable, patent-clear method for correcting refractive
vision errors through display technology.

You have tools to query the Knowledge Base (KB). Prefer calling tools to ground
your answers in real data rather than speculating. When you display node lists,
use compact markdown tables. When you give numbers, attribute them to the tool
that returned them.

Be concise. The user can see a Dashboard alongside this chat — don't repeat what
the dashboard already shows; add interpretation.
"""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: Optional[str] = None


def _client() -> Anthropic:
    return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _model() -> str:
    return os.getenv("MODEL_STANDARD", "claude-sonnet-4-6")


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data)}


def _to_anthropic_messages(history: list[ChatMessage]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in history]


@router.post("")
async def chat(req: ChatRequest):
    """Streamed chat with tool use. Returns SSE."""

    async def event_stream():
        client = _client()
        model = req.model or _model()
        messages = _to_anthropic_messages(req.messages)

        # Tool-use loop. Each iteration is one Claude turn; if Claude requests
        # tool calls we run them and continue the loop.
        for _ in range(8):  # hard cap
            with client.messages.stream(
                model=model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            ) as stream:
                for chunk in stream.text_stream:
                    if chunk:
                        yield _sse("text", {"delta": chunk})

                final = stream.get_final_message()

            assistant_blocks: list[dict] = []
            tool_uses: list[dict] = []

            for block in final.content:
                if block.type == "text":
                    assistant_blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                    tool_uses.append(
                        {"id": block.id, "name": block.name, "input": block.input}
                    )

            # Append assistant turn to history
            messages.append({"role": "assistant", "content": assistant_blocks})

            if final.stop_reason == "end_turn" or not tool_uses:
                yield _sse(
                    "done",
                    {
                        "stop_reason": final.stop_reason,
                        "input_tokens": final.usage.input_tokens,
                        "output_tokens": final.usage.output_tokens,
                    },
                )
                return

            # Execute each requested tool and feed back as a single user turn
            tool_results: list[dict] = []
            for tu in tool_uses:
                yield _sse(
                    "tool_use",
                    {"id": tu["id"], "name": tu["name"], "input": tu["input"]},
                )
                output = run_tool(tu["name"], tu["input"] or {})
                yield _sse(
                    "tool_result",
                    {"id": tu["id"], "name": tu["name"], "output": output},
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": json.dumps(output)[:6000],
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        yield _sse("done", {"stop_reason": "max_turns"})

    return EventSourceResponse(event_stream())
