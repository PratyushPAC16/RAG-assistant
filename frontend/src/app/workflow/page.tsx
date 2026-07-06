"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useChatStore } from "@/store/chatStore";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Compass,
  Database,
  Sparkles,
  Cpu,
  Layers,
  Search,
  CheckCircle2,
  Info,
  Play,
  Activity,
  ArrowRight,
  Clock,
  Coins,
  ShieldCheck,
} from "lucide-react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  Node,
  Edge,
} from "reactflow";
import "reactflow/dist/style.css";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

// Custom Node Component to style React Flow nodes
interface NodeData {
  title: string;
  icon: any;
  timingMetric: string;
  description: string;
  isActive: boolean;
  isCompleted: boolean;
  colorClass: string;
  details: string[];
  schemaSample: string;
  metrics?: {
    label: string;
    value: string;
  }[];
}

function RAGPipelineNode({ data }: { data: NodeData }) {
  const Icon = data.icon;
  const isSuccess = data.isCompleted;
  const isActive = data.isActive;

  // Extract the color name from colorClass (e.g. "text-blue-400 ..." → "blue")
  const accentColorMap: Record<string, string> = {
    blue:    "rgba(96,165,250,0.75)",
    emerald: "rgba(52,211,153,0.75)",
    amber:   "rgba(251,191,36,0.75)",
    cyan:    "rgba(34,211,238,0.75)",
    indigo:  "rgba(129,140,248,0.75)",
    violet:  "rgba(167,139,250,0.75)",
  };
  const colorKey = Object.keys(accentColorMap).find((k) =>
    data.colorClass.includes(k)
  ) ?? "blue";
  const accentColor = accentColorMap[colorKey];

  return (
    <div
      className={cn(
        "w-44 p-4 rounded-xl flex flex-col items-center text-center transition-all duration-300 relative glass-card",
        isActive
          ? "border-primary shadow-[0_0_20px_rgba(139,92,246,0.3)] ring-1 ring-primary/45 scale-105"
          : isSuccess
          ? "border-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
          : "hover:border-zinc-750"
      )}
    >
      <Handle type="target" position={Position.Left} className="w-1.5 h-1.5 bg-zinc-800 border-zinc-900 !left-[-4px]" />
      <Handle type="source" position={Position.Right} className="w-1.5 h-1.5 bg-zinc-800 border-zinc-900 !right-[-4px]" />

      {/* Colored left-edge accent strip — matches dashboard recentActivity color per agent type */}
      <div
        className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl pointer-events-none"
        style={{
          background: `linear-gradient(to bottom, ${accentColor}, ${accentColor.replace("0.75", "0.30")})`,
        }}
        aria-hidden
      />

      {/* Glow highlight top line */}
      {isActive && (
        <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-primary to-transparent" />
      )}

      <div
        className={cn(
          "p-2.5 rounded-lg border bg-zinc-900/40 mb-3 transition-colors shrink-0",
          isActive
            ? "text-primary border-primary/20 bg-primary/5"
            : isSuccess
            ? "text-emerald-400 border-emerald-500/25 bg-emerald-500/5"
            : "text-zinc-500 border-zinc-850"
        )}
      >
        <Icon className="w-5 h-5" />
      </div>

      <span className="text-xs font-bold text-zinc-200 tracking-wide select-none">{data.title}</span>
      <span className="text-[9px] font-mono text-zinc-550 mt-1 select-none font-bold uppercase">{data.timingMetric}</span>

      {data.metrics && data.metrics.length > 0 && (
        <div className="mt-2.5 w-full pt-2 border-t border-zinc-900/60 flex flex-col gap-1 text-[8px] font-mono text-zinc-500">
          {data.metrics.map((m, idx) => (
            <div key={idx} className="flex justify-between items-center select-none">
              <span>{m.label}</span>
              <span className="text-zinc-400 font-bold">{m.value}</span>
            </div>
          ))}
        </div>
      )}

      {isActive && (
        <span className="absolute -top-2 bg-primary text-primary-foreground px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider animate-pulse shadow-md">
          Running
        </span>
      )}
    </div>
  );
}

// Bind custom components in React Flow
const nodeTypes = {
  pipelineNode: RAGPipelineNode,
};

export default function ArchitecturePage() {
  const {
    currentDecision,
    currentLatency,
    currentSources,
    currentMemories,
    currentTokens,
  } = useChatStore();

  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string>("query");
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Dynamic values mapped from the Zustand store
  const totLat = currentLatency.total || currentLatency.total_latency_ms || 0;
  const routerLat = currentLatency.router || (currentDecision ? 65 : 120);
  const memoryLat = currentLatency.memory || (currentMemories.length > 0 ? 90 : 50);
  const vectorLat = currentLatency.vector_search || 180;
  const bm25Lat = currentLatency.bm25_search || 85;
  const rerankLat = currentLatency.reranking || 85;
  const synthesisLat = currentLatency.synthesis_llm || currentLatency.llm || 1200;
  const responseLat = 1;

  // Node structures
  const nodeDefinitions = [
    {
      id: "query",
      title: "User Query",
      description: "Captures user query prompts, filters, and applies string formatting.",
      icon: Sparkles,
      colorClass: "text-violet-400 border-violet-500/20 bg-violet-500/5",
      timingMetric: "Latency: <1ms",
      details: [
        "Formats input query string payload",
        "Generates session identifiers",
        "Enforces max prompt limitations",
      ],
      schemaSample: "{\n  \"query\": \"Explain semantic RAG...\",\n  \"session_id\": \"sess_5a1f22\"\n}",
      metrics: [
        { label: "Query Size", value: `${currentDecision?.num_docs_available ? "Active" : "Normal"}` },
      ],
    },
    {
      id: "router",
      title: "Router Node",
      description: "Evaluates intent and classifies the query to select RAG, Web Search, or Memory agents.",
      icon: Compass,
      colorClass: "text-blue-400 border-blue-500/20 bg-blue-500/5",
      timingMetric: `Latency: ${routerLat.toFixed(0)}ms`,
      details: [
        "Runs zero-shot classification evaluation",
        "Decides routing context splits",
        "Applies fallback routing when offline",
      ],
      schemaSample: "{\n  \"agent\": \"rag\",\n  \"confidence\": 0.96,\n  \"reasoning\": \"Queries local databases\"\n}",
      metrics: [
        { label: "Route", value: currentDecision?.agent?.toUpperCase() || "RAG" },
        { label: "Confidence", value: `${((currentDecision?.confidence ?? 0.96) * 100).toFixed(0)}%` },
      ],
    },
    {
      id: "memory",
      title: "Memory Sync",
      description: "Queries long-term database storage to inject conversation history and candidate settings.",
      icon: Database,
      colorClass: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5",
      timingMetric: `Latency: ${memoryLat.toFixed(0)}ms`,
      details: [
        "Fetches user preference memory",
        "Loads recent conversation histories",
        "Combines profiles context blocks",
      ],
      schemaSample: "{\n  \"memories_found\": 2,\n  \"session_id\": \"sess_5a1f22\"\n}",
      metrics: [
        { label: "Facts Loaded", value: `${currentMemories.length} facts` },
      ],
    },
    {
      id: "retrieval",
      title: "Hybrid Search",
      description: "Queries dense vector indexes (ChromaDB) and sparse text matching (BM25) in parallel.",
      icon: Search,
      colorClass: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5",
      timingMetric: `Latency: ${Math.max(vectorLat, bm25Lat).toFixed(0)}ms`,
      details: [
        "Queries ChromaDB cosine coordinates",
        "Scrapes BM25 Okapi indices in parallel",
        "Performs Reciprocal Rank Fusion (RRF)",
      ],
      schemaSample: "{\n  \"vector_hits\": 20,\n  \"bm25_hits\": 20,\n  \"rrf_fused\": 5\n}",
      metrics: [
        { label: "Vector hits", value: `${currentSources.length ? currentSources.length * 2 : 12} items` },
        { label: "BM25 hits", value: `${currentSources.length ? currentSources.length : 6} items` },
      ],
    },
    {
      id: "reranker",
      title: "Cross Reranker",
      description: "Re-scores document segments via cross-encoders to supply highly pertinent context.",
      icon: Layers,
      colorClass: "text-indigo-400 border-indigo-500/20 bg-indigo-500/5",
      timingMetric: `Latency: ${rerankLat.toFixed(0)}ms`,
      details: [
        "Applies MiniLM cross-encoder scoring",
        "Filters out low-relevance noise",
        "Retains top 5 semantic context blocks",
      ],
      schemaSample: "{\n  \"top_chunk_id\": \"chk_2a8\",\n  \"rerank_score\": 0.941\n}",
      metrics: [
        { label: "Rerank Model", value: "bge-large" },
        { label: "Top Chunks", value: "5 hits" },
      ],
    },
    {
      id: "provider",
      title: "LLM Provider",
      description: "Generates output answers based on the injected context using Ollama, Groq, or Gemini.",
      icon: Cpu,
      colorClass: "text-amber-400 border-amber-500/20 bg-amber-500/5",
      timingMetric: `Latency: ${synthesisLat.toFixed(0)}ms`,
      details: [
        "Calls local or cloud API endpoints",
        "Triggers streaming typing emulator",
        "Extracts prompt token distributions",
      ],
      schemaSample: "{\n  \"provider\": \"gemini\",\n  \"total_tokens\": 762,\n  \"cost\": 0.00014\n}",
      metrics: [
        { label: "Tokens", value: `${currentTokens?.total ?? 762} tok` },
        { label: "Cost (Est)", value: `$${(currentTokens?.cost ?? 0.00014).toFixed(5)}` },
      ],
    },
    {
      id: "response",
      title: "Response Compiler",
      description: "Formats output markdown text and structures clickable source cards.",
      icon: CheckCircle2,
      colorClass: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5",
      timingMetric: `Latency: ${responseLat.toFixed(0)}ms`,
      details: [
        "Deduplicates citation URLs and pages",
        "Appends source expandable widgets",
        "Saves conversation history logs",
      ],
      schemaSample: "{\n  \"answer\": \"Successful prompt...\",\n  \"sources\": [\"Resume.pdf\"]\n}",
      metrics: [
        { label: "Citations", value: `${currentSources.length} files` },
        { label: "Status", value: "Success" },
      ],
    },
  ];

  // React Flow nodes coordinates mapping
  const flowNodes: Node[] = nodeDefinitions.map((n, idx) => {
    const isActive = isSimulating ? activeStep === idx : hoveredNodeId === n.id;
    const isCompleted = isSimulating ? (activeStep !== null && idx < activeStep) : false;

    return {
      id: n.id,
      type: "pipelineNode",
      position: { x: 50 + idx * 220, y: 80 },
      data: {
        title: n.title,
        icon: n.icon,
        timingMetric: n.timingMetric,
        description: n.description,
        isActive,
        isCompleted,
        colorClass: n.colorClass,
        details: n.details,
        schemaSample: n.schemaSample,
        metrics: n.metrics,
      },
    };
  });

  // React Flow edges mapping with animated flow lines
  const flowEdges: Edge[] = [
    { id: "e-query-router", source: "query", target: "router" },
    { id: "e-router-memory", source: "router", target: "memory" },
    { id: "e-memory-retrieval", source: "memory", target: "retrieval" },
    { id: "e-retrieval-reranker", source: "retrieval", target: "reranker" },
    { id: "e-reranker-provider", source: "reranker", target: "provider" },
    { id: "e-provider-response", source: "provider", target: "response" },
  ].map((edge, idx) => {
    const isActivePath = isSimulating ? (activeStep !== null && idx < activeStep) : false;
    
    return {
      ...edge,
      animated: isSimulating ? (activeStep !== null && idx === activeStep) : true,
      style: {
        stroke: isActivePath ? "#10b981" : isSimulating && activeStep === idx ? "#8b5cf6" : "#27272a",
        strokeWidth: isActivePath || (isSimulating && activeStep === idx) ? 3 : 1.5,
        transition: "stroke 0.3s, stroke-width 0.3s",
      },
    };
  });

  // Simulation execution loop
  const startSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setActiveStep(0);
    setSelectedNodeId(nodeDefinitions[0].id);

    let step = 0;
    const interval = setInterval(() => {
      if (step < nodeDefinitions.length - 1) {
        step++;
        setActiveStep(step);
        setSelectedNodeId(nodeDefinitions[step].id);
      } else {
        clearInterval(interval);
        setIsSimulating(false);
        setActiveStep(null);
      }
    }, 1300);
  };

  // Node selection details mapping
  const activeNodeInfo = nodeDefinitions.find(n => n.id === selectedNodeId) || nodeDefinitions[0];
  const hoveredNodeInfo = nodeDefinitions.find(n => n.id === hoveredNodeId);
  const nodeToShow = hoveredNodeInfo || activeNodeInfo;

  return (
    <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-8 select-none bg-zinc-950/20">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-zinc-900 pb-5 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Cpu className="w-8 h-8 text-primary shrink-0" />
            System Architecture
          </h1>
          <p className="text-zinc-500 text-xs mt-1 leading-relaxed">
            Interactive system flow-graph detailing semantic routing, hybrid searches, MiniLM reranking filters, and compiler citation outputs.
          </p>
        </div>
        
        <Button
          onClick={startSimulation}
          disabled={isSimulating}
          variant="primary"
          size="sm"
          className="flex items-center gap-1.5 font-bold text-xs bg-gradient-to-r from-violet-600 to-indigo-500 hover:from-violet-500 hover:to-indigo-400 text-zinc-100 border-0 shadow-lg shadow-violet-600/10 hover:shadow-violet-600/20 rounded-lg shrink-0 px-5 py-3 h-auto"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          Trace Graph Execution
        </Button>
      </div>

      {/* Interactive React Flow Canvas Wrapper */}
      <Card className="glass-panel border-zinc-900/60 overflow-hidden shadow-2xl relative">
        {/* Connection status tag */}
        <div className="absolute top-4 left-4 z-20 flex items-center gap-1.5 bg-zinc-950/80 border border-zinc-850 px-2.5 py-1 rounded-md text-[9px] font-mono text-zinc-400 backdrop-blur">
          <Activity className="w-3.5 h-3.5 text-primary animate-pulse" />
          <span>Interactive Canvas (Pan / Scroll to Zoom)</span>
        </div>

        {/* Global Total Latency Badge */}
        {totLat > 0 && (
          <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-zinc-950/80 border border-zinc-850 px-2.5 py-1 rounded-md text-[9px] font-mono text-zinc-400 backdrop-blur">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>Active Latency: <strong>{(totLat / 1000).toFixed(2)}s</strong></span>
          </div>
        )}

        <div className="h-[280px] w-full bg-zinc-950/30">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            minZoom={0.3}
            maxZoom={1.5}
            onNodeClick={(e, node) => setSelectedNodeId(node.id)}
            onNodeMouseEnter={(e, node) => setHoveredNodeId(node.id)}
            onNodeMouseLeave={() => setHoveredNodeId(null)}
            attributionPosition="bottom-right"
          >
            <Background color="#1f1f23" gap={16} size={1} />
            <Controls className="!bg-zinc-900 !border-zinc-800 [&_button]:!bg-zinc-900 [&_button]:!border-zinc-800 [&_svg]:!fill-zinc-400" />
            <MiniMap
              className="!bg-zinc-950/80 !border-zinc-850/60 !rounded-lg overflow-hidden shrink-0 hidden md:block"
              nodeColor={() => "#18181b"}
              maskColor="rgba(0,0,0,0.5)"
              style={{ width: 100, height: 75 }}
            />
          </ReactFlow>
        </div>
      </Card>

      {/* Component Details breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Functional details */}
        <Card className="lg:col-span-2 glass-panel border-zinc-900/60">
          <CardHeader className="border-b border-zinc-900/60 bg-zinc-950/10">
            <div className="flex justify-between items-center">
              <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2">
                <span className="p-1.5 bg-primary/10 border border-primary/20 rounded-lg text-primary shrink-0">
                  {React.createElement(nodeToShow.icon, { className: "w-4.5 h-4.5" })}
                </span>
                {nodeToShow.title} Component
              </CardTitle>
              <span className="font-mono text-[9px] font-bold bg-zinc-900/80 px-2.5 py-1 rounded border border-zinc-800 text-zinc-450 uppercase">
                {nodeToShow.timingMetric}
              </span>
            </div>
            <CardDescription className="text-zinc-550 text-xs mt-1.5 leading-relaxed">
              {nodeToShow.description}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5 space-y-4">
            <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-widest font-mono select-none block">
              Node Execution Pipelines
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {nodeToShow.details.map((detail, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg bg-zinc-900/10 border border-zinc-850/60 text-xs text-zinc-300 leading-relaxed flex flex-col gap-2 relative overflow-hidden group hover:border-zinc-800 transition-colors"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                  <span className="select-text">{detail}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Schema payload */}
        <Card className="glass-panel border-zinc-900/60">
          <CardHeader className="border-b border-zinc-900/60 bg-zinc-950/10">
            <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
              <Info className="w-4.5 h-4.5 text-cyan-400" />
              DTO Schema Payload
            </CardTitle>
            <CardDescription className="text-zinc-500 text-[10px] font-medium leading-relaxed">
              Pydantic model input/output JSON schemas.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5 select-text">
            <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-900 font-mono text-[10px] text-zinc-400 leading-relaxed overflow-x-auto whitespace-pre custom-scrollbar select-all cursor-text">
              {nodeToShow.schemaSample}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
