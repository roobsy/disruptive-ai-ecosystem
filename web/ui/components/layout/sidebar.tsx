"use client";

import {
  LayoutDashboard,
  Database,
  Telescope,
  Brain,
  MessagesSquare,
  Plug,
  Settings,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { icon: LayoutDashboard, label: "Dashboard", active: true },
  { icon: Database, label: "Knowledge Base" },
  { icon: Telescope, label: "Research" },
  { icon: Brain, label: "Master Brain" },
  { icon: MessagesSquare, label: "Domain Agents" },
  { icon: Plug, label: "Sources" },
  { icon: Settings, label: "Settings" },
];

export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-ink-line bg-bg-elevated/60 flex flex-col">
      <div className="px-5 pt-5 pb-4">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-ink text-bg-elevated grid place-items-center">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">Ecosystem</div>
            <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
              Disruptive Intelligence
            </div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-2 pt-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              disabled={!item.active}
              className={cn(
                "w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                item.active
                  ? "bg-bg-subtle text-ink font-medium"
                  : "text-ink-subtle hover:text-ink-muted disabled:hover:text-ink-subtle disabled:cursor-not-allowed"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="flex-1 text-left">{item.label}</span>
              {!item.active && (
                <span className="text-[9px] uppercase text-ink-subtle">
                  soon
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-3 border-t border-ink-line">
        <div className="rounded-lg bg-accent-soft border border-accent-ring/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-accent font-semibold">
            Vertical slice
          </div>
          <div className="text-xs text-ink-muted mt-1 leading-relaxed">
            Dashboard + Chat are live. More surfaces ship next.
          </div>
        </div>
      </div>
    </aside>
  );
}
