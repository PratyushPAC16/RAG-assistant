"use client";

import React, { useState } from "react";
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
} from "lucide-react";
import { cn } from "@/lib/utils";

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
      <aside className="w-80 bg-zinc-950/40 border-l border-zinc-800/40 p-6 flex flex-col justify-center items-center text-center select-none backdrop-blur-sm h-full">
        <Activity className="w-8 h-8 text-zinc-600 mb-3 animate-pulse" />
        <span className="text-sm font-semibold text-zinc-400">Observability Panel</span>
        <p className="text-zinc-600 text-xs mt-1.5 max-w-[80%] leading-relaxed">
          Submit a query in the chat window to stream active node paths, document sources, and token pricing telemetry.
        </p>
      </aside>
    );
  }

  return (
    <aside className="w-80 bg-zinc-950/40 border-l border-zinc-800/40 flex flex-col h-full overflow-hidden select-none backdrop-blur-sm">
      {/* Header Tabs */}
      <div className="flex border-b border-zinc-800/40 bg-zinc-950/50 p-2 shrink-0">
        {(["workflow", "citations", "metrics"] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "flex-1 text-center py-1.5 rounded-md text-[11px] font-semibold uppercase tracking-wider transition-all duration-200",
              activeTab === tab
                ? "bg-zinc-800 text-zinc-100 shadow"
                : "text-zinc-500 hover:text-zinc-300"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4">
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

function WorkflowTab({ decision, trace, latency, isGenerating, isStreaming }: WorkflowTabProps) {
  // Define standard steps in the multi-agent execution pipeline
  const steps = [
    { key: "router", label: "Router Agent", icon: Compass, color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    { key: "memory", label: "Memory Agent", icon: FileText, color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    { key: "vector", label: "Semantic Retriever", icon: Search, color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20" },
    { key: "bm25", label: "BM25 Keyword Search", icon: Search, color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
    { key: "reranker", label: "Cross-Encoder Reranker", icon: Layers, color: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20" },
    { key: "synthesis", label: "LLM Provider Response", icon: Cpu, color: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
    { key: "response", label: "Response Generated", icon: CheckCircle2, color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20" },
  ];

  // Helper to determine status: 'done', 'active', 'pending'
  const getStepStatus = (key: string) => {
    if (isGenerating && !decision) {
      if (key === "router") return "active";
      return "pending";
    }

    const matched = getMatchedStepLatency(key);
    if (matched !== undefined && matched > 0) return "done";
    
    // Active states fallback mapping
    if (isGenerating || isStreaming) {
      if (key === "response") return "pending";
      if (key === "synthesis" && latency.retrieval) return "active";
      if ((key === "vector" || key === "bm25" || key === "reranker") && decision && !latency.retrieval) return "active";
      if (key === "memory" && decision && !latency.retrieval && !latency.vector_search) return "active";
    }

    if (decision || Object.keys(latency).length > 0) {
      if (key === "response" && !isStreaming) return "done";
      if (key !== "response" && matched !== undefined) return "done";
      return "done"; // All completed on successful resolve
    }

    return "pending";
  };

  const getMatchedStepLatency = (key: string): number | undefined => {
    switch (key) {
      case "router":
        return latency.router || (decision ? 50 : undefined);
      case "memory":
        return latency.memory || (latency.retrieved_memories ? 100 : undefined);
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
      {/* Active Routing decision panel */}
      {decision && (
        <Card className="bg-zinc-900/40 border-zinc-800/40 p-4 relative overflow-hidden">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Router Route</span>
            <ArrowRight className="w-3.5 h-3.5 text-zinc-600" />
            <span className="text-xs font-semibold text-primary uppercase">
              {decision.agent} agent
            </span>
          </div>
          <p className="text-[11px] text-zinc-400 mt-2 font-medium leading-relaxed">
            "{decision.reasoning}"
          </p>
          <div className="mt-3 flex items-center justify-between text-[10px] text-zinc-500">
            <span>Confidence: {(decision.confidence * 100).toFixed(0)}%</span>
            <span>Docs indexed: {decision.num_docs_available}</span>
          </div>
        </Card>
      )}

      {/* Workflow checklist timeline */}
      <div className="relative pl-6 space-y-5 border-l border-zinc-800/60 ml-3 py-1">
        {steps.map((step, idx) => {
          const status = getStepStatus(step.key);
          const val = getMatchedStepLatency(step.key);
          const StepIcon = step.icon;

          return (
            <div key={idx} className="relative group">
              {/* Dot icon indicator */}
              <div
                className={cn(
                  "absolute -left-[33px] top-0.5 w-4.5 h-4.5 rounded-full border flex items-center justify-center transition-all duration-300",
                  status === "done"
                    ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                    : status === "active"
                    ? "bg-primary/20 border-primary text-primary animate-pulse scale-105"
                    : "bg-zinc-950 border-zinc-800 text-zinc-600"
                )}
              >
                <StepIcon className="w-2.5 h-2.5" />
              </div>

              {/* Step info details */}
              <div className="flex justify-between items-center text-xs">
                <span
                  className={cn(
                    "font-medium transition-colors duration-200",
                    status === "done"
                      ? "text-zinc-300"
                      : status === "active"
                      ? "text-primary font-semibold"
                      : "text-zinc-500"
                  )}
                >
                  {step.label}
                </span>

                {status === "done" && val !== undefined && val > 0 && (
                  <span className="font-mono text-[10px] text-zinc-500">
                    {val.toFixed(0)}ms
                  </span>
                )}
                {status === "active" && (
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                    <span className="text-[10px] text-primary font-medium tracking-tight animate-pulse">Running</span>
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

  return (
    <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/30 flex flex-col gap-2 hover:border-primary/20 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          <span className="text-xs font-semibold text-zinc-200 truncate" title={citation.document}>
            {citation.document}
          </span>
        </div>
        
        {citation.relevance_score !== undefined && (
          <span className="text-[10px] font-bold text-emerald-400 shrink-0">
            {(citation.relevance_score * 100).toFixed(0)}% Match
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-[10px] text-zinc-500 font-medium">
        <span>Page: {citation.page || "TXT"}</span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-0.5 hover:text-zinc-300 transition-colors text-primary"
        >
          {expanded ? (
            <>
              Hide chunk <ChevronUp className="w-3 h-3" />
            </>
          ) : (
            <>
              Preview chunk <ChevronDown className="w-3 h-3" />
            </>
          )}
        </button>
      </div>

      {expanded && citation.text && (
        <div className="text-[11px] text-zinc-400 bg-zinc-950 p-2.5 rounded border border-zinc-800/50 mt-1 leading-relaxed max-h-40 overflow-y-auto select-text font-serif">
          {citation.text}
        </div>
      )}
    </div>
  );
}

function CitationsTab({ sources, memories }: CitationsTabProps) {
  return (
    <div className="space-y-6">
      {/* Memories Citation list */}
      {memories.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
            Retrieved Memory Contexts
          </h4>
          <div className="space-y-2">
            {memories.map((mem) => (
              <div
                key={mem.memory_id}
                className="p-3 rounded-lg bg-emerald-950/10 border border-emerald-500/20 text-xs flex flex-col gap-1.5"
              >
                <div className="flex justify-between items-center text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">
                  <span>Long-term memory fact</span>
                  {mem.score && <span>Score: {(mem.score * 100).toFixed(0)}%</span>}
                </div>
                <p className="text-zinc-300 italic text-[11px] font-serif leading-relaxed">
                  "{mem.content}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* RAG Documents Citation list */}
      <div className="space-y-3">
        <h4 className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
          Document Citations ({sources.length})
        </h4>
        {sources.length === 0 ? (
          <div className="text-center py-6 text-zinc-500 text-xs">
            No source documents retrieved for this agent context.
          </div>
        ) : (
          <div className="space-y-3.5">
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
      {/* LLM Observability details */}
      <div className="space-y-3">
        <h4 className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
          Token Observability
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/30">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Prompt Input</span>
            <div className="text-md font-bold text-zinc-200 font-mono mt-0.5">
              {tokens?.prompt ?? 0}
            </div>
            <span className="text-[9px] text-zinc-500">Tokens</span>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/30">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Completion Output</span>
            <div className="text-md font-bold text-zinc-200 font-mono mt-0.5">
              {tokens?.completion ?? 0}
            </div>
            <span className="text-[9px] text-zinc-500">Tokens</span>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/30">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Total Size</span>
            <div className="text-md font-bold text-zinc-200 font-mono mt-0.5">
              {tokens?.total ?? 0}
            </div>
            <span className="text-[9px] text-zinc-500">Tokens</span>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/30">
            <span className="text-[9px] text-zinc-500 font-semibold uppercase">Estimated Cost</span>
            <div className="text-md font-bold text-emerald-400 font-mono mt-0.5">
              ${tokens?.cost !== undefined ? tokens.cost.toFixed(5) : "0.00000"}
            </div>
            <span className="text-[9px] text-zinc-500">USD pricing</span>
          </div>
        </div>
      </div>

      {/* Detailed Latency Breakdown progress bars */}
      <div className="space-y-3.5">
        <h4 className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
          Latency Breakdown ({(totLat / 1000).toFixed(2)}s total)
        </h4>
        <div className="space-y-3 bg-zinc-900/20 border border-zinc-800/30 rounded-lg p-3.5">
          {/* Retrieval progress bar */}
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
