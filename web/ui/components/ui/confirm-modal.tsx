"use client";

import { useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ConfirmStat = {
  label: string;
  value: string;
  tone?: "neutral" | "warn" | "info";
};

export function ConfirmModal({
  open,
  title,
  description,
  stats,
  confirmLabel = "Confirm and run",
  cancelLabel = "Cancel",
  destructive = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  stats?: ConfirmStat[];
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onConfirm();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel, onConfirm]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 animate-fadeUp">
      <div
        className="absolute inset-0 bg-ink/30 backdrop-blur-sm"
        onClick={onCancel}
      />
      <div className="relative w-full max-w-md rounded-xl border border-ink-line bg-bg-elevated shadow-soft">
        <div className="px-5 pt-4 pb-3 border-b border-ink-line flex items-start gap-3">
          <div
            className={cn(
              "h-8 w-8 rounded-lg grid place-items-center shrink-0",
              destructive
                ? "bg-rose-50 text-rose-600 border border-rose-200"
                : "bg-accent-soft text-accent border border-accent-ring/40"
            )}
          >
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-ink leading-tight">
              {title}
            </div>
            <div className="mt-1 text-[12px] text-ink-muted leading-relaxed">
              {description}
            </div>
          </div>
          <button
            onClick={onCancel}
            className="shrink-0 h-7 w-7 rounded-lg hover:bg-bg-subtle grid place-items-center text-ink-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {stats && stats.length > 0 && (
          <div className="px-5 py-3 grid grid-cols-2 gap-3">
            {stats.map((s) => (
              <div key={s.label}>
                <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
                  {s.label}
                </div>
                <div
                  className={cn(
                    "mt-0.5 text-sm font-medium",
                    s.tone === "warn" && "text-amber-700",
                    s.tone === "info" && "text-accent",
                    !s.tone && "text-ink"
                  )}
                >
                  {s.value}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="px-5 pb-4 pt-2 flex items-center justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant="primary"
            onClick={onConfirm}
            className={
              destructive ? "bg-rose-600 hover:bg-rose-700" : undefined
            }
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
