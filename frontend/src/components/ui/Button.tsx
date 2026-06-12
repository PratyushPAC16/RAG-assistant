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
          "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 active:scale-95",
          {
            // default
            "bg-[#1A171B] border border-[#66415C]/40 text-white hover:bg-[#1A171B]/80 hover:border-[#D65BB4]/35 hover:shadow-[0_0_15px_rgba(214,91,180,0.08)]":
              variant === "default",
            // primary
            "bg-gradient-to-r from-[#D65BB4] to-[#66415C] text-white hover:opacity-95 shadow-[0_4px_20px_rgba(214,91,180,0.22)] hover:shadow-[0_6px_25px_rgba(214,91,180,0.35)] hover:scale-[1.01] border border-[#D65BB4]/20":
              variant === "primary",
            // secondary
            "bg-[#66415C]/35 border border-[#66415C]/50 text-zinc-100 hover:bg-[#66415C]/45 hover:text-white":
              variant === "secondary",
            // destructive
            "bg-rose-500/80 text-white border border-rose-500/30 hover:bg-rose-600":
              variant === "destructive",
            // outline
            "border border-[#66415C]/40 bg-transparent hover:bg-[#66415C]/20 hover:border-[#D65BB4]/30 text-zinc-200 hover:text-white":
              variant === "outline",
            // ghost
            "hover:bg-[#66415C]/20 hover:text-white bg-transparent text-zinc-300":
              variant === "ghost",
            // link
            "text-[#D65BB4] underline-offset-4 hover:underline":
              variant === "link",
          },
          {
            "h-9 px-4 py-2": size === "default",
            "h-8 rounded-lg px-3 text-xs": size === "sm",
            "h-10 rounded-[14px] px-8": size === "lg",
            "h-9 w-9 p-0": size === "icon",
          },
          className
        )}
        {...props}
      >
        {loading ? (
          <span className="flex items-center gap-1">
            <svg
              className="animate-spin -ml-1 mr-1 h-4 w-4 text-current"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Loading...
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
