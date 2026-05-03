import { cn } from "@/lib/utils";
import { ReactNode } from "react";

export function Card({
  children,
  className,
  glass = false,
}: {
  children: ReactNode;
  className?: string;
  glass?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-ink-line shadow-soft",
        glass ? "glass" : "bg-bg-elevated",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  right,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between px-5 pt-4 pb-3">
      <div>
        <div className="text-sm font-medium text-ink">{title}</div>
        {subtitle && (
          <div className="text-xs text-ink-subtle mt-0.5">{subtitle}</div>
        )}
      </div>
      {right}
    </div>
  );
}

export function CardBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("px-5 pb-5", className)}>{children}</div>;
}
