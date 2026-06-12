"use client";

import React, { useState, useEffect, useRef } from "react";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import { Card, CardContent } from "@/components/ui/Card";
import {
  Compass,
  Database,
  Search,
  Layers,
  Cpu,
  CheckCircle2,
  FileText,
  Activity,
  ChevronDown,
  ChevronUp,
  Clock,
  Coins,
  ShieldAlert,
  Globe,
  History,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import QueryTraceTimeline from "./QueryTraceTimeline";
import SourceCards from "./SourceCards";

// Custom hook for active step timing tickers
function useStepTimer(isActive: boolean, finalValue?: number) {
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<any>(null);

  useEffect(() => {
    if (isActive) {
      setElapsed(0);
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setElapsed(Date.now() - start);
      }, 25);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isActive]);

  return finalValue !== undefined && finalValue > 0 ? finalValue : elapsed;
}

export default function ObservabilityPanel() {
  const {
    currentDecision,
    currentLatency,
    currentSources,
    currentMemories,
    currentTokens,
    isGenerating,
    isStreaming,
    error,
    messages,
    currentTrace,
  } = useChatStore();

  const { health } = useSettingsStore();
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(true);

  // Check if live query trace data is available
  const isLive = !!(
    currentDecision ||
    currentSources.length > 0 ||
    Object.keys(currentLatency).length > 0 ||
    isGenerating ||
    error
  );

  // Fallback to high-fidelity mock data if no query trace is active
  const decision = isLive ? currentDecision : { selected_agent: "RAG Agent", query_intent: "technical_question" };
  const latency = isLive ? currentLatency : {
    router: 18,
    memory: 35,
    vector_search: 82,
    bm25_search: 29,
    reranking: 67,
    synthesis_llm: 1800,
    total: 2031
  };
  const sources = isLive ? currentSources : [
    {
      name: "Resume.pdf",
      page: 3,
      chunk_id: "chk_092a",
      confidence: 0.94,
      text: "Developed an enterprise-grade multi-agent orchestrator with real-time vector search integration, achieving sub-100ms index lookup latency.",
      score: 0.94
    },
    {
      name: "Architecture_Spec.md",
      page: 1,
      chunk_id: "chk_771b",
      confidence: 0.88,
      text: "The platform routes user queries dynamically through a semantic memory agent and BM25 search index before applying cross-encoders.",
      score: 0.88
    }
  ];
  const memories = isLive ? currentMemories : [
    { key: "candidate_experience", value: "Senior Frontend Engineer" }
  ];
  const tokens = isLive ? currentTokens : {
    prompt: 342,
    completion: 894,
    total: 1236,
    cost: 0.00037
  };
  const trace = isLive ? currentTrace : ["router", "memory", "hybrid_search", "reranker", "llm"];
  const generating = isLive ? isGenerating : false;
  const streaming = isLive ? isStreaming : false;
  const traceError = isLive ? error : null;

  const activeProvider = health?.llm_provider?.toLowerCase() || "ollama";

  // Latency helper variables
  const totLat = latency.total || latency.total_latency_ms || 0;
  const routerLat = latency.router || (decision ? 18 : 0);
  const memoryLat = latency.memory || (memories.length > 0 ? 35 : 0);
  const vectorLat = latency.vector_search || 0;
  const bm25Lat = latency.bm25_search || 0;
  const rerankLat = latency.reranking || 0;
  const synthesisLat = latency.synthesis_llm || latency.llm || 0;

  const steps = [
    { key: "router", label: "Router Agent", icon: Compass, val: routerLat },
    { key: "memory", label: "Memory Retrieval", icon: Database, val: memoryLat },
    { key: "vector", label: "Semantic Search", icon: Search, val: vectorLat },
    { key: "bm25", label: "BM25 Search", icon: Search, val: bm25Lat },
    { key: "reranking", label: "Cross Reranker", icon: Layers, val: rerankLat },
    {
      key: "synthesis",
      label: `${activeProvider.charAt(0).toUpperCase() + activeProvider.slice(1)} Generation`,
      icon: Cpu,
      val: synthesisLat,
    },
    { key: "response", label: "Response Completed", icon: CheckCircle2, val: 0 },
  ];

  const getStepStatus = (key: string) => {
    if (generating && !decision) {
      if (key === "router") return "active";
      return "pending";
    }

    const matched = getMatchedVal(key);
    if (matched > 0) return "done";

    if (generating || streaming) {
      if (key === "response") return "pending";
      if (key === "synthesis" && (latency.retrieval || latency.vector_search)) return "active";
      if (key === "reranking" && latency.vector_search && !latency.reranking) return "active";
      if ((key === "vector" || key === "bm25") && decision && !latency.vector_search) return "active";
      if (key === "memory" && decision && !latency.vector_search) return "active";
    }

    if (decision || Object.keys(latency).length > 0) {
      return "done";
    }

    return "pending";
  };

  const getMatchedVal = (key: string): number => {
    switch (key) {
      case "router":
        return routerLat;
      case "memory":
        return memoryLat;
      case "vector":
        return vectorLat;
      case "bm25":
        return bm25Lat;
      case "reranking":
        return rerankLat;
      case "synthesis":
        return synthesisLat;
      default:
        return 0;
    }
  };

  const formatLatencyValue = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <aside className="w-96 bg-zinc-950/60 border-l border-zinc-900/60 flex flex-col h-full overflow-hidden select-none backdrop-blur-md z-30 shrink-0 shadow-2xl">
      {/* Observability Center Header */}
      <div className="p-4 border-b border-zinc-900/60 flex items-center justify-between bg-zinc-950/20 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-primary" />
          Observability Center
        </span>

        <span className="flex items-center gap-1.5">
          <span
            className={cn("w-1.5 h-1.5 rounded-full shrink-0", {
              "bg-amber-400 animate-pulse shadow-[0_0_8px_rgba(251,191,36,0.5)]": generating,
              "bg-violet-400 animate-pulse shadow-[0_0_8px_rgba(139,92,246,0.5)]": streaming,
              "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]": traceError && !generating,
              "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]": !generating && !streaming && !traceError,
            })}
          />
          <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">
            {generating ? "Tracing" : streaming ? "Streaming" : traceError ? "Failed" : "Resolved"}
          </span>
        </span>
      </div>

      {/* Stacked Observability Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-8 custom-scrollbar">
        {/* SECTION 1: Agent Workflow */}
        <div className="space-y-4">
          <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-400 flex items-center gap-1.5 border-b border-zinc-900/60 pb-2">
            <Workflow className="w-3.5 h-3.5 text-primary" />
            <span>Agent Workflow</span>
            {!isLive && (
              <span className="text-[8px] bg-zinc-800 text-zinc-500 px-1.5 py-0.5 rounded font-mono font-normal tracking-normal uppercase ml-auto">
                Demo Mode
              </span>
            )}
          </div>
          
          <div className="space-y-3 px-1">
            {steps.map((step) => {
              const status = getStepStatus(step.key);
              const finalVal = getMatchedVal(step.key);
              const timerVal = useStepTimer(status === "active", finalVal);
              const StepIcon = step.icon;

              const isPending = status === "pending";
              const isActive = status === "active";
              const isDone = status === "done";

              return (
                <div
                  key={step.key}
                  className={cn(
                    "flex items-center justify-between text-xs select-none transition-all duration-200",
                    isActive ? "text-primary font-bold" : isDone ? "text-zinc-300" : "text-zinc-650"
                  )}
                >
                  <div className="flex items-center gap-2 max-w-[65%]">
                    <StepIcon
                      className={cn("w-3.5 h-3.5 shrink-0", {
                        "text-zinc-700": isPending,
                        "text-primary animate-pulse": isActive,
                        "text-emerald-400": isDone && step.key === "response",
                        "text-zinc-500": isDone && step.key !== "response",
                      })}
                    />
                    <span className="truncate">{step.label}</span>
                  </div>

                  <div className="flex-1 border-b border-dotted border-zinc-800/80 mx-2 self-end mb-1" />

                  <div className="shrink-0 font-mono text-[10px]">
                    {isActive ? (
                      <span className="animate-pulse">{formatLatencyValue(timerVal)}</span>
                    ) : isDone && step.key !== "response" ? (
                      <span>{formatLatencyValue(finalVal)}</span>
                    ) : isDone && step.key === "response" ? (
                      <span className="text-emerald-400 font-bold uppercase tracking-wider text-[8px] bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-md">
                        Success
                      </span>
                    ) : (
                      <span className="text-zinc-800">--</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* SECTION 2: Query Timeline */}
        <div className="space-y-4">
          <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-400 flex items-center gap-1.5 border-b border-zinc-900/60 pb-2">
            <Clock className="w-3.5 h-3.5 text-primary" />
            <span>Query Timeline</span>
          </div>
          
          <div className="bg-zinc-950/20 border border-zinc-900/40 rounded-xl p-3.5">
            <QueryTraceTimeline
              decision={decision}
              latency={latency}
              tokens={tokens}
              sourcesCount={sources.length}
              memoriesCount={memories.length}
              isGenerating={generating}
              isStreaming={streaming}
              messages={messages}
              error={traceError}
              routingTrace={trace}
            />
          </div>
        </div>

        {/* SECTION 3: Source Cards */}
        <div className="space-y-4">
          <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-400 flex items-center gap-1.5 border-b border-zinc-900/60 pb-2">
            <FileText className="w-3.5 h-3.5 text-primary" />
            <span>Source Cards</span>
            {sources.length > 0 && (
              <span className="text-[9px] bg-zinc-900 text-zinc-400 px-1.5 py-0.5 rounded-full border border-zinc-800 font-bold ml-auto animate-fade-in">
                {sources.length}
              </span>
            )}
          </div>
          
          <div className="space-y-3">
            {sources.length === 0 ? (
              <div className="flex flex-col items-center justify-center text-center py-8 text-zinc-650 bg-zinc-950/10 border border-zinc-900/30 rounded-xl">
                <FileText className="w-6 h-6 mb-1.5 text-zinc-800 animate-pulse" />
                <span className="text-xs font-semibold">No citations referenced</span>
                <p className="text-[10px] text-zinc-700 mt-1 max-w-[80%] leading-relaxed">
                  Source documentation cards appear once vector or search queries complete.
                </p>
              </div>
            ) : (
              <SourceCards sources={sources} />
            )}
          </div>
        </div>

        {/* SECTION 4: Latency Metrics */}
        <div className="space-y-4">
          <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-400 flex items-center gap-1.5 border-b border-zinc-900/60 pb-2">
            <Activity className="w-3.5 h-3.5 text-primary" />
            <span>Latency Metrics</span>
          </div>
          
          <div className="space-y-4">
            {/* Total Latency Split Meter */}
            <div className="p-3.5 rounded-xl border border-zinc-900 bg-zinc-950/40 space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-zinc-400">Pipeline Latency</span>
                <span className="font-mono font-bold text-zinc-150 text-xs">
                  {generating ? (
                    <span className="animate-pulse text-primary font-bold">Measuring...</span>
                  ) : (
                    formatLatencyValue(totLat || synthesisLat + routerLat + memoryLat + vectorLat + bm25Lat + rerankLat)
                  )}
                </span>
              </div>

              {!generating && totLat > 0 && (
                <div className="w-full bg-zinc-900 h-2 rounded-full overflow-hidden flex shadow-inner">
                  <div
                    className="bg-blue-500 h-full hover:opacity-80 transition-opacity"
                    style={{ width: `${(routerLat / totLat) * 100}%` }}
                    title={`Router: ${routerLat.toFixed(0)}ms`}
                  />
                  <div
                    className="bg-emerald-500 h-full hover:opacity-80 transition-opacity"
                    style={{ width: `${(memoryLat / totLat) * 100}%` }}
                    title={`Memory: ${memoryLat.toFixed(0)}ms`}
                  />
                  <div
                    className="bg-cyan-500 h-full hover:opacity-80 transition-opacity"
                    style={{ width: `${(vectorLat / totLat) * 100}%` }}
                    title={`Semantic Search: ${vectorLat.toFixed(0)}ms`}
                  />
                  <div
                    className="bg-amber-500 h-full hover:opacity-80 transition-opacity"
                    style={{ width: `${(bm25Lat / totLat) * 100}%` }}
                    title={`BM25 Search: ${bm25Lat.toFixed(0)}ms`}
                  />
                  <div
                    className="bg-indigo-500 h-full hover:opacity-80 transition-opacity"
                    style={{ width: `${(rerankLat / totLat) * 100}%` }}
                    title={`Reranking: ${rerankLat.toFixed(0)}ms`}
                  />
                  <div
                    className="bg-violet-500 h-full hover:opacity-80 transition-opacity"
                    style={{ width: `${(synthesisLat / totLat) * 100}%` }}
                    title={`LLM Synthesis: ${synthesisLat.toFixed(0)}ms`}
                  />
                </div>
              )}

              {/* Legend Grid */}
              {!generating && totLat > 0 && (
                <div className="grid grid-cols-3 gap-x-2 gap-y-1.5 pt-1 text-[8px] font-mono text-zinc-500 uppercase tracking-tight">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    <span>Router</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span>Memory</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                    <span>Semantic</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                    <span>BM25</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                    <span>Rerank</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />
                    <span>LLM</span>
                  </div>
                </div>
              )}
            </div>

            {/* Diagnostics details dropdown */}
            <div className="border border-zinc-900 rounded-xl bg-zinc-950/20">
              <button
                onClick={() => setIsDiagnosticsOpen(!isDiagnosticsOpen)}
                className="w-full flex items-center justify-between text-[9px] font-bold text-zinc-500 hover:text-zinc-400 uppercase tracking-widest px-3.5 py-2.5 transition-colors border-b border-zinc-900/50"
              >
                <span>Diagnostics Table</span>
                {isDiagnosticsOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              <AnimatePresence>
                {isDiagnosticsOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="p-3.5 text-[9px] space-y-2.5 text-zinc-500 font-mono select-text">
                      <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                        <span>LLM Model Provider</span>
                        <span className="text-zinc-350 font-bold uppercase">{activeProvider}</span>
                      </div>
                      {health?.llm_model && (
                        <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                          <span>Model Identity</span>
                          <span className="text-zinc-350 font-bold truncate max-w-[120px]" title={health.llm_model}>
                            {health.llm_model.split("/").pop()}
                          </span>
                        </div>
                      )}
                      {health?.vector_store && (
                        <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                          <span>Vector Database</span>
                          <span className="text-zinc-350 font-bold uppercase">{health.vector_store}</span>
                        </div>
                      )}
                      <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                        <span>Retrieved Memories</span>
                        <span className="text-zinc-350 font-bold">{memories.length} facts</span>
                      </div>
                      <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                        <span>Cited References</span>
                        <span className="text-zinc-350 font-bold">{sources.length} sources</span>
                      </div>
                      <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                        <span>Total Token Size</span>
                        <span className="text-zinc-350 font-bold flex items-center gap-1">
                          <Coins className="w-2.5 h-2.5 text-zinc-700" />
                          {tokens?.total ?? 0} tokens
                        </span>
                      </div>
                      <div className="flex justify-between items-center pb-0.5">
                        <span>Est API Fee</span>
                        <span className="text-emerald-500 font-bold">
                          ${tokens?.cost ? tokens.cost.toFixed(5) : "0.00000"}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
