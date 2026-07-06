import * as React from "react";
import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glass?: boolean;
  /** Elevated = slightly more opaque glass surface, hovers with lift */
  elevated?: boolean;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, glass = false, elevated = false, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-[20px] transition-all duration-300",
        // Always apply glass-card (Liquid Glass surface) — glass prop kept for back-compat
        "glass-card",
        // Elevated variant: slightly stronger shadow tint
        elevated && "shadow-[0_20px_60px_rgba(0,0,0,0.50),0_1px_0_rgba(255,255,255,0.12)_inset]",
        className
      )}
      {...props}
    />
  )
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6 relative z-10", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-lg font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0 relative z-10", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex items-center p-6 pt-0 relative z-10",
      "border-t border-[var(--glass-border)] mt-4",
      className
    )}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

/**
 * CardSection — an inset glass surface for stat chips, data rows, etc.
 * Uses the `glass-inset` class for a recessed appearance.
 */
const CardSection = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("glass-inset p-3 rounded-xl", className)}
    {...props}
  />
));
CardSection.displayName = "CardSection";

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, CardSection };
