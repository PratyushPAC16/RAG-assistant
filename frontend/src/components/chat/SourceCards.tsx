"use client";

import React, { useState } from "react";
import { FileText, ChevronDown, ChevronUp, Copy, Check, Hash } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { SourceCitation } from "@/types";

interface SourceCardsProps {
  sources: SourceCitation[];
  hideHeader?: boolean;
}

export default function SourceCards({ sources, hideHeader = false }: SourceCardsProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  if (!sources || sources.length === 0) return null;

  const handleCopy = async (text: string, index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error("Failed to copy source text:", err);
    }
  };

  // Helper to clean up ugly 32-character hex UUID prefixes from document names
  const cleanDocName = (name: string) => {
    if (!name) return "";
    return name.replace(/^[a-fA-F0-9]{32}_/i, "");
  };

  // Helper to scale any input score to 0-100% match score
  const getMatchPercentage = (score: number | undefined | null): number | null => {
    if (score === undefined || score === null) return null;
    
    // If the score is outside [0, 1] bounds, treat it as a cross-encoder logit score
    if (score < 0 || score > 1) {
      const sigmoid = 1 / (1 + Math.exp(-score));
      return Math.round(sigmoid * 100);
    }
    
    // Otherwise, treat as normal normalized similarity score (0.0 to 1.0)
    return Math.round(score * 100);
  };

  // Color mappings based on match percentage
  const getScoreColor = (pct: number | null) => {
    if (pct === null) {
      return {
        border: "border-zinc-800",
        text: "text-zinc-400 bg-zinc-800/30 border-zinc-800",
        accent: "bg-zinc-700",
      };
    }
    if (pct >= 85) {
      return {
        border: "border-emerald-500/25",
        text: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        accent: "bg-emerald-500",
      };
    }
    if (pct >= 65) {
      return {
        border: "border-amber-500/25",
        text: "text-amber-400 bg-amber-500/10 border-amber-500/20",
        accent: "bg-amber-500",
      };
    }
    if (pct >= 40) {
      return {
        border: "border-orange-500/25",
        text: "text-orange-400 bg-orange-500/10 border-orange-500/20",
        accent: "bg-orange-500",
      };
    }
    return {
      border: "border-rose-500/25",
      text: "text-rose-400 bg-rose-500/10 border-rose-500/20",
      accent: "bg-rose-500",
    };
  };

  return (
    <div className={cn("w-full", !hideHeader && "mt-4 space-y-3.5")}>
      {!hideHeader && (
        <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-1 flex items-center gap-1.5 select-none">
          <FileText className="w-3.5 h-3.5 text-zinc-500" />
          Supporting Sources ({sources.length})
        </div>
      )}

      <div className="flex flex-col gap-3">
        {sources.map((src, idx) => {
          const isExpanded = expandedIndex === idx;
          const formattedScore = getMatchPercentage(src.relevance_score);
          const colors = getScoreColor(formattedScore);

          const previewText = src.text || "";
          const shortPreview = previewText.length > 95
            ? `${previewText.slice(0, 95)}...`
            : previewText;

          return (
            <div
              key={idx}
              onClick={() => setExpandedIndex(isExpanded ? null : idx)}
              className={cn(
                "group relative rounded-xl border pl-4 pr-3.5 py-3.5 transition-all duration-300 cursor-pointer select-none overflow-hidden backdrop-blur-md",
                isExpanded
                  ? "bg-zinc-900/90 border-zinc-700/80 shadow-lg shadow-zinc-950/50"
                  : "bg-zinc-900/40 border-zinc-850/60 hover:bg-zinc-900/60 hover:border-zinc-850 hover:shadow-md"
              )}
            >
              {/* Vertical Color Indicator Line */}
              <div className={cn("absolute left-0 top-0 bottom-0 w-[3px]", colors.accent)} />

              {/* Dynamic border lighting gradient line */}
              <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

              {/* Card Header */}
              <div className="flex items-start justify-between gap-2.5">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-7.5 h-7.5 rounded-lg bg-zinc-950 border border-zinc-850 flex items-center justify-center shrink-0 shadow-inner">
                    <FileText className="w-3.5 h-3.5 text-primary group-hover:scale-105 transition-transform duration-200" />
                  </div>
                  <div className="min-w-0">
                    <div
                      className="text-xs font-bold text-zinc-200 truncate group-hover:text-zinc-100 transition-colors"
                      title={src.document}
                    >
                      {cleanDocName(src.document)}
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5 text-[9px] text-zinc-500 font-mono">
                      {src.page !== undefined && src.page !== null && (
                        <span className="bg-zinc-950/40 border border-zinc-900 px-1 py-0.5 rounded text-zinc-400">
                          Page {src.page}
                        </span>
                      )}
                      {src.chunk_id && (
                        <span
                          className="flex items-center gap-0.5 bg-zinc-950/40 border border-zinc-900 px-1 py-0.5 rounded text-zinc-400 max-w-[90px] truncate"
                          title={src.chunk_id}
                        >
                          <Hash className="w-2 h-2 text-zinc-600 shrink-0" />
                          {src.chunk_id.replace("chunk_", "")}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Score badge */}
                {formattedScore !== null && (
                  <div
                    className={cn(
                      "shrink-0 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border shadow-sm",
                      colors.text
                    )}
                  >
                    {formattedScore}% Match
                  </div>
                )}
              </div>

              {/* Card Preview Text */}
              <div className="mt-3 text-[11px] leading-relaxed text-zinc-400 font-sans pl-2 border-l border-zinc-800 group-hover:border-zinc-700/80 transition-colors select-text">
                {!isExpanded ? (
                  <p className="italic">"{shortPreview}"</p>
                ) : (
                  <p className="italic text-zinc-350">"{previewText.slice(0, 120)}..."</p>
                )}
              </div>

              {/* Expand Details Trigger */}
              <div className="mt-3 flex items-center justify-between border-t border-zinc-900/50 pt-2.5">
                <button
                  type="button"
                  className="text-[10px] text-zinc-550 group-hover:text-zinc-350 flex items-center gap-1 font-bold uppercase tracking-wider transition-colors"
                >
                  {isExpanded ? (
                    <>
                      <span>Collapse</span>
                      <ChevronUp className="w-3.5 h-3.5" />
                    </>
                  ) : (
                    <>
                      <span>View Full Chunk</span>
                      <ChevronDown className="w-3.5 h-3.5 group-hover:translate-y-0.5 transition-transform" />
                    </>
                  )}
                </button>

                {isExpanded && previewText && (
                  <button
                    type="button"
                    onClick={(e) => handleCopy(previewText, idx, e)}
                    className="px-2 py-0.5 hover:bg-zinc-900 border border-zinc-850 hover:border-zinc-800 rounded text-zinc-500 hover:text-zinc-300 transition-all z-20 flex items-center gap-1 shrink-0"
                    title="Copy Full Chunk Content"
                  >
                    {copiedIndex === idx ? (
                      <>
                        <Check className="w-2.5 h-2.5 text-emerald-400 animate-pulse" />
                        <span className="text-[8px] text-emerald-400 font-mono">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-2.5 h-2.5" />
                        <span className="text-[8px] font-mono">Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Full context text expanded */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0, marginTop: 0 }}
                    animate={{ height: "auto", opacity: 1, marginTop: 12 }}
                    exit={{ height: 0, opacity: 0, marginTop: 0 }}
                    transition={{ duration: 0.25, ease: "easeInOut" }}
                    className="overflow-hidden border-t border-zinc-850/60 pt-3"
                  >
                    <div
                      className="rounded-lg bg-zinc-950/80 border border-zinc-900/60 p-3 max-h-48 overflow-y-auto font-mono text-[10px] text-zinc-350 leading-relaxed select-text select-all custom-scrollbar cursor-text"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {previewText}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </div>
  );
}
