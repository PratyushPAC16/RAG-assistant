"use client";

import React, { useState } from "react";
import { FileText, ChevronDown, ChevronUp, Copy, Check, Hash } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { SourceCitation } from "@/types";

interface SourceCardsProps {
  sources: SourceCitation[];
}

export default function SourceCards({ sources }: SourceCardsProps) {
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

  return (
    <div className="space-y-3 mt-3 w-full">
      <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-1 flex items-center gap-1.5 select-none">
        <FileText className="w-3.5 h-3.5 text-zinc-500" />
        Supporting Sources ({sources.length})
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {sources.map((src, idx) => {
          const isExpanded = expandedIndex === idx;
          const score = src.relevance_score !== undefined
            ? Math.round(src.relevance_score * 100)
            : src.relevance_score; // if already 0-100 or null

          // Handle if relevance score is 0-1 vs 0-100
          const formattedScore = score !== undefined && score <= 1
            ? Math.round(score * 100)
            : score;

          const hasScore = formattedScore !== undefined && formattedScore !== null;
          const previewText = src.text || "";
          const shortPreview = previewText.length > 95
            ? `${previewText.slice(0, 95)}...`
            : previewText;

          return (
            <div
              key={idx}
              onClick={() => setExpandedIndex(isExpanded ? null : idx)}
              className={cn(
                "group relative rounded-xl border p-3.5 transition-all duration-300 cursor-pointer select-none overflow-hidden",
                isExpanded
                  ? "bg-zinc-950/80 border-primary/30 shadow-lg shadow-primary/5"
                  : "bg-zinc-900/20 border-zinc-850/60 hover:bg-zinc-900/40 hover:border-zinc-800 hover:shadow-md glass-card"
              )}
            >
              {/* Dynamic border lighting gradient line */}
              <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

              {/* Card Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-zinc-950 border border-zinc-850 flex items-center justify-center shrink-0">
                    <FileText className="w-3.5 h-3.5 text-primary group-hover:scale-110 transition-transform duration-200" />
                  </div>
                  <div className="min-w-0">
                    <div
                      className="text-xs font-bold text-zinc-200 truncate group-hover:text-zinc-100 transition-colors"
                      title={src.document}
                    >
                      {src.document}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 text-[10px] text-zinc-500 font-mono">
                      {src.page !== undefined && src.page !== null && (
                        <span>Page {src.page}</span>
                      )}
                      {src.page !== undefined && src.page !== null && src.chunk_id && (
                        <span className="text-zinc-700 select-none">•</span>
                      )}
                      {src.chunk_id && (
                        <span className="flex items-center gap-0.5 max-w-[80px] truncate" title={src.chunk_id}>
                          <Hash className="w-2.5 h-2.5 text-zinc-650" />
                          {src.chunk_id.replace("chunk_", "")}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Score badge */}
                {hasScore && (
                  <div
                    className={cn(
                      "shrink-0 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border",
                      formattedScore! >= 80
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.05)]"
                        : formattedScore! >= 60
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-zinc-850/50 text-zinc-400 border-zinc-800"
                    )}
                  >
                    {formattedScore}% Match
                  </div>
                )}
              </div>

              {/* Card Preview Text */}
              <div className="mt-3 text-[11px] leading-relaxed text-zinc-450 font-sans select-text">
                {!isExpanded ? (
                  <p className="italic">"{shortPreview}"</p>
                ) : (
                  <p className="italic text-zinc-400">"{previewText.slice(0, 120)}..."</p>
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
                    className="p-1 hover:bg-zinc-900 rounded text-zinc-500 hover:text-zinc-300 transition-colors z-20"
                    title="Copy Full Chunk Content"
                  >
                    {copiedIndex === idx ? (
                      <Check className="w-3 h-3 text-emerald-400 animate-pulse" />
                    ) : (
                      <Copy className="w-3 h-3" />
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
                      className="rounded-lg bg-zinc-950/80 border border-zinc-900 p-3 max-h-48 overflow-y-auto font-mono text-[10px] text-zinc-350 leading-relaxed select-text select-all custom-scrollbar cursor-text"
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
