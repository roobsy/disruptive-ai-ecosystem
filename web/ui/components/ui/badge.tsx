import { cn } from "@/lib/utils";
import { ReactNode } from "react";

type Tone = "neutral" | "axiomatic" | "experimental" | "framework" | "accent";

const toneClass: Record<Tone, string> = {
  neutral: "bg-bg-subtle text-ink-muted border-ink-line",
  axiomatic: "bg-emerald-50 text-emerald-700 border-emerald-200",
  experimental: "bg-accent-soft text-accent border-accent-ring/50",
  framework: "bg-amber-50 text-amber-700 border-amber-200",
  accent: "bg-accent-soft text-accent border-accent-ring/50",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        toneClass[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function labelToTone(label: string): Tone {
  if (label === "axiomatic_fact") return "axiomatic";
  if (label === "experimental_result") return "experimental";
  if (label === "cognitive_framework") return "framework";
  return "neutral";
}
