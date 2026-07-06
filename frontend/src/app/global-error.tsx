"use client";

import { useEffect } from "react";
import { AlertOctagon, RefreshCw } from "lucide-react";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Next.js global error boundary — wraps the root layout.
 * This must render its own <html> and <body> tags because it replaces the root
 * layout entirely when a root-layout-level error occurs.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error("[Global Error]", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: "hsl(30, 6.2%, 6.3%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif",
          color: "#f5f5f7",
        }}
      >
        <div
          style={{
            maxWidth: 480,
            width: "100%",
            padding: "2rem",
            textAlign: "center",
            borderRadius: 24,
            background: "rgba(28, 22, 30, 0.80)",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow:
              "0 20px 60px rgba(0,0,0,0.60), inset 0 1px 0 rgba(255,255,255,0.08)",
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: "rgba(239,68,68,0.10)",
              border: "1px solid rgba(239,68,68,0.20)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 1.5rem",
            }}
          >
            <AlertOctagon
              style={{ width: 28, height: 28, color: "#f87171" }}
            />
          </div>

          <h1
            style={{
              fontSize: "1.125rem",
              fontWeight: 600,
              letterSpacing: "-0.022em",
              marginBottom: "0.5rem",
            }}
          >
            Application Error
          </h1>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgba(161,161,170,0.85)",
              lineHeight: 1.6,
              marginBottom: "1.5rem",
            }}
          >
            {error.message ||
              "A critical error occurred. Please reload the page."}
          </p>

          {error.digest && (
            <p
              style={{
                fontSize: "0.625rem",
                fontFamily: "ui-monospace, 'SF Mono', monospace",
                color: "rgba(113,113,122,0.80)",
                background: "rgba(9,9,11,0.40)",
                border: "1px solid rgba(63,63,70,0.30)",
                borderRadius: 8,
                padding: "0.25rem 0.75rem",
                display: "inline-block",
                marginBottom: "1.5rem",
              }}
            >
              digest: {error.digest}
            </p>
          )}

          <br />
          <button
            onClick={reset}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.625rem 1.25rem",
              borderRadius: 12,
              background: "rgba(214,91,180,0.15)",
              border: "1px solid rgba(214,91,180,0.25)",
              color: "#D65BB4",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 200ms ease",
            }}
          >
            <RefreshCw style={{ width: 16, height: 16 }} />
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
