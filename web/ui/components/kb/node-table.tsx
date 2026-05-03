"use client";

import { KBNode } from "@/lib/api";
import { Badge, labelToTone } from "@/components/ui/badge";
import { titleCase } from "@/lib/utils";

export function NodeTable({
  nodes,
  loading,
  onSelect,
}: {
  nodes: KBNode[];
  loading: boolean;
  onSelect: (n: KBNode) => void;
}) {
  if (loading) {
    return (
      <div className="rounded-xl border border-ink-line bg-bg-elevated p-8 text-center text-sm text-ink-subtle">
        Loading nodes…
      </div>
    );
  }

  if (!nodes.length) {
    return (
      <div className="rounded-xl border border-ink-line bg-bg-elevated p-8 text-center text-sm text-ink-subtle">
        No nodes match the current filters.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-ink-line bg-bg-elevated shadow-soft overflow-hidden">
      <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 px-4 py-2 border-b border-ink-line bg-bg-subtle/50 text-[10px] uppercase tracking-wider text-ink-subtle font-medium">
        <div>Summary</div>
        <div>Label</div>
        <div>Domain</div>
        <div>Lifecycle</div>
        <div className="text-right">Conf.</div>
      </div>
      <ul className="divide-y divide-ink-line">
        {nodes.map((n) => (
          <li key={n.id}>
            <button
              onClick={() => onSelect(n)}
              className="w-full text-left grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 items-center px-4 py-2.5 hover:bg-accent-soft/40 transition-colors"
            >
              <div className="text-sm text-ink truncate">
                {n.summary || (n.content || "").slice(0, 100)}
              </div>
              <Badge tone={labelToTone(n.epistemic_label)}>
                {n.epistemic_label.split("_")[0]}
              </Badge>
              <div className="text-[11px] text-ink-muted truncate max-w-[160px]">
                {n.domain ? titleCase(n.domain) : "—"}
              </div>
              <div className="text-[11px] text-ink-subtle truncate max-w-[120px]">
                {titleCase(n.lifecycle_state || "")}
              </div>
              <div className="text-sm tabular-nums text-ink-muted text-right w-12">
                {Math.round(n.confidence)}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
