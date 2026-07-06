import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary" | "secondary" | "destructive" | "outline" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", loading = false, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={loading || props.disabled}
        className={cn(
          // Base — shared across all variants
          "relative inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium",
          "rounded-xl select-none overflow-hidden",
          "transition-all duration-200 focus-visible:outline-none",
          "focus-visible:ring-2 focus-visible:ring-[rgba(214,91,180,0.55)] focus-visible:ring-offset-1 focus-visible:ring-offset-transparent",
          "disabled:pointer-events-none disabled:opacity-45",
          "active:scale-[0.96]",

          // ── Variants ──────────────────────────────────────────────────────
          variant === "primary" && [
            // Liquid glass tinted with brand gradient + specular highlight
            "glass-shimmer-on-hover",
            "bg-gradient-to-br from-[rgba(214,91,180,0.90)] via-[rgba(180,70,160,0.85)] to-[rgba(102,65,92,0.90)]",
            "border border-[rgba(214,91,180,0.35)]",
            "shadow-[0_4px_20px_rgba(214,91,180,0.28),0_1px_0_rgba(255,255,255,0.20)_inset,0_-1px_0_rgba(0,0,0,0.15)_inset]",
            "text-white",
            "hover:shadow-[0_6px_28px_rgba(214,91,180,0.42),0_1px_0_rgba(255,255,255,0.22)_inset]",
            "hover:border-[rgba(214,91,180,0.50)]",
            "hover:brightness-105",
          ],

          variant === "default" && [
            // Glass chrome — frosted dark surface
            "glass-shimmer-on-hover",
            "bg-[var(--glass-fill)] backdrop-blur-[12px]",
            "border border-[var(--glass-border)]",
            "shadow-[var(--glass-shadow-sm)]",
            "text-zinc-200",
            "hover:bg-[var(--glass-fill-elevated)]",
            "hover:border-[var(--glass-border-strong)]",
            "hover:text-white",
          ],

          variant === "outline" && [
            // Frosted glass pill with brand border tint
            "glass-shimmer-on-hover",
            "bg-[rgba(214,91,180,0.05)] backdrop-blur-[12px]",
            "border border-[rgba(214,91,180,0.28)]",
            "shadow-[0_2px_8px_rgba(0,0,0,0.20),0_1px_0_rgba(255,255,255,0.07)_inset]",
            "text-zinc-200",
            "hover:bg-[rgba(214,91,180,0.10)]",
            "hover:border-[rgba(214,91,180,0.45)]",
            "hover:text-white",
            "hover:shadow-[0_4px_16px_rgba(214,91,180,0.15),0_1px_0_rgba(255,255,255,0.10)_inset]",
          ],

          variant === "secondary" && [
            "bg-[rgba(102,65,92,0.30)] backdrop-blur-[12px]",
            "border border-[rgba(102,65,92,0.45)]",
            "shadow-[var(--glass-shadow-sm)]",
            "text-zinc-100",
            "hover:bg-[rgba(102,65,92,0.45)]",
            "hover:text-white",
          ],

          variant === "destructive" && [
            "bg-[rgba(251,113,133,0.15)] backdrop-blur-[12px]",
            "border border-[rgba(251,113,133,0.30)]",
            "shadow-[0_2px_10px_rgba(251,113,133,0.15),0_1px_0_rgba(255,255,255,0.06)_inset]",
            "text-rose-300",
            "hover:bg-[rgba(251,113,133,0.25)]",
            "hover:text-rose-200",
            "hover:shadow-[0_4px_16px_rgba(251,113,133,0.25)]",
          ],

          variant === "ghost" && [
            "bg-transparent border-transparent",
            "text-zinc-300",
            "hover:bg-[var(--glass-fill)] hover:text-white",
            "hover:border-[var(--glass-border-subtle)]",
          ],

          variant === "link" && [
            "bg-transparent border-transparent text-[#D65BB4]",
            "underline-offset-4 hover:underline",
            "shadow-none",
          ],

          // ── Sizes ─────────────────────────────────────────────────────────
          size === "default" && "h-9 px-4 py-2",
          size === "sm" && "h-8 rounded-lg px-3 text-xs",
          size === "lg" && "h-10 rounded-[14px] px-8",
          size === "icon" && "h-9 w-9 p-0",

          className
        )}
        {...props}
      >
        {/* Specular top-edge highlight for solid variants */}
        {(variant === "primary" || variant === "default" || variant === "outline") && (
          <span
            className="absolute inset-x-0 top-0 h-[1px] rounded-t-xl pointer-events-none"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.28), transparent)",
            }}
            aria-hidden
          />
        )}

        {loading ? (
          <span className="flex items-center gap-1.5">
            <svg
              className="animate-spin h-3.5 w-3.5 text-current"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Loading…
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button };
