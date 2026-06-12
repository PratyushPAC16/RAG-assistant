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

type TabType = "trace" | "timeline" | "citations" | "metrics";

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
  const [activeTab, setActiveTab] = useState<TabType>("trace");
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(true);

  // Auto-switch tabs to timeline when query starts generating
  useEffect(() => {
    if (isGenerating) {
      setActiveTab("timeline");
    }
  }, [isGenerating]);

  const activeProvider = health?.llm_provider?.toLowerCase() || "ollama";
  const hasData =
    currentDecision ||
    currentSources.length > 0 ||
    Object.keys(currentLatency).length > 0 ||
    isGenerating ||
    error;

  if (!hasData) {
    return (
      <aside className="w-80 bg-zinc-950/60 border-l border-zinc-900/60 p-6 flex flex-col justify-center items-center text-center select-none backdrop-blur-md h-full relative">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-44 h-44 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <Activity className="w-7 h-7 text-zinc-700 mb-3 animate-pulse" />
        <span className="text-xs font-bold uppercase tracking-widest text-zinc-400">Observability Panel</span>
        <p className="text-zinc-650 text-xs mt-2 max-w-[85%] leading-relaxed">
          Reasoning traces, chronological query timelines, citations context, and infrastructure metrics will load here once a query starts.
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
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const tabs: { id: TabType; label: string; icon: any; badge?: number }[] = [
    { id: "trace", label: "Trace", icon: Workflow },
    { id: "timeline", label: "Timeline", icon: Clock },
    { id: "citations", label: "Citations", icon: FileText, badge: currentSources.length },
    { id: "metrics", label: "Metrics", icon: Activity },
  ];

  return (
    <aside className="w-80 bg-zinc-950/60 border-l border-zinc-900/60 flex flex-col h-full overflow-hidden select-none backdrop-blur-md z-30 shrink-0 shadow-2xl">
      {/* Trace Status Header */}
      <div className="p-4 border-b border-zinc-900/60 flex items-center justify-between bg-zinc-950/20 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-primary" />
          Observability Center
        </span>

        <span className="flex items-center gap-1.5">
          <span
            className={cn("w-1.5 h-1.5 rounded-full shrink-0", {
              "bg-amber-400 animate-pulse shadow-[0_0_8px_rgba(251,191,36,0.5)]": isGenerating,
              "bg-violet-400 animate-pulse shadow-[0_0_8px_rgba(139,92,246,0.5)]": isStreaming,
              "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]": error && !isGenerating,
              "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]": !isGenerating && !isStreaming && !error,
            })}
          />
          <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">
            {isGenerating ? "Tracing" : isStreaming ? "Streaming" : error ? "Failed" : "Resolved"}
          </span>
        </span>
      </div>

      {/* Tabs Switcher Navigation */}
      <div className="flex border-b border-zinc-900 px-2 pt-1.5 bg-zinc-950/10 shrink-0">
        {tabs.map((tab) => {
          const TabIcon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "relative flex-1 py-2 px-1 text-[10px] font-bold uppercase tracking-wider flex flex-col items-center gap-1 transition-colors outline-none",
                isActive ? "text-zinc-150" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              <div className="flex items-center gap-1">
                <TabIcon className="w-3.5 h-3.5 shrink-0" />
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className="text-[9px] bg-zinc-900 text-zinc-400 px-1 rounded-full border border-zinc-800 shrink-0">
                    {tab.badge}
                  </span>
                )}
              </div>
              <span>{tab.label}</span>

              {isActive && (
                <motion.div
                  layoutId="observabilityActiveTab"
                  className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Panel Scrollable Content Body */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            className="h-full"
          >
            {/* TAB 1: Trace Steps List */}
            {activeTab === "trace" && (
              <div className="space-y-4 pt-1">
                <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-3 select-none flex items-center gap-1.5">
                  <Workflow className="w-3.5 h-3.5 text-zinc-500" />
                  Live Workflow Nodes
                </div>
                <div className="space-y-4">
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
                          isActive ? "text-primary font-bold" : isDone ? "text-zinc-350" : "text-zinc-650"
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
                            <span className="text-emerald-400 font-bold uppercase tracking-wider text-[9px] bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-md">
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
            )}

            {/* TAB 2: Dynamic Timeline View */}
            {activeTab === "timeline" && (
              <QueryTraceTimeline
                decision={currentDecision}
                latency={currentLatency}
                tokens={currentTokens}
                sourcesCount={currentSources.length}
                memoriesCount={currentMemories.length}
                isGenerating={isGenerating}
                isStreaming={isStreaming}
                messages={messages}
                error={error}
                routingTrace={currentTrace}
              />
            )}

            {/* TAB 3: Expandable Citations */}
            {activeTab === "citations" && (
              <div className="pt-1">
                {currentSources.length === 0 ? (
                  <div className="flex flex-col items-center justify-center text-center py-12 text-zinc-600">
                    <FileText className="w-8 h-8 mb-2 text-zinc-700" />
                    <span className="text-xs font-semibold">No citations referenced</span>
                    <p className="text-[10px] text-zinc-700 mt-1 max-w-[80%] leading-relaxed">
                      Source documentation cards appear once vector or search queries complete.
                    </p>
                  </div>
                ) : (
                  <SourceCards sources={currentSources} />
                )}
              </div>
            )}

            {/* TAB 4: Telemetry Metrics */}
            {activeTab === "metrics" && (
              <div className="space-y-4 pt-1">
                <div className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 select-none flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-zinc-500" />
                  Performance Diagnostics
                </div>

                {/* Total Latency Split Meter */}
                <div className="p-3.5 rounded-xl border border-zinc-900 bg-zinc-950/40 space-y-3">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-zinc-400">Pipeline Latency</span>
                    <span className="font-mono font-bold text-zinc-150 text-xs">
                      {isGenerating ? (
                        <span className="animate-pulse">Measuring...</span>
                      ) : (
                        formatLatencyValue(totLat || synthesisLat + routerLat + memoryLat + vectorLat + bm25Lat + rerankLat)
                      )}
                    </span>
                  </div>

                  {!isGenerating && totLat > 0 && (
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
                  {!isGenerating && totLat > 0 && (
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
                            <span className="text-zinc-350 font-bold">{currentMemories.length} facts</span>
                          </div>
                          <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                            <span>Cited References</span>
                            <span className="text-zinc-350 font-bold">{currentSources.length} sources</span>
                          </div>
                          <div className="flex justify-between items-center border-b border-zinc-900/40 pb-1.5">
                            <span>Total Token Size</span>
                            <span className="text-zinc-350 font-bold flex items-center gap-1">
                              <Coins className="w-2.5 h-2.5 text-zinc-700" />
                              {currentTokens?.total ?? 0} tokens
                            </span>
                          </div>
                          <div className="flex justify-between items-center pb-0.5">
                            <span>Est API Fee</span>
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
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </aside>
  );
}
