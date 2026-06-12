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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

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
  } = useChatStore();

  const { health } = useSettingsStore();
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(false);

  const activeProvider = health?.llm_provider?.toLowerCase() || "ollama";
  const hasData = currentDecision || currentSources.length > 0 || Object.keys(currentLatency).length > 0;

  if (!hasData && !isGenerating) {
    return (
      <aside className="w-80 bg-zinc-950/60 border-l border-zinc-900/60 p-6 flex flex-col justify-center items-center text-center select-none backdrop-blur-md h-full relative">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-44 h-44 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <Activity className="w-7 h-7 text-zinc-700 mb-3 animate-pulse" />
        <span className="text-xs font-bold uppercase tracking-widest text-zinc-400">Reasoning Trace</span>
        <p className="text-zinc-650 text-xs mt-2 max-w-[85%] leading-relaxed">
          Reasoning traces, step timings, and resource diagnostics will render here when a query is active.
        </p>
      </aside>
    );
  }

  // Latency helper variables
  const totLat = currentLatency.total || currentLatency.total_latency_ms || 0;
  const routerLat = currentLatency.router || (currentDecision ? 65 : 0);
  const memoryLat = currentLatency.memory || (currentMemories.length > 0 ? 90 : 0);
  const vectorLat = currentLatency.vector_search || 0;
  const bm25Lat = currentLatency.bm25_search || 0;
  const rerankLat = currentLatency.reranking || 0;
  const synthesisLat = currentLatency.synthesis_llm || currentLatency.llm || 0;

  const steps = [
    { key: "router", label: "Router Agent", icon: Compass, val: routerLat },
    { key: "memory", label: "Memory Retrieval", icon: FileText, val: memoryLat },
    { key: "vector", label: "Semantic Search", icon: Search, val: vectorLat },
    { key: "bm25", label: "BM25 Search", icon: Search, val: bm25Lat },
    { key: "reranking", label: "Cross Reranker", icon: Layers, val: rerankLat },
    {
      key: "synthesis",
      label: `${activeProvider.charAt(0).toUpperCase() + activeProvider.slice(1)} Generation`,
      icon: Cpu,
      val: synthesisLat,
    },
    { key: "response", label: "Response Generation", icon: CheckCircle2, val: 0 },
  ];

  const getStepStatus = (key: string) => {
    if (isGenerating && !currentDecision) {
      if (key === "router") return "active";
      return "pending";
    }

    const matched = getMatchedVal(key);
    if (matched > 0) return "done";

    if (isGenerating || isStreaming) {
      if (key === "response") return "pending";
      if (key === "synthesis" && (currentLatency.retrieval || currentLatency.vector_search)) return "active";
      if (key === "reranking" && currentLatency.vector_search && !currentLatency.reranking) return "active";
      if ((key === "vector" || key === "bm25") && currentDecision && !currentLatency.vector_search) return "active";
      if (key === "memory" && currentDecision && !currentLatency.vector_search) return "active";
    }

    if (currentDecision || Object.keys(currentLatency).length > 0) {
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
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <aside className="w-80 bg-zinc-950/60 border-l border-zinc-900/60 flex flex-col h-full overflow-hidden select-none backdrop-blur-md">
      {/* Trace Status Header */}
      <div className="p-4 border-b border-zinc-900/60 flex items-center justify-between bg-zinc-950/20">
        <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-primary" />
          Reasoning Trace
        </span>
        
        <span className="flex items-center gap-1.5">
          <span
            className={cn("w-1.5 h-1.5 rounded-full shrink-0", {
              "bg-amber-400 animate-ping": isGenerating,
              "bg-violet-400 animate-ping": isStreaming,
              "bg-emerald-500": !isGenerating && !isStreaming,
            })}
          />
          <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">
            {isGenerating ? "Tracing" : isStreaming ? "Streaming" : "Resolved"}
          </span>
        </span>
      </div>

      {/* Dotted Steps List */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
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
                isActive ? "text-primary font-semibold" : isDone ? "text-zinc-350" : "text-zinc-600"
              )}
            >
              <div className="flex items-center gap-2 max-w-[65%]">
                <StepIcon
                  className={cn("w-3.5 h-3.5 shrink-0", {
                    "text-zinc-650": isPending,
                    "text-primary animate-pulse": isActive,
                    "text-emerald-400": isDone && step.key === "response",
                    "text-zinc-500": isDone && step.key !== "response",
                  })}
                />
                <span className="truncate">{step.label}</span>
              </div>

              {/* Dotted separator */}
              <div className="flex-1 border-b border-dotted border-zinc-800/80 mx-2 self-end mb-1" />

              {/* Timing value */}
              <div className="shrink-0 font-mono text-[10px]">
                {isActive ? (
                  <span className="animate-pulse">{formatLatencyValue(timerVal)}</span>
                ) : isDone && step.key !== "response" ? (
                  <span>{formatLatencyValue(finalVal)}</span>
                ) : isDone && step.key === "response" ? (
                  <span className="text-emerald-400 font-bold uppercase tracking-wider text-[9px]">Ok</span>
                ) : (
                  <span className="text-zinc-700">--</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Total Pipeline latency card */}
      <div className="p-4 border-t border-zinc-900/60 bg-zinc-950/20 shrink-0 space-y-3">
        <div className="flex justify-between items-center text-xs">
          <span className="font-semibold text-zinc-400">Total Pipeline Latency</span>
          <span className="font-mono font-bold text-zinc-100 text-sm">
            {isGenerating ? (
              <span className="animate-pulse">Measuring...</span>
            ) : (
              formatLatencyValue(totLat || synthesisLat + routerLat + memoryLat + vectorLat + bm25Lat + rerankLat)
            )}
          </span>
        </div>

        {/* Latency split segments bar */}
        {!isGenerating && totLat > 0 && (
          <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden flex">
            {/* Router */}
            <div
              className="bg-blue-500 h-full hover:opacity-85 transition-opacity"
              style={{ width: `${(routerLat / totLat) * 100}%` }}
              title={`Router: ${routerLat.toFixed(0)}ms`}
            />
            {/* Memory */}
            <div
              className="bg-emerald-500 h-full hover:opacity-85 transition-opacity"
              style={{ width: `${(memoryLat / totLat) * 100}%` }}
              title={`Memory: ${memoryLat.toFixed(0)}ms`}
            />
            {/* Semantic/Vector */}
            <div
              className="bg-cyan-500 h-full hover:opacity-85 transition-opacity"
              style={{ width: `${(vectorLat / totLat) * 100}%` }}
              title={`Semantic Search: ${vectorLat.toFixed(0)}ms`}
            />
            {/* BM25 */}
            <div
              className="bg-amber-500 h-full hover:opacity-85 transition-opacity"
              style={{ width: `${(bm25Lat / totLat) * 100}%` }}
              title={`BM25 Search: ${bm25Lat.toFixed(0)}ms`}
            />
            {/* Reranker */}
            <div
              className="bg-indigo-500 h-full hover:opacity-85 transition-opacity"
              style={{ width: `${(rerankLat / totLat) * 100}%` }}
              title={`Reranking: ${rerankLat.toFixed(0)}ms`}
            />
            {/* Synthesis */}
            <div
              className="bg-violet-500 h-full hover:opacity-85 transition-opacity"
              style={{ width: `${(synthesisLat / totLat) * 100}%` }}
              title={`LLM Synthesis: ${synthesisLat.toFixed(0)}ms`}
            />
          </div>
        )}

        {/* Diagnostics Drawer drop */}
        <div className="pt-1 border-t border-zinc-900/40">
          <button
            onClick={() => setIsDiagnosticsOpen(!isDiagnosticsOpen)}
            className="w-full flex items-center justify-between text-[10px] font-bold text-zinc-500 hover:text-zinc-300 uppercase tracking-wider py-1.5 transition-colors"
          >
            <span>Diagnostic Details</span>
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
                <div className="pt-2 pb-1 text-[10px] space-y-2.5 text-zinc-500 font-mono">
                  {/* Sources used count */}
                  <div className="flex justify-between items-center border-b border-zinc-900 pb-1.5">
                    <span>Cited Sources</span>
                    <span className="text-zinc-350 font-bold">{currentSources.length} files</span>
                  </div>

                  {/* Token pricing */}
                  <div className="flex justify-between items-center border-b border-zinc-900 pb-1.5">
                    <span>Token Size</span>
                    <span className="text-zinc-350 font-bold">{currentTokens?.total ?? 0} tok</span>
                  </div>

                  {/* Pricing estimation */}
                  <div className="flex justify-between items-center pb-0.5">
                    <span>API Cost (Est)</span>
                    <span className="text-emerald-500 font-bold">
                      ${currentTokens?.cost ? currentTokens.cost.toFixed(5) : "0.00000"}
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </aside>
  );
}
