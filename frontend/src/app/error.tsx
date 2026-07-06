"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Next.js route-level error boundary.
 * Catches render errors in any route segment without crashing the whole app.
 * Styled with the existing glass-panel utility from globals.css.
 */
export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log to console; in production you'd forward to an error tracker
    console.error("[Route Error]", error);
  }, [error]);

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="glass-panel rounded-2xl p-8 max-w-lg w-full space-y-5 text-center">
        {/* Icon */}
        <div className="flex justify-center">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <AlertCircle className="w-7 h-7 text-rose-400" />
          </div>
        </div>

        {/* Heading */}
        <div className="space-y-1.5">
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">
            Something went wrong
          </h1>
          <p className="text-sm text-zinc-400 leading-relaxed max-w-sm mx-auto">
            {error.message || "An unexpected error occurred in this view."}
          </p>
        </div>

        {/* Digest */}
        {error.digest && (
          <p className="text-[10px] font-mono text-zinc-600 bg-zinc-950/40 border border-zinc-800/30 rounded-lg px-3 py-1.5 inline-block">
            digest: {error.digest}
          </p>
        )}

        {/* Reset button */}
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary/15 border border-primary/25 text-primary text-sm font-semibold hover:bg-primary/20 transition-all duration-200 shadow-[0_0_20px_-4px_rgba(214,91,180,0.30)] hover:shadow-[0_0_24px_-4px_rgba(214,91,180,0.45)]"
        >
          <RefreshCw className="w-4 h-4" />
          Try again
        </button>
      </div>
    </div>
  );
}
