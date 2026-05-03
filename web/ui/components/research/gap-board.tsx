"use client";

import { Gap } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { ChevronRight, CheckCircle2, AlertTriangle, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

const SEVERITY_TONE: Record<Gap["severity"], "framework" | "experimental" | "neutral"> = {
  showstopper: "framework",
  critical: "experimental",
  strategic: "neutral",
};

const STATUS_LABEL: Record<Gap["status"], string> = {
  filled: "Filled",
  partially_filled: "Partial",
  open: "Open",
};

export function GapBoard({
  gaps,
  selectedId,
  onSelect,
}: {
  gaps: Gap[];
  selectedId: string | null;
  onSelect: (g: Gap) => void;
}) {
  return (
    <div className="rounded-xl border border-ink-line bg-bg-elevated shadow-soft overflow-hidden">
      <div className="px-4 py-2.5 border-b border-ink-line bg-bg-subtle/50">
        <div className="text-[11px] uppercase tracking-wider text-ink-subtle font-medium">
          Research gaps · click a gap to seed a search
        </div>
      </div>
      <ul className="divide-y divide-ink-line">
        {gaps.map((g) => {
          const StatusIcon =
            g.status === "filled"
              ? CheckCircle2
              : g.status === "partially_filled"
                ? AlertTriangle
                : Circle;
          const statusColor =
            g.status === "filled"
              ? "text-emerald-600"
              : g.status === "partially_filled"
                ? "text-amber-600"
                : "text-ink-subtle";
          const isActive = selectedId === g.id;
          return (
            <li key={g.id}>
              <button
                onClick={() => onSelect(g)}
                className={cn(
                  "w-full text-left flex items-start gap-3 px-4 py-3 transition-colors",
                  isActive ? "bg-accent-soft/40" : "hover:bg-bg-subtle/50"
                )}
              >
                <StatusIcon
                  className={cn("h-3.5 w-3.5 mt-0.5 shrink-0", statusColor)}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-ink-subtle">
                      {g.id}
                    </span>
                    <Badge tone={SEVERITY_TONE[g.severity]}>{g.severity}</Badge>
                    <span className={cn("text-[10px] uppercase tracking-wider", statusColor)}>
                      {STATUS_LABEL[g.status]}
                    </span>
                  </div>
                  <div className="mt-0.5 text-sm font-medium text-ink leading-snug">
                    {g.title}
                  </div>
                  <div className="mt-0.5 text-[11px] text-ink-muted line-clamp-2">
                    {g.description}
                  </div>
                </div>
                <ChevronRight className="h-3.5 w-3.5 text-ink-subtle mt-1 shrink-0" />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
