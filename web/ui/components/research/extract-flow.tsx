"use client";

import { useEffect, useRef, useState } from "react";
import { SourceResult } from "@/lib/api";
import { ConfirmModal } from "@/components/ui/confirm-modal";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Badge, labelToTone } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, Loader2, X } from "lucide-react";
import { cn, titleCase } from "@/lib/utils";

type Stage =
  | "idle"
  | "metadata"
  | "download"
  | "epistemic_filter"
  | "store"
  | "done"
  | "error"
  | "skipped";

type StoredEvent = {
  index: number;
  total: number;
  node_id: string;
  summary: string;
};

type ExtractedSummary = {
  node_count: number;
  summary: string;
  model: string;
  cost_usd: number;
  duration_ms: number;
  nodes_preview: {
    epistemic_label: string;
    summary: string;
    domain: string | null;
    confidence: number;
  }[];
};

const STAGE_LABEL: Record<Stage, string> = {
  idle: "Ready",
  metadata: "Fetching metadata",
  download: "Downloading PDF",
  epistemic_filter: "Running Epistemic Filter",
  store: "Storing nodes",
  done: "Complete",
  error: "Failed",
  skipped: "Skipped",
};

const STAGES: Stage[] = ["metadata", "download", "epistemic_filter", "store"];

export function ExtractFlow({
  candidate,
  onClose,
}: {
  candidate: SourceResult | null;
  onClose: () => void;
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [stage, setStage] = useState<Stage>("idle");
  const [stageMessage, setStageMessage] = useState("");
  const [extracted, setExtracted] = useState<ExtractedSummary | null>(null);
  const [stored, setStored] = useState<StoredEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ stored: number; cost_usd: number; duration_seconds: number } | null>(null);
  const [skipped, setSkipped] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // Open the confirmation modal whenever a new candidate arrives
  useEffect(() => {
    if (candidate) {
      reset();
      setConfirmOpen(true);
    }
  }, [candidate]);

  function reset() {
    setStage("idle");
    setStageMessage("");
    setExtracted(null);
    setStored([]);
    setError(null);
    setDone(null);
    setSkipped(null);
  }

  function cancelConfirm() {
    setConfirmOpen(false);
    onClose();
  }

  async function startExtraction() {
    if (!candidate) return;
    setConfirmOpen(false);
    setStage("metadata");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const r = await fetch("/api/backend/research/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paper_id: candidate.arxiv_id,
          context: "",
          force: false,
        }),
        signal: controller.signal,
      });

      if (!r.body) throw new Error("No stream body");
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done: streamDone } = await reader.read();
        if (streamDone) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const ev = parseFrame(frame);
          if (!ev) continue;
          handle(ev);
        }
      }
    } catch (e) {
      if ((e as any).name !== "AbortError") {
        setError(String(e));
        setStage("error");
      }
    }
  }

  function handle(ev: { event: string; data: any }) {
    if (ev.event === "stage") {
      setStage(ev.data.name as Stage);
      setStageMessage(ev.data.message || "");
    } else if (ev.event === "metadata") {
      // We already have candidate metadata; nothing to do
    } else if (ev.event === "downloaded") {
      // pass
    } else if (ev.event === "extracted") {
      setExtracted(ev.data as ExtractedSummary);
    } else if (ev.event === "stored") {
      setStored((s) => [...s, ev.data as StoredEvent]);
    } else if (ev.event === "skipped") {
      setSkipped(ev.data.message || "Already extracted.");
      setStage("skipped");
    } else if (ev.event === "error") {
      setError(ev.data.message || "Unknown error");
      setStage("error");
    } else if (ev.event === "done") {
      if (ev.data.stop_reason === "completed") {
        setDone({
          stored: ev.data.stored,
          cost_usd: ev.data.cost_usd,
          duration_seconds: ev.data.duration_seconds,
        });
        setStage("done");
      }
    }
  }

  if (!candidate) return null;

  return (
    <>
      <ConfirmModal
        open={confirmOpen}
        title="Extract this paper into the Knowledge Base?"
        description={
          `This will download the PDF, run Sonnet 4.6 to extract 10–30 ` +
          `epistemically labelled knowledge nodes, and insert them into the KB ` +
          `with full provenance. The KB will be modified.`
        }
        stats={[
          { label: "Paper", value: candidate.title.slice(0, 60) + (candidate.title.length > 60 ? "…" : "") },
          { label: "Source", value: `arXiv:${candidate.arxiv_id}`, tone: "info" },
          { label: "Estimated cost", value: "~$0.02–0.08", tone: "warn" },
          { label: "Estimated time", value: "30–90 seconds", tone: "warn" },
        ]}
        confirmLabel="Confirm and extract"
        onConfirm={startExtraction}
        onCancel={cancelConfirm}
      />

      {/* Progress panel — visible after confirmation */}
      {!confirmOpen && (
        <div className="fixed inset-0 z-40 flex items-end md:items-center justify-center p-4 md:p-6 animate-fadeUp">
          <div
            className="absolute inset-0 bg-ink/30 backdrop-blur-sm"
            onClick={() => (stage === "done" || stage === "error" || stage === "skipped") && onClose()}
          />
          <div className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-xl border border-ink-line bg-bg-elevated shadow-soft">
            {/* Header */}
            <div className="px-5 pt-4 pb-3 border-b border-ink-line flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-ink-subtle font-mono">
                  Extraction · arXiv:{candidate.arxiv_id}
                </div>
                <div className="mt-0.5 text-sm font-medium text-ink leading-snug">
                  {candidate.title}
                </div>
              </div>
              {(stage === "done" || stage === "error" || stage === "skipped") && (
                <button
                  onClick={onClose}
                  className="shrink-0 h-7 w-7 rounded-lg hover:bg-bg-subtle grid place-items-center text-ink-muted"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Stage tracker */}
            <div className="px-5 py-3 border-b border-ink-line">
              <div className="flex items-center gap-1.5">
                {STAGES.map((s, i) => {
                  const stageIndex = STAGES.indexOf(stage);
                  const isCurrent = s === stage;
                  const isDone = stage === "done" || (stageIndex > i && stageIndex >= 0);
                  return (
                    <div key={s} className="flex-1 flex items-center gap-1.5">
                      <div
                        className={cn(
                          "h-1.5 flex-1 rounded-full transition-colors",
                          isDone
                            ? "bg-accent"
                            : isCurrent
                              ? "bg-accent/50 animate-pulse"
                              : "bg-ink-line"
                        )}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="mt-2 flex items-center gap-2 text-xs">
                {(stage === "metadata" ||
                  stage === "download" ||
                  stage === "epistemic_filter" ||
                  stage === "store") && (
                  <Loader2 className="h-3 w-3 text-accent animate-spin" />
                )}
                {stage === "done" && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />}
                {stage === "error" && <AlertCircle className="h-3.5 w-3.5 text-rose-600" />}
                {stage === "skipped" && <AlertCircle className="h-3.5 w-3.5 text-amber-600" />}
                <span className="text-ink-muted">
                  {STAGE_LABEL[stage]}
                  {stageMessage && ` — ${stageMessage}`}
                </span>
              </div>
            </div>

            {/* Body — scrolls */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {error && (
                <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3">
                  {error}
                </div>
              )}

              {skipped && (
                <div className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">
                  {skipped}
                </div>
              )}

              {extracted && (
                <section>
                  <div className="text-[10px] uppercase tracking-wider text-ink-subtle mb-1.5">
                    Extracted summary
                  </div>
                  <div className="text-[12px] text-ink-muted leading-relaxed bg-bg-subtle/40 border border-ink-line rounded-lg p-3">
                    {extracted.summary}
                  </div>
                  <div className="mt-1.5 text-[10px] text-ink-subtle font-mono flex flex-wrap gap-x-3">
                    <span>{extracted.model}</span>
                    <span>${extracted.cost_usd.toFixed(4)}</span>
                    <span>{(extracted.duration_ms / 1000).toFixed(1)}s</span>
                    <span>{extracted.node_count} nodes proposed</span>
                  </div>
                </section>
              )}

              {extracted && (
                <section>
                  <div className="text-[10px] uppercase tracking-wider text-ink-subtle mb-1.5">
                    Nodes ({stored.length} / {extracted.nodes_preview.length} stored)
                  </div>
                  <ul className="space-y-1.5">
                    {extracted.nodes_preview.map((n, i) => {
                      const wasStored = stored.some((s) => s.index === i + 1);
                      return (
                        <li
                          key={i}
                          className={cn(
                            "flex items-start gap-2 rounded-lg border px-2.5 py-1.5 transition-colors",
                            wasStored
                              ? "border-emerald-200 bg-emerald-50/40"
                              : "border-ink-line bg-bg-elevated"
                          )}
                        >
                          {wasStored ? (
                            <CheckCircle2 className="h-3 w-3 text-emerald-600 mt-1 shrink-0" />
                          ) : stage === "store" ? (
                            <Loader2 className="h-3 w-3 text-ink-subtle animate-spin mt-1 shrink-0" />
                          ) : (
                            <div className="h-3 w-3 rounded-full border border-ink-line mt-1 shrink-0" />
                          )}
                          <Badge tone={labelToTone(n.epistemic_label)}>
                            {n.epistemic_label.split("_")[0]}
                          </Badge>
                          <div className="flex-1 min-w-0">
                            <div className="text-[12px] text-ink truncate">{n.summary}</div>
                            <div className="text-[10px] text-ink-subtle font-mono">
                              {n.domain ? titleCase(n.domain) : "—"} · conf {Math.round(n.confidence)}
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}

              {done && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50/40 p-3">
                  <div className="flex items-center gap-2 text-sm text-emerald-700 font-medium">
                    <CheckCircle2 className="h-4 w-4" />
                    Stored {done.stored} new knowledge nodes
                  </div>
                  <div className="mt-1 text-[11px] text-emerald-700/80 font-mono">
                    {done.duration_seconds}s · ${done.cost_usd.toFixed(4)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
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
