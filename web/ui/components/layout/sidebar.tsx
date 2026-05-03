"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
  { icon: LayoutDashboard, label: "Dashboard", href: "/", active: true },
  { icon: Database, label: "Knowledge Base", href: "/kb", active: true },
  { icon: Telescope, label: "Research", href: "/research", active: true },
  { icon: Brain, label: "Master Brain", href: "/master-brain", active: false },
  { icon: MessagesSquare, label: "Domain Agents", href: "/agents", active: false },
  { icon: Plug, label: "Sources", href: "/sources", active: false },
  { icon: Settings, label: "Settings", href: "/settings", active: false },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 border-r border-ink-line bg-bg-elevated/60 flex flex-col">
      <div className="px-5 pt-5 pb-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-ink text-bg-elevated grid place-items-center">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">Ecosystem</div>
            <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
              Disruptive Intelligence
            </div>
          </div>
        </Link>
      </div>

      <nav className="flex-1 px-2 pt-2 space-y-0.5">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname?.startsWith(item.href));

          if (!item.active) {
            return (
              <div
                key={item.label}
                className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-ink-subtle cursor-not-allowed select-none"
              >
                <Icon className="h-4 w-4" />
                <span className="flex-1 text-left">{item.label}</span>
                <span className="text-[9px] uppercase text-ink-subtle">
                  soon
                </span>
              </div>
            );
          }

          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-bg-subtle text-ink font-medium"
                  : "text-ink-muted hover:text-ink hover:bg-bg-subtle/60"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="flex-1 text-left">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-ink-line">
        <div className="rounded-lg bg-accent-soft border border-accent-ring/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-accent font-semibold">
            Vertical slice
          </div>
          <div className="text-xs text-ink-muted mt-1 leading-relaxed">
            Dashboard, KB, Research + Chat are live. More surfaces ship next.
          </div>
        </div>
      </div>
    </aside>
  );
}
