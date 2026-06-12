"use client";

import React, { useState, useEffect, useRef } from "react";
import { useChatStore } from "@/store/chatStore";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import {
  Activity,
  Files,
  Cpu,
  CheckCircle2,
  Clock,
  Compass,
  FileText,
  Search,
  Layers,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Database,
  Globe,
  Coins,
  FileSpreadsheet,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

type TabType = "workflow" | "citations" | "metrics";

export default function ObservabilityPanel() {
  const [activeTab, setActiveTab] = useState<TabType>("workflow");
  const {
    currentDecision,
    currentTrace,
    currentLatency,
    currentSources,
    currentMemories,
    currentTokens,
    isGenerating,
    isStreaming,
  } = useChatStore();

  const hasData = currentDecision || currentSources.length > 0 || Object.keys(currentLatency).length > 0;

  if (!hasData && !isGenerating) {
    return (
      <aside className="w-80 bg-zinc-950/60 border-l border-zinc-800/40 p-6 flex flex-col justify-center items-center text-center select-none backdrop-blur-md h-full relative">
        {/* Glow effect background */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-40 h-40 bg-violet-600/5 rounded-full blur-3xl" />
        <Activity className="w-8 h-8 text-zinc-700 mb-3 animate-pulse" />
        <span className="text-sm font-semibold text-zinc-300">Observability Engine</span>
        <p className="text-zinc-650 text-xs mt-2 max-w-[85%] leading-relaxed">
          Submit a message in the chat console to stream active agent paths, document sources, and token pricing telemetry.
        </p>
      </aside>
    );
  }

  return (
    <aside className="w-80 bg-zinc-950/60 border-l border-zinc-800/40 flex flex-col h-full overflow-hidden select-none backdrop-blur-md">
      {/* Header Tabs */}
      <div className="flex border-b border-zinc-850/40 bg-zinc-950/40 p-2 shrink-0">
        {(["workflow", "citations", "metrics"] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "flex-1 text-center py-2 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all duration-200 relative",
              activeTab === tab
                ? "text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300"
            )}
          >
            {tab}
            {activeTab === tab && (
              <motion.div
                layoutId="activeTabIndicator"
                className="absolute bottom-0 left-2 right-2 h-0.5 bg-primary rounded-full"
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === "workflow" && (
          <WorkflowTab
            decision={currentDecision}
            trace={currentTrace}
            latency={currentLatency}
            isGenerating={isGenerating}
            isStreaming={isStreaming}
          />
        )}
        {activeTab === "citations" && <CitationsTab sources={currentSources} memories={currentMemories} />}
        {activeTab === "metrics" && <MetricsTab tokens={currentTokens} latency={currentLatency} />}
      </div>
    </aside>
  );
}

// ── 1. Workflow Tab ──────────────────────────────────────────────────────────

interface WorkflowTabProps {
  decision: any;
  trace: string[];
  latency: Record<string, number>;
  isGenerating: boolean;
  isStreaming: boolean;
}

// Custom hook to run a ticker for active steps
function useStepTimer(isActive: boolean, finalValue?: number) {
  const [seconds, setSeconds] = useState(0);
  const timerRef = useRef<any>(null);

  useEffect(() => {
    if (isActive) {
      setSeconds(0);
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setSeconds(Date.now() - start);
      }, 35);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isActive]);

  return finalValue !== undefined && finalValue > 0 ? finalValue : seconds;
}

function WorkflowTab({ decision, trace, latency, isGenerating, isStreaming }: WorkflowTabProps) {
  const steps = [
    { key: "router", label: "Router Agent", icon: Compass, color: "text-blue-400 border-blue-500/20 bg-blue-500/5" },
    { key: "memory", label: "Memory Agent", icon: FileText, color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5" },
    { key: "vector", label: "Semantic Search", icon: Search, color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5" },
    { key: "bm25", label: "BM25 Search", icon: Search, color: "text-amber-400 border-amber-500/20 bg-amber-500/5" },
    { key: "reranker", label: "Cross-Reranker", icon: Layers, color: "text-indigo-400 border-indigo-500/20 bg-indigo-500/5" },
    { key: "synthesis", label: "Provider Layer", icon: Cpu, color: "text-violet-400 border-violet-500/20 bg-violet-500/5" },
    { key: "response", label: "Response Generation", icon: CheckCircle2, color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5" },
  ];

  const getStepStatus = (key: string) => {
    if (isGenerating && !decision) {
      if (key === "router") return "active";
      return "pending";
    }

    const matched = getMatchedStepLatency(key);
    if (matched !== undefined && matched > 0) return "done";

    if (isGenerating || isStreaming) {
      if (key === "response") return "pending";
      if (key === "synthesis" && (latency.retrieval || latency.vector_search)) return "active";
      if (key === "reranker" && latency.vector_search && !latency.reranking) return "active";
      if ((key === "vector" || key === "bm25") && decision && !latency.vector_search) return "active";
      if (key === "memory" && decision && !latency.vector_search) return "active";
    }

    if (decision || Object.keys(latency).length > 0) {
      return "done";
    }

    return "pending";
  };

  const getMatchedStepLatency = (key: string): number | undefined => {
    switch (key) {
      case "router":
        return latency.router || (decision ? 65 : undefined);
      case "memory":
        return latency.memory || (latency.retrieved_memories ? 90 : undefined);
      case "vector":
        return latency.vector_search;
      case "bm25":
        return latency.bm25_search;
      case "reranker":
        return latency.reranking;
      case "synthesis":
        return latency.synthesis_llm || latency.llm;
      case "response":
        return latency.total || latency.total_latency_ms;
      default:
        return undefined;
    }
  };

  return (
    <div className="space-y-6">
      {/* Route classification card */}
      {decision && (
        <Card className="bg-zinc-900/35 border-zinc-800/40 p-4 relative overflow-hidden glow-primary-hover backdrop-blur-sm">
          <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-primary shrink-0" />
            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Routing Path</span>
            <ArrowRight className="w-3.5 h-3.5 text-zinc-700" />
            <span className="text-xs font-bold text-primary uppercase bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
              {decision.agent}
            </span>
          </div>
          <p className="text-[11px] text-zinc-350 mt-2.5 leading-relaxed italic select-text">
            "{decision.reasoning}"
          </p>
          <div className="mt-3 flex items-center justify-between text-[9px] text-zinc-500 font-mono">
            <span>Confidence: {(decision.confidence * 100).toFixed(0)}%</span>
            <span>Trace Docs: {decision.num_docs_available}</span>
          </div>
        </Card>
      )}

      {/* SVG Connected Workflow Path */}
      <div className="relative pl-7 space-y-6 select-none">
        {/* SVG vertical line wrapper */}
        <div className="absolute left-[9px] top-3 bottom-3 w-0.5 bg-zinc-850">
          {isGenerating && (
            <motion.div
              initial={{ top: "0%" }}
              animate={{ top: "100%" }}
              transition={{ repeat: Infinity, duration: 2.2, ease: "linear" }}
              className="absolute left-0 w-[2px] h-12 bg-gradient-to-b from-transparent via-primary to-transparent"
            />
          )}
        </div>

        {steps.map((step, idx) => {
          const status = getStepStatus(step.key);
          const finalVal = getMatchedStepLatency(step.key);
          const timerVal = useStepTimer(status === "active", finalVal);
          const StepIcon = step.icon;

          return (
            <div key={step.key} className="relative flex items-center justify-between">
              {/* Floating connector circle */}
              <div
                className={cn(
                  "absolute -left-[30px] w-4.5 h-4.5 rounded-full border flex items-center justify-center transition-all duration-300 z-10",
                  status === "done"
                    ? "bg-emerald-500/10 border-emerald-500 text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.2)]"
                    : status === "active"
                    ? "bg-primary/20 border-primary text-primary scale-105 shadow-[0_0_12px_rgba(139,92,246,0.4)] animate-pulse"
                    : "bg-zinc-950 border-zinc-800 text-zinc-600"
                )}
              >
                <StepIcon className="w-2.5 h-2.5" />
              </div>

              {/* Step info display */}
              <div className="flex-1 flex justify-between items-center pl-1">
                <span
                  className={cn(
                    "text-xs transition-colors duration-200",
                    status === "done"
                      ? "text-zinc-300 font-medium"
                      : status === "active"
                      ? "text-primary font-bold"
                      : "text-zinc-500"
                  )}
                >
                  {step.label}
                </span>

                {(status === "done" || status === "active") && (
                  <span
                    className={cn(
                      "font-mono text-[10px]",
                      status === "active" ? "text-primary font-bold animate-pulse" : "text-zinc-500"
                    )}
                  >
                    {timerVal ? `${timerVal.toFixed(0)}ms` : "0ms"}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 2. Citations Tab ─────────────────────────────────────────────────────────

interface CitationsTabProps {
  sources: SourceCitation[];
  memories: MemoryRecord[];
}

function CitationCard({ citation }: { citation: SourceCitation }) {
  const [expanded, setExpanded] = useState(false);
  const relevance = citation.relevance_score ?? 0;
  
  // Color scale mapping
  const relevanceColor =
    relevance >= 0.9
      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      : relevance >= 0.7
      ? "text-cyan-400 bg-cyan-500/10 border-cyan-500/20"
      : "text-zinc-400 bg-zinc-800/40 border-zinc-700/20";

  return (
    <Card className="bg-zinc-900/35 border-zinc-850/40 hover:border-primary/20 hover:bg-zinc-900/50 transition-all duration-300 relative group overflow-hidden">
      <CardContent className="p-3 space-y-2.5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-1.5 min-w-0">
            <FileText className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <span className="text-[11px] font-bold text-zinc-200 truncate select-text" title={citation.document}>
              {citation.document}
            </span>
          </div>

          <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider shrink-0", relevanceColor)}>
            {(relevance * 100).toFixed(0)}% Match
          </span>
        </div>

        {/* Progress Bar score indicator */}
        <div className="w-full bg-zinc-950 h-1 rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full", {
              "bg-emerald-500": relevance >= 0.9,
              "bg-cyan-500": relevance >= 0.7 && relevance < 0.9,
              "bg-zinc-600": relevance < 0.7,
            })}
            style={{ width: `${relevance * 100}%` }}
          />
        </div>

        <div className="flex justify-between items-center text-[9px] text-zinc-500 font-semibold uppercase tracking-wider">
          <span>Page: {citation.page || "TXT"}</span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-primary hover:text-primary/80 flex items-center gap-0.5 transition-colors font-bold"
          >
            {expanded ? "Hide text" : "Preview text"}
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        {/* Expandable view block */}
        <AnimatePresence>
          {expanded && citation.text && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="text-[10px] text-zinc-400 bg-zinc-950/80 p-2.5 rounded border border-zinc-900/60 font-serif leading-relaxed mt-1 select-text max-h-40 overflow-y-auto">
                {citation.text}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}

function CitationsTab({ sources, memories }: CitationsTabProps) {
  return (
    <div className="space-y-6">
      {/* Dynamic memory extraction log */}
      {memories.length > 0 && (
        <div className="space-y-2.5">
          <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">
            Vectorized Memory Contexts
          </span>
          <div className="space-y-2">
            {memories.map((mem) => (
              <div
                key={mem.memory_id}
                className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs flex flex-col gap-1"
              >
                <div className="flex justify-between items-center text-[9px] text-emerald-400 font-bold uppercase tracking-wider">
                  <span>Long-term memory match</span>
                  {mem.score && <span>{(mem.score * 100).toFixed(0)}% Score</span>}
                </div>
                <p className="text-zinc-350 italic text-[11px] font-serif leading-relaxed select-text mt-0.5">
                  "{mem.content}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* RAG sources citation panel */}
      <div className="space-y-2.5">
        <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">
          Retrieval Sources ({sources.length})
        </span>
        {sources.length === 0 ? (
          <div className="text-center py-6 text-zinc-500 text-xs">
            No source documents retrieved.
          </div>
        ) : (
          <div className="space-y-3">
            {sources.map((citation, index) => (
              <CitationCard key={index} citation={citation} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── 3. Metrics Tab ───────────────────────────────────────────────────────────

interface MetricsTabProps {
  tokens: any;
  latency: Record<string, number>;
}

function MetricsTab({ tokens, latency }: MetricsTabProps) {
  const totLat = latency.total || latency.total_latency_ms || 0;
  const llmLat = latency.synthesis_llm || latency.llm || 0;
  const retLat = latency.retrieval || 0;
  const rerLat = latency.reranking || 0;

  return (
    <div className="space-y-6">
      {/* Token pricing counts */}
      <div className="space-y-2.5">
        <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">
          Token Observability
        </span>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-zinc-900/35 border border-zinc-850/40">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Prompt In</span>
            <div className="text-sm font-bold text-zinc-200 font-mono mt-0.5">
              {tokens?.prompt ?? 0}
            </div>
            <span className="text-[9px] text-zinc-650">Tokens</span>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/35 border border-zinc-850/40">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Completion Out</span>
            <div className="text-sm font-bold text-zinc-200 font-mono mt-0.5">
              {tokens?.completion ?? 0}
            </div>
            <span className="text-[9px] text-zinc-650">Tokens</span>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/35 border border-zinc-850/40">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Total Size</span>
            <div className="text-sm font-bold text-zinc-200 font-mono mt-0.5">
              {tokens?.total ?? 0}
            </div>
            <span className="text-[9px] text-zinc-650">Tokens</span>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/35 border border-zinc-850/40">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Estimated Cost</span>
            <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
              ${tokens?.cost !== undefined ? tokens.cost.toFixed(5) : "0.00000"}
            </div>
            <span className="text-[9px] text-zinc-650">USD Pricing</span>
          </div>
        </div>
      </div>

      {/* Latency meter progress splits */}
      <div className="space-y-2.5">
        <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">
          Latency Breakdown ({(totLat / 1000).toFixed(2)}s)
        </span>
        <div className="space-y-3.5 bg-zinc-900/20 border border-zinc-850/40 rounded-lg p-3.5">
          {/* Hybrid Retrieval progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between items-center text-[10px]">
              <span className="text-zinc-400">Hybrid Retrieval</span>
              <span className="font-mono text-zinc-400">{retLat.toFixed(0)}ms</span>
            </div>
            <div className="w-full bg-zinc-950 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-cyan-500 h-full rounded-full"
                style={{ width: `${totLat > 0 ? (retLat / totLat) * 100 : 0}%` }}
              />
            </div>
          </div>

          {/* Reranking progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between items-center text-[10px]">
              <span className="text-zinc-400">Cross-Reranking</span>
              <span className="font-mono text-zinc-400">{rerLat.toFixed(0)}ms</span>
            </div>
            <div className="w-full bg-zinc-950 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-indigo-500 h-full rounded-full"
                style={{ width: `${totLat > 0 ? (rerLat / totLat) * 100 : 0}%` }}
              />
            </div>
          </div>

          {/* Synthesis LLM progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between items-center text-[10px]">
              <span className="text-zinc-400">LLM Synthesis</span>
              <span className="font-mono text-zinc-400">{llmLat.toFixed(0)}ms</span>
            </div>
            <div className="w-full bg-zinc-950 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-violet-500 h-full rounded-full"
                style={{ width: `${totLat > 0 ? (llmLat / totLat) * 100 : 0}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
