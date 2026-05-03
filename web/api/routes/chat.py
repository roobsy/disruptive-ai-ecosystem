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

import asyncio
import json
import os
import sys
import traceback
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

TOOL USE POLICY:
- kb_stats and kb_query are FAST and FREE — use them liberally to ground answers
  in real KB data instead of speculating.
- master_brain_review is EXPENSIVE (~30–90s, ~$0.50). Call it ONLY when the user
  explicitly asks for a strategic review, comprehensive assessment, or "what's
  the state of the venture." Never call it just to answer a narrow question.
- master_brain_assess is EXPENSIVE (~30–60s, ~$0.40). Call it when the user
  proposes a concrete idea/hypothesis/solution path and wants it stress-tested.
- Before calling an expensive tool, briefly tell the user what you're about to
  do and why. After it returns, summarize the key findings — don't paste the
  full text back, the user can expand the tool card to read it.

When you display node lists, use compact markdown tables. When you give numbers,
attribute them to the tool that returned them.

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


async def _run_tool_streaming(tool_id: str, name: str, args: dict):
    """Run a tool in a worker thread while bridging on_progress callbacks
    back to the main event loop via an asyncio.Queue.

    Yields ("progress", text_delta) zero or more times, then exactly one
    ("result", output_dict) at the end.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    SENTINEL = object()

    def on_progress(text: str):
        # Called from the worker thread — schedule the put on the loop thread
        try:
            loop.call_soon_threadsafe(queue.put_nowait, ("progress", text))
        except RuntimeError:
            pass  # loop closed

    async def _runner():
        try:
            result = await asyncio.to_thread(run_tool, name, args, on_progress)
        except Exception as e:
            result = {"error": str(e)}
        await queue.put(("result", result))
        await queue.put(SENTINEL)

    runner = asyncio.create_task(_runner())

    try:
        while True:
            item = await queue.get()
            if item is SENTINEL:
                return
            kind, payload = item
            yield kind, payload
    finally:
        if not runner.done():
            runner.cancel()


@router.post("")
async def chat(req: ChatRequest):
    """Streamed chat with tool use. Returns SSE."""

    async def event_stream():
        try:
            client = _client()
        except Exception as e:
            print(f"[chat] client init failed: {e}", file=sys.stderr)
            yield _sse("error", {"message": f"Anthropic client init failed: {e}"})
            yield _sse("done", {"stop_reason": "error"})
            return

        model = req.model or _model()
        messages = _to_anthropic_messages(req.messages)
        print(f"[chat] starting stream, model={model}, turns_in={len(messages)}", file=sys.stderr)

        # Tool-use loop. Each iteration is one Claude turn; if Claude requests
        # tool calls we run them and continue the loop.
        for turn in range(8):  # hard cap
            try:
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
            except Exception as e:
                tb = traceback.format_exc()
                print(f"[chat] anthropic call failed on turn {turn}:\n{tb}", file=sys.stderr)
                yield _sse(
                    "error",
                    {
                        "message": f"{type(e).__name__}: {e}",
                        "model": model,
                    },
                )
                yield _sse("done", {"stop_reason": "error"})
                return

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

                # Run the tool off the event loop, but bridge progress events
                # back into the SSE stream so the UI can render live deltas
                # while Opus generates.
                async for kind, payload in _run_tool_streaming(
                    tu["id"], tu["name"], tu["input"] or {}
                ):
                    if kind == "progress":
                        yield _sse(
                            "tool_progress",
                            {"id": tu["id"], "delta": payload},
                        )
                    else:
                        output = payload
                        yield _sse(
                            "tool_result",
                            {"id": tu["id"], "name": tu["name"], "output": output},
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tu["id"],
                                "content": json.dumps(output)[:30000],
                            }
                        )

            messages.append({"role": "user", "content": tool_results})

        yield _sse("done", {"stop_reason": "max_turns"})

    return EventSourceResponse(event_stream())
