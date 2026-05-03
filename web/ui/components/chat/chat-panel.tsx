"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  Send,
  Sparkles,
  Wrench,
  ChevronDown,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { onChatMessage } from "@/lib/chat-bus";

type ToolCall = {
  id: string;
  name: string;
  input: any;
  output?: any;
  progress?: string; // accumulated streaming text while running
};

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  tools?: ToolCall[];
  pending?: boolean;
};

const SUGGESTIONS = [
  "What's the current state of the KB?",
  "Show me the top 5 ophthalmology nodes.",
  "Run a Master Brain strategic review.",
  "Assess the idea: hybrid PSF deconvolution + tunable lens layer.",
];

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      text:
        "Hi — I'm wired into your Knowledge Base. Ask me about node counts, domain coverage, or specific epistemic labels and I'll query the KB live.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const sendRef = useRef<(text: string) => void>(() => {});

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  // Subscribe to the global chat bus once. Other components (dashboard
  // buttons, suggestion chips) emit messages here.
  useEffect(() => {
    return onChatMessage((text) => sendRef.current(text));
  }, []);

  // Keep the bus-callable send pointed at the latest closure (state changes
  // each render, so closures capturing `messages` / `sending` go stale).
  sendRef.current = (text: string) => {
    void send(text);
  };

  async function send(text: string) {
    if (!text.trim() || sending) return;
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text,
    };
    const assistantId = crypto.randomUUID();
    const placeholder: Message = {
      id: assistantId,
      role: "assistant",
      text: "",
      tools: [],
      pending: true,
    };
    setMessages((m) => [...m, userMsg, placeholder]);
    setInput("");
    setSending(true);

    try {
      const history = [
        ...messages
          .filter((m) => m.id !== "welcome")
          .map((m) => ({ role: m.role, content: m.text })),
        { role: "user", content: text },
      ];

      const resp = await fetch("/api/backend/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });

      if (!resp.body) throw new Error("No stream body");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        // Normalize CRLF → LF so the frame separator is always \n\n.
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

        // Parse SSE frames separated by a blank line
        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const ev = parseFrame(frame);
          if (!ev) continue;
          handleEvent(assistantId, ev);
        }
      }
    } catch (e) {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                text: `Sorry — chat failed: ${String(e)}`,
                pending: false,
              }
            : msg
        )
      );
    } finally {
      setSending(false);
      setMessages((m) =>
        m.map((msg) => (msg.id === assistantId ? { ...msg, pending: false } : msg))
      );
    }
  }

  function handleEvent(
    assistantId: string,
    ev: { event: string; data: any }
  ) {
    if (ev.event === "text") {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? { ...msg, text: msg.text + (ev.data.delta || "") }
            : msg
        )
      );
    } else if (ev.event === "tool_use") {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                tools: [
                  ...(msg.tools || []),
                  { id: ev.data.id, name: ev.data.name, input: ev.data.input },
                ],
              }
            : msg
        )
      );
    } else if (ev.event === "tool_progress") {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                tools: (msg.tools || []).map((t) =>
                  t.id === ev.data.id
                    ? { ...t, progress: (t.progress || "") + (ev.data.delta || "") }
                    : t
                ),
              }
            : msg
        )
      );
    } else if (ev.event === "tool_result") {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                tools: (msg.tools || []).map((t) =>
                  t.id === ev.data.id ? { ...t, output: ev.data.output } : t
                ),
              }
            : msg
        )
      );
    } else if (ev.event === "error") {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                text:
                  msg.text +
                  `\n\nError: ${ev.data?.message || "unknown"}${
                    ev.data?.model ? ` (model: ${ev.data.model})` : ""
                  }`,
                pending: false,
              }
            : msg
        )
      );
    } else if (ev.event === "done") {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId ? { ...msg, pending: false } : msg
        )
      );
    }
  }

  return (
    <div className="h-full flex flex-col bg-bg-elevated/60 border-l border-ink-line">
      {/* Header */}
      <div className="h-14 shrink-0 px-4 border-b border-ink-line flex items-center gap-2">
        <div className="h-7 w-7 rounded-lg bg-accent-soft text-accent grid place-items-center">
          <Sparkles className="h-3.5 w-3.5" />
        </div>
        <div>
          <div className="text-sm font-medium leading-tight">Chat</div>
          <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
            Sonnet 4.6 · KB tools
          </div>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((m) => (
          <ChatBubble key={m.id} message={m} />
        ))}
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="text-[11px] rounded-full border border-ink-line bg-bg-elevated px-2.5 py-1 text-ink-muted hover:text-ink hover:border-accent-ring/50 hover:bg-accent-soft transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="p-3 border-t border-ink-line"
      >
        <div className="flex items-end gap-2 rounded-xl border border-ink-line bg-bg-elevated focus-within:border-accent-ring focus-within:shadow-glow transition-all px-3 py-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={1}
            placeholder="Ask the ecosystem…"
            className="flex-1 resize-none bg-transparent text-sm placeholder:text-ink-subtle focus:outline-none max-h-32"
          />
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={sending || !input.trim()}
          >
            <Send className="h-3 w-3" />
          </Button>
        </div>
      </form>
    </div>
  );
}

function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("animate-fadeUp", isUser ? "flex justify-end" : "")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-ink text-bg-elevated"
            : "bg-bg-subtle border border-ink-line text-ink"
        )}
      >
        {message.tools && message.tools.length > 0 && (
          <div className="mb-2 space-y-1.5">
            {message.tools.map((t) => (
              <ToolCard key={t.id} tool={t} />
            ))}
          </div>
        )}
        <div className="prose-chat whitespace-pre-wrap">
          {message.text}
          {message.pending && !message.text && (
            <span className="inline-block h-3 w-3 rounded-full bg-accent animate-pulse" />
          )}
          {message.pending && message.text && (
            <span className="inline-block ml-1 h-3 w-1.5 align-middle bg-ink-muted/60 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
}

const EXPENSIVE_TOOLS = new Set(["master_brain_review", "master_brain_assess"]);

function ToolCard({ tool }: { tool: ToolCall }) {
  const isExpensive = EXPENSIVE_TOOLS.has(tool.name);
  const running = tool.output === undefined;
  const streaming = running && (tool.progress?.length ?? 0) > 0;
  // Auto-expand expensive tools while running so the user sees activity.
  const [open, setOpen] = useState(isExpensive && running);
  const out = tool.output as any;
  const failed = out && (out.success === false || out.error);
  const hasProse = out && typeof out.content === "string" && out.content.length > 0;

  const status = running
    ? streaming
      ? "Streaming"
      : isExpensive
        ? "Thinking"
        : "Running"
    : failed
      ? "Failed"
      : "Complete";
  const statusClass = running
    ? streaming
      ? "text-accent"
      : "text-amber-600"
    : failed
      ? "text-rose-600"
      : "text-emerald-600";

  // Auto-scroll the streaming pane to bottom as new tokens arrive
  const streamRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [tool.progress]);

  return (
    <div
      className={cn(
        "rounded-lg border bg-bg-elevated transition-colors",
        failed
          ? "border-rose-200"
          : isExpensive
            ? "border-accent-ring/40"
            : "border-ink-line"
      )}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left"
      >
        {open ? (
          <ChevronDown className="h-3 w-3 text-ink-subtle" />
        ) : (
          <ChevronRight className="h-3 w-3 text-ink-subtle" />
        )}
        {isExpensive ? (
          <Sparkles className={cn("h-3 w-3 text-accent", running && "animate-pulse")} />
        ) : failed ? (
          <AlertCircle className="h-3 w-3 text-rose-600" />
        ) : (
          <Wrench className="h-3 w-3 text-accent" />
        )}
        <span className="text-[11px] font-mono text-ink">{tool.name}</span>
        {streaming && (
          <span className="text-[10px] font-mono text-ink-subtle">
            {(tool.progress?.length ?? 0).toLocaleString()} ch
          </span>
        )}
        <span className={cn("ml-auto text-[10px] uppercase tracking-wider", statusClass)}>
          {status}
          {running && <span className="ml-1 inline-block animate-pulse">·</span>}
        </span>
      </button>
      {open && (
        <div className="px-2.5 pb-2 space-y-1.5">
          {tool.input && Object.keys(tool.input).length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
                Input
              </div>
              <pre className="mt-0.5 text-[11px] bg-bg-subtle rounded p-2 overflow-x-auto">
                {JSON.stringify(tool.input, null, 2)}
              </pre>
            </div>
          )}

          {/* Live streaming pane while running */}
          {running && streaming && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-accent">
                Streaming · {(tool.progress?.length ?? 0).toLocaleString()} chars
              </div>
              <div
                ref={streamRef}
                className="mt-0.5 text-[12px] leading-relaxed bg-accent-soft/40 border border-accent-ring/30 rounded p-2.5 max-h-72 overflow-y-auto whitespace-pre-wrap text-ink"
              >
                {tool.progress}
                <span className="inline-block ml-0.5 h-3 w-1.5 align-middle bg-accent/60 animate-pulse" />
              </div>
            </div>
          )}

          {/* Pre-stream waiting state */}
          {running && !streaming && (
            <div className="text-[11px] text-ink-muted italic px-0.5">
              {isExpensive
                ? "Calling Opus across the full Knowledge Base — first tokens usually arrive within 5–10 seconds."
                : "Running…"}
            </div>
          )}

          {!running && failed && (
            <div className="text-[11px] text-rose-700 bg-rose-50 border border-rose-200 rounded p-2">
              {out?.error || "Tool returned an error."}
            </div>
          )}

          {!running && !failed && hasProse && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
                Result
              </div>
              <div className="mt-0.5 text-[12px] leading-relaxed bg-bg-subtle rounded p-2.5 max-h-72 overflow-y-auto whitespace-pre-wrap text-ink">
                {out.content}
              </div>
              <ToolMeta out={out} />
            </div>
          )}

          {!running && !failed && !hasProse && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
                Output
              </div>
              <pre className="mt-0.5 text-[11px] bg-bg-subtle rounded p-2 overflow-x-auto max-h-48">
                {JSON.stringify(tool.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ToolMeta({ out }: { out: any }) {
  const bits: string[] = [];
  if (out.model) bits.push(out.model);
  if (out.duration_seconds != null) bits.push(`${out.duration_seconds}s`);
  if (out.cost_usd != null) bits.push(`$${out.cost_usd.toFixed(3)}`);
  if (out.input_tokens != null && out.output_tokens != null) {
    bits.push(`${out.input_tokens}→${out.output_tokens} tok`);
  }
  if (!bits.length) return null;
  return (
    <div className="mt-1.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-ink-subtle font-mono">
      {bits.map((b, i) => (
        <span key={i}>{b}</span>
      ))}
    </div>
  );
}

function parseFrame(frame: string): { event: string; data: any } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return { event, data: dataLines.join("\n") };
  }
}
