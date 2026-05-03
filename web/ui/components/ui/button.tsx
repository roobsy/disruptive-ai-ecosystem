import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "ghost" | "outline";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
}

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { className, variant = "outline", size = "md", ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all",
        "focus:outline-none focus:ring-2 focus:ring-accent-ring focus:ring-offset-1 focus:ring-offset-bg",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-sm",
        variant === "primary" &&
          "bg-ink text-bg-elevated hover:bg-ink/90 shadow-soft",
        variant === "outline" &&
          "border border-ink-line bg-bg-elevated hover:bg-bg-subtle text-ink",
        variant === "ghost" && "text-ink-muted hover:text-ink hover:bg-bg-subtle",
        className
      )}
      {...rest}
    />
  );
});
