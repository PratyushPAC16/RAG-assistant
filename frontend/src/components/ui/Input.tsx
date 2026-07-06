import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          // Base glass surface
          "flex h-9 w-full",
          "bg-[var(--glass-fill)] backdrop-blur-[12px]",
          "border border-[var(--glass-border)] rounded-xl",
          "px-3 py-1 text-sm text-white",
          "shadow-[0_1px_0_var(--glass-specular-soft)_inset,0_2px_6px_rgba(0,0,0,0.18)]",

          // Placeholder
          "placeholder:text-[rgba(150,140,160,0.60)]",

          // Focus — specular ring + brand glow
          "focus-visible:outline-none",
          "focus-visible:border-[rgba(214,91,180,0.50)]",
          "focus-visible:shadow-[0_1px_0_var(--glass-specular-soft)_inset,0_0_0_3px_rgba(214,91,180,0.14),0_2px_10px_rgba(214,91,180,0.12)]",

          // Transitions
          "transition-all duration-200",

          // Disabled
          "disabled:cursor-not-allowed disabled:opacity-40",

          // File input reset
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",

          className
        )}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
