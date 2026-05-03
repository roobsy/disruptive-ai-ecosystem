import { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatTile({
  label,
  value,
  trend,
  icon,
  accent,
}: {
  label: string;
  value: ReactNode;
  trend?: string;
  icon?: ReactNode;
  accent?: boolean;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-ink-subtle">
            {label}
          </div>
          <div
            className={cn(
              "mt-2 text-3xl font-semibold tracking-tight",
              accent ? "text-accent" : "text-ink"
            )}
          >
            {value}
          </div>
          {trend && (
            <div className="mt-1 text-xs text-ink-muted">{trend}</div>
          )}
        </div>
        {icon && (
          <div className="h-9 w-9 rounded-lg bg-bg-subtle grid place-items-center text-ink-muted">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}
