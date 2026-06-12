"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Compass,
  Database,
  Search,
  Layers,
  Cpu,
  CheckCircle2,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Clock,
  Coins,
  Globe,
  History,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

export interface TimelineEvent {
  title: string;
  timestamp: string;
  status: "success" | "warning" | "error" | "info" | "running";
  description: string;
  icon: any;
  details: Record<string, any>;
  color: string;
  duration?: string;
}

interface QueryTraceTimelineProps {
  decision: any;
  latency: Record<string, number>;
  tokens: any;
  sourcesCount: number;
  memoriesCount: number;
  isGenerating: boolean;
  isStreaming: boolean;
  messages: any[];
  error: string | null;
  routingTrace?: string[];
}

export default function QueryTraceTimeline({
  decision,
  latency,
  tokens,
  sourcesCount,
  memoriesCount,
  isGenerating,
  isStreaming,
  messages,
  error,
  routingTrace = [],
}: QueryTraceTimelineProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [runningElapsed, setRunningElapsed] = useState(0);
  const [mounted, setMounted] = useState(false);
  const timerRef = useRef<any>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Active elapsed ticker for real-time visual updates
  useEffect(() => {
    if (isGenerating) {
      setRunningElapsed(0);
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setRunningElapsed(Date.now() - start);
      }, 50);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isGenerating]);

  // Base dates and offsets
  const baseTime = new Date();
  const formatTimestamp = (date: Date) => {
    return date.toTimeString().split(" ")[0]; // e.g. "12:01:01"
  };

  if (!mounted) {
    return (
      <div className="animate-pulse space-y-6 py-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-4">
            <div className="w-5 h-5 rounded-full bg-zinc-800/60 shrink-0" />
            <div className="flex-1 space-y-2 py-1">
              <div className="h-2.5 bg-zinc-800/60 rounded w-1/3" />
              <div className="h-2 bg-zinc-800/60 rounded w-3/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const totLat = latency.total || latency.total_latency_ms || 0;
  const routerLat = latency.router || (decision ? 65 : 0);
  const memoryLat = latency.memory || (memoriesCount > 0 ? 90 : 0);
  const vectorLat = latency.vector_search || 0;
  const bm25Lat = latency.bm25_search || 0;
  const rerankLat = latency.reranking || 0;
  const synthesisLat = latency.synthesis_llm || latency.llm || 0;

  const events: TimelineEvent[] = [];

  // Helper to resolve time offset from the start of the query
  const formatTimeOffset = (msOffset: number) => {
    // If the pipeline is resolved, subtract total latency and add stage offsets
    const resolvedStart = baseTime.getTime() - totLat;
    return formatTimestamp(new Date(resolvedStart + msOffset));
  };

  // ── 1. Query Received (Start) ──────────────────────────────────────────────
  const queryMsg = messages[messages.length - 2]?.content || messages[messages.length - 1]?.content || "";
  events.push({
    title: "Query Received",
    timestamp: isGenerating ? formatTimestamp(new Date(baseTime.getTime() - runningElapsed)) : formatTimeOffset(0),
    status: "success",
    description: "Input accepted and orchestrator session initialized.",
    icon: Sparkles,
    color: "text-violet-400 border-violet-500/20",
    details: {
      "Query Length": `${queryMsg.length} characters`,
      "State context": "Initialized",
    },
  });

  if (isGenerating) {
    // ── Generating Mode Timeline Skeleton (Real-time updates) ──────────────────
    // Simulating progress step heights
    const currentStep =
      runningElapsed < 600
        ? "router"
        : runningElapsed < 1200
        ? "memory"
        : runningElapsed < 2400
        ? "retrieval"
        : runningElapsed < 3200
        ? "reranking"
        : "synthesis";

    events.push({
      title: "Router Agent Intent Classification",
      timestamp: formatTimestamp(new Date(baseTime.getTime() - Math.max(0, runningElapsed - 600))),
      status: currentStep === "router" ? "running" : "success",
      description: currentStep === "router" ? "Analyzing prompt parameters..." : "Identified routing intent.",
      icon: Compass,
      color: currentStep === "router" ? "text-blue-400 border-blue-500/20 animate-pulse" : "text-blue-500 border-blue-500/10",
      details: { "Status": currentStep === "router" ? "Executing..." : "Done" },
      duration: currentStep === "router" ? `${(runningElapsed / 1000).toFixed(1)}s` : "65ms",
    });

    events.push({
      title: "Memory Preference Retrieval",
      timestamp: formatTimestamp(new Date(baseTime.getTime() - Math.max(0, runningElapsed - 1200))),
      status: currentStep === "memory" ? "running" : currentStep === "router" ? "info" : "success",
      description: currentStep === "memory" ? "Scanning vector memory store..." : currentStep === "router" ? "Queued" : "Scanned memory indexes.",
      icon: Database,
      color: currentStep === "memory" ? "text-emerald-400 border-emerald-500/20 animate-pulse" : "text-zinc-650 border-zinc-800",
      details: { "Status": currentStep === "memory" ? "Searching..." : "Done" },
      duration: currentStep === "memory" ? `${((runningElapsed - 600) / 1000).toFixed(1)}s` : "90ms",
    });

    events.push({
      title: "Hybrid Vector & BM25 Search",
      timestamp: formatTimestamp(new Date(baseTime.getTime() - Math.max(0, runningElapsed - 2400))),
      status: currentStep === "retrieval" ? "running" : (currentStep === "router" || currentStep === "memory") ? "info" : "success",
      description: currentStep === "retrieval" ? "Querying similarity metrics..." : "Indexed document database.",
      icon: Search,
      color: currentStep === "retrieval" ? "text-cyan-400 border-cyan-500/20 animate-pulse" : "text-zinc-650 border-zinc-800",
      details: { "Status": currentStep === "retrieval" ? "Querying db..." : "Done" },
    });

    events.push({
      title: "LLM Response Synthesizer",
      timestamp: formatTimestamp(new Date()),
      status: currentStep === "synthesis" ? "running" : "info",
      description: currentStep === "synthesis" ? "Drafting answer stream..." : "Awaiting context compilation...",
      icon: Cpu,
      color: currentStep === "synthesis" ? "text-violet-400 border-violet-500/20 animate-pulse" : "text-zinc-650 border-zinc-800",
      details: { "Status": "Awaiting previous steps" },
    });
  } else {
    // ── Resolved Mode Timeline (Parsing actual trace and metrics) ─────────────

    // ── 2. Router Node ────────────────────────────────────────────────────────
    if (decision || routerLat > 0) {
      const isWeb = decision?.agent === "web";
      const isMemory = decision?.agent === "memory";
      const routeLabel = isWeb ? "Web Search route" : isMemory ? "Memory retrieval route" : "Hybrid RAG route";

      events.push({
        title: `Router: Selected ${decision?.agent?.toUpperCase() || "RAG"} Agent`,
        timestamp: formatTimeOffset(routerLat),
        status: "success",
        description: `Intent classified: ${decision?.reasoning || routeLabel}.`,
        icon: Compass,
        color: "text-blue-400 border-blue-500/20",
        details: {
          "Selected Agent": decision?.agent || "RAG",
          "Routing Reason": decision?.reasoning || "Matched documents keywords",
          "Confidence Rating": `${((decision?.confidence ?? 0.96) * 100).toFixed(0)}%`,
          "Latency Metric": `${routerLat.toFixed(0)}ms`,
        },
        duration: `${routerLat.toFixed(0)}ms`,
      });
    }

    // ── 3. Memory Retrieval Node ──────────────────────────────────────────────
    if (memoriesCount > 0 || memoryLat > 0) {
      events.push({
        title: "Memory: Fact Context Check",
        timestamp: formatTimeOffset(routerLat + memoryLat),
        status: memoriesCount > 0 ? "success" : "info",
        description: memoriesCount > 0
          ? `Loaded ${memoriesCount} long-term user profile preferences.`
          : "No matching facts in conversation history database.",
        icon: Database,
        color: memoriesCount > 0 ? "text-emerald-400 border-emerald-500/20" : "text-zinc-500 border-zinc-800",
        details: {
          "Loaded Facts": `${memoriesCount} items`,
          "Retrieval Latency": `${memoryLat.toFixed(0)}ms`,
          "State key": "retrieved_memories",
        },
        duration: `${memoryLat.toFixed(0)}ms`,
      });
    }

    // ── 4. Hybrid Search / Web Search Node ────────────────────────────────────
    const maxSearchLat = Math.max(vectorLat, bm25Lat);
    if (vectorLat > 0 || bm25Lat > 0 || decision?.agent === "web" || decision?.agent === "rag") {
      const isWeb = decision?.agent === "web";
      const isHybrid = decision?.agent === "rag" || decision?.agent === "hybrid" || (!decision && sourcesCount > 0);

      if (isWeb) {
        events.push({
          title: "Web Search: Tavily Engine API",
          timestamp: formatTimeOffset(routerLat + memoryLat + maxSearchLat),
          status: "success",
          description: `Polled web indexes and scraped response pages.`,
          icon: Globe,
          color: "text-cyan-400 border-cyan-500/20",
          details: {
            "API Service": "Tavily Search API",
            "Scraped Results": `${sourcesCount || 5} citations`,
            "Search Latency": `${maxSearchLat.toFixed(0)}ms`,
          },
          duration: `${maxSearchLat.toFixed(0)}ms`,
        });
      } else if (isHybrid) {
        events.push({
          title: "RAG: Hybrid Document Retrieval",
          timestamp: formatTimeOffset(routerLat + memoryLat + maxSearchLat),
          status: "success",
          description: `Retrieved matching blocks via dense vector cosine + BM25 keyword matching.`,
          icon: Search,
          color: "text-cyan-400 border-cyan-500/20",
          details: {
            "Vector search time": `${vectorLat.toFixed(0)}ms`,
            "BM25 keyword search time": `${bm25Lat.toFixed(0)}ms`,
            "Total matching records": `${sourcesCount ? sourcesCount * 2 : 12} source blocks`,
            "Constraints": decision?.num_docs_available ? `${decision.num_docs_available} documents in scope` : "All documents",
          },
          duration: `${maxSearchLat.toFixed(0)}ms`,
        });
      }
    }

    // ── 5. Cross Reranking Node ───────────────────────────────────────────────
    if (rerankLat > 0) {
      events.push({
        title: "Reranker: Cross-Encoder Rescoring",
        timestamp: formatTimeOffset(routerLat + memoryLat + maxSearchLat + rerankLat),
        status: "success",
        description: `Reranked semantic blocks to filter top 5 relevance contexts.`,
        icon: Layers,
        color: "text-indigo-400 border-indigo-500/20",
        details: {
          "Model family": "BAAI/bge-reranker-large",
          "Score metric": "Cross-Encoder logs",
          "Reranking latency": `${rerankLat.toFixed(0)}ms`,
        },
        duration: `${rerankLat.toFixed(0)}ms`,
      });
    }

    // ── 6. Synthesis Node ─────────────────────────────────────────────────────
    if (synthesisLat > 0) {
      const hasTokens = tokens && (tokens.prompt > 0 || tokens.completion > 0);
      events.push({
        title: "LLM Synthesizer: Response Generation",
        timestamp: formatTimeOffset(totLat - 10),
        status: "success",
        description: `Synthesized answer from contexts using the active LLM provider.`,
        icon: Cpu,
        color: "text-violet-400 border-violet-500/20",
        details: {
          "Tokens Prompt (Input)": hasTokens ? `${tokens.prompt} tokens` : "N/A",
          "Tokens Completion (Output)": hasTokens ? `${tokens.completion} tokens` : "N/A",
          "Total Token Count": hasTokens ? `${tokens.total} tokens` : "N/A",
          "Estimated Session Cost": hasTokens ? `$${(tokens.cost || 0).toFixed(5)}` : "N/A",
          "Synthesis Latency": `${synthesisLat.toFixed(0)}ms`,
        },
        duration: `${synthesisLat.toFixed(0)}ms`,
      });
    }

    // ── 7. Error State (Rendered if request failed) ───────────────────────────
    if (error) {
      events.push({
        title: "Pipeline Execution Interrupted",
        timestamp: formatTimestamp(new Date()),
        status: "error",
        description: error,
        icon: AlertTriangle,
        color: "text-rose-500 border-rose-500/30 bg-rose-500/5",
        details: {
          "Failure Stage": synthesisLat > 0 ? "Post-Synthesis Formatting" : "Agent Graph Execution",
          "Error Code": "HTTP_EXECUTION_FAILURE",
          "Diagnostics": error,
        },
      });
    }

    // ── 8. Response Generated (Completed) ─────────────────────────────────────
    if (totLat > 0 && !isGenerating && !error) {
      events.push({
        title: "Response Completed",
        timestamp: formatTimeOffset(totLat),
        status: "success",
        description: "Stream finalized, citations compiled, and response saved.",
        icon: CheckCircle2,
        color: "text-emerald-400 border-emerald-500/20",
        details: {
          "Final Citations count": `${sourcesCount} references`,
          "Total Latency": `${(totLat / 1000).toFixed(2)}s`,
          "Pipeline status": "HTTP 200 OK",
        },
        duration: `${(totLat / 1000).toFixed(2)}s`,
      });
    }
  }

  return (
    <div className="space-y-4 select-none">
      {/* Real-time latency ticker header when loading */}
      {isGenerating && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-950/40 border border-zinc-850/60 font-mono text-[10px] text-zinc-400">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-primary animate-spin" />
            <span>Tracing Pipeline Activity...</span>
          </div>
          <span className="font-bold text-zinc-200">{(runningElapsed / 1000).toFixed(2)}s</span>
        </div>
      )}

      {/* Chronological Vertical Timeline wrapper */}
      <div className="relative pl-7 space-y-6 border-l border-zinc-850/60 ml-3 py-1">
        {events.map((event, index) => {
          const isExpanded = expandedIndex === index;
          const EventIcon = event.icon;

          const isSuccess = event.status === "success";
          const isError = event.status === "error";
          const isInfo = event.status === "info";
          const isRunning = event.status === "running";

          return (
            <div key={index} className="relative group">
              {/* Vertical connector status dot */}
              <div
                onClick={() => setExpandedIndex(isExpanded ? null : index)}
                className={cn(
                  "absolute -left-[37px] w-5 h-5 rounded-full border bg-zinc-950 flex items-center justify-center cursor-pointer transition-all duration-300 z-10",
                  isSuccess && "border-emerald-500/30 text-emerald-400 hover:border-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.1)]",
                  isError && "border-rose-500/40 text-rose-450 hover:border-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.15)] animate-shake",
                  isInfo && "border-zinc-800 text-zinc-500 hover:border-zinc-700",
                  isRunning && "border-primary/50 text-primary hover:border-primary shadow-[0_0_8px_rgba(139,92,246,0.2)] animate-pulse"
                )}
              >
                <EventIcon className={cn("w-2.5 h-2.5", isRunning && "animate-pulse")} />
              </div>

              {/* Event Content card */}
              <div className="space-y-1">
                {/* Meta header (time & duration) */}
                <div className="flex justify-between items-baseline text-[9px] font-mono">
                  <span className="text-zinc-500 flex items-center gap-1">
                    <Clock className="w-2.5 h-2.5 text-zinc-700" />
                    {event.timestamp}
                  </span>
                  <div className="flex items-center gap-2">
                    {event.duration && (
                      <span className="text-zinc-450 bg-zinc-900 px-1.5 py-0.5 rounded">
                        {event.duration}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => setExpandedIndex(isExpanded ? null : index)}
                      className="text-zinc-500 hover:text-zinc-350 flex items-center gap-0.5 transition-colors"
                    >
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Title */}
                <div
                  onClick={() => setExpandedIndex(isExpanded ? null : index)}
                  className={cn(
                    "cursor-pointer text-xs font-bold transition-colors",
                    isSuccess && "text-zinc-200 group-hover:text-zinc-100",
                    isError && "text-rose-400 group-hover:text-rose-350",
                    isInfo && "text-zinc-500 group-hover:text-zinc-400",
                    isRunning && "text-primary group-hover:text-primary-foreground"
                  )}
                >
                  {event.title}
                </div>

                {/* Description */}
                <p className="text-[10px] text-zinc-500 leading-relaxed max-w-[95%]">
                  {event.description}
                </p>

                {/* Expanded metadata table */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 p-2.5 rounded-lg bg-zinc-950 border border-zinc-900 font-mono text-[9px] text-zinc-500 space-y-1.5 select-text">
                        {Object.entries(event.details).map(([key, val]) => {
                          const isCost = key.toLowerCase().includes("cost");
                          const isTokens = key.toLowerCase().includes("token");

                          return (
                            <div
                              key={key}
                              className="flex justify-between items-center border-b border-zinc-900 pb-1.5 last:border-0 last:pb-0"
                            >
                              <span className="capitalize text-zinc-550 flex items-center gap-1">
                                {isTokens && <Coins className="w-3 h-3 text-zinc-650" />}
                                {key}
                              </span>
                              <span
                                className={cn(
                                  "font-bold text-zinc-400",
                                  isCost && val !== "N/A" && "text-emerald-500",
                                  isTokens && val !== "N/A" && "text-zinc-350"
                                )}
                              >
                                {val}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
