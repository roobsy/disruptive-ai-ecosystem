"use client";

import { useEffect, useState } from "react";
import { X, ExternalLink, FileText, Calendar, User } from "lucide-react";
import { api, KBNode, Provenance } from "@/lib/api";
import { Badge, labelToTone } from "@/components/ui/badge";
import { titleCase } from "@/lib/utils";

export function NodeDetail({
  nodeId,
  onClose,
}: {
  nodeId: string | null;
  onClose: () => void;
}) {
  const [node, setNode] = useState<KBNode | null>(null);
  const [provenance, setProvenance] = useState<Provenance[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!nodeId) return;
    setLoading(true);
    setError(null);
    setNode(null);
    setProvenance([]);
    api
      .node(nodeId)
      .then((r) => {
        setNode(r.node);
        setProvenance(r.provenance);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [nodeId]);

  // Esc to close
  useEffect(() => {
    if (!nodeId) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [nodeId, onClose]);

  if (!nodeId) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6 animate-fadeUp"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-xl border border-ink-line bg-bg-elevated shadow-soft"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 pt-4 pb-3 border-b border-ink-line">
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-ink-subtle font-mono">
              Node · {nodeId.slice(0, 8)}
            </div>
            <div className="mt-1 text-sm font-medium text-ink leading-snug">
              {node?.summary || (loading ? "Loading…" : "")}
            </div>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 h-7 w-7 rounded-lg hover:bg-bg-subtle grid place-items-center text-ink-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {error && (
            <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded p-3">
              {error}
            </div>
          )}

          {node && (
            <>
              {/* Meta strip */}
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={labelToTone(node.epistemic_label)}>
                  {titleCase(node.epistemic_label)}
                </Badge>
                <Badge tone="neutral">
                  {titleCase(node.lifecycle_state || "")}
                </Badge>
                {node.domain && (
                  <Badge tone="neutral">{titleCase(node.domain)}</Badge>
                )}
                <div className="ml-auto text-xs text-ink-muted tabular-nums">
                  Confidence{" "}
                  <span className="text-ink font-semibold">
                    {Math.round(node.confidence)}
                  </span>
                  /100
                </div>
              </div>

              {/* Content */}
              <section>
                <div className="text-[10px] uppercase tracking-wider text-ink-subtle mb-1.5">
                  Content
                </div>
                <div className="text-sm leading-relaxed text-ink whitespace-pre-wrap bg-bg-subtle/40 border border-ink-line rounded-lg p-3">
                  {node.content || node.summary}
                </div>
              </section>

              {/* Tags */}
              {node.tags && node.tags.length > 0 && (
                <section>
                  <div className="text-[10px] uppercase tracking-wider text-ink-subtle mb-1.5">
                    Tags
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {node.tags.map((t) => (
                      <span
                        key={t}
                        className="text-[11px] rounded-md bg-bg-subtle border border-ink-line px-1.5 py-0.5 text-ink-muted"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Provenance */}
              <section>
                <div className="text-[10px] uppercase tracking-wider text-ink-subtle mb-1.5">
                  Provenance ({provenance.length})
                </div>
                {provenance.length === 0 ? (
                  <div className="text-xs text-ink-subtle italic">
                    No source records linked.
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {provenance.map((p) => (
                      <li
                        key={p.id}
                        className="rounded-lg border border-ink-line bg-bg-elevated p-3"
                      >
                        <div className="flex items-start gap-2">
                          <FileText className="h-3.5 w-3.5 text-ink-subtle mt-0.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm text-ink font-medium leading-snug">
                              {p.source_title || p.source_url || p.source_type}
                            </div>
                            {p.source_authors && p.source_authors.length > 0 && (
                              <div className="mt-0.5 text-[11px] text-ink-muted flex items-center gap-1">
                                <User className="h-3 w-3" />
                                {p.source_authors.slice(0, 4).join(", ")}
                                {p.source_authors.length > 4 &&
                                  ` +${p.source_authors.length - 4}`}
                              </div>
                            )}
                            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-ink-subtle font-mono">
                              {p.source_year && (
                                <span className="inline-flex items-center gap-1">
                                  <Calendar className="h-2.5 w-2.5" />
                                  {p.source_year}
                                </span>
                              )}
                              <span>{p.source_type}</span>
                              {p.credibility_tier && (
                                <span>{p.credibility_tier}</span>
                              )}
                              {p.source_doi && <span>doi:{p.source_doi}</span>}
                            </div>
                            {p.source_url && (
                              <a
                                href={p.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1 inline-flex items-center gap-1 text-[11px] text-accent hover:underline"
                              >
                                Open source
                                <ExternalLink className="h-2.5 w-2.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* Footer meta */}
              <div className="pt-2 border-t border-ink-line text-[10px] text-ink-subtle font-mono flex flex-wrap gap-x-3 gap-y-0.5">
                {node.created_by && <span>by {node.created_by}</span>}
                {node.created_at && (
                  <span>{new Date(node.created_at).toLocaleString()}</span>
                )}
                {node.decay_rate != null && (
                  <span>decay: {node.decay_rate}d</span>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
