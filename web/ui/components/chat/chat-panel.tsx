"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Sparkles, Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type ToolCall = {
  id: string;
  name: string;
  input: any;
  output?: any;
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
  "Which lifecycle states are most common?",
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

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

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
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE frames separated by blank lines
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

function ToolCard({ tool }: { tool: ToolCall }) {
  const [open, setOpen] = useState(false);
  const status = tool.output === undefined ? "Running" : "Complete";
  return (
    <div className="rounded-lg border border-ink-line bg-bg-elevated">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left"
      >
        {open ? (
          <ChevronDown className="h-3 w-3 text-ink-subtle" />
        ) : (
          <ChevronRight className="h-3 w-3 text-ink-subtle" />
        )}
        <Wrench className="h-3 w-3 text-accent" />
        <span className="text-[11px] font-mono text-ink">{tool.name}</span>
        <span
          className={cn(
            "ml-auto text-[10px] uppercase tracking-wider",
            tool.output === undefined ? "text-amber-600" : "text-emerald-600"
          )}
        >
          {status}
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
          {tool.output !== undefined && (
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
