"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Compass,
  Database,
  ArrowRight,
  Sparkles,
  HelpCircle,
  Play,
  Cpu,
  Layers,
  Search,
  CheckCircle2,
  Info,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface ArchitectureNode {
  id: string;
  title: string;
  description: string;
  icon: any;
  color: string;
  details: string[];
  timingMetric: string;
  schemaSample: string;
}

const nodes: ArchitectureNode[] = [
  {
    id: "query",
    title: "User Query",
    description: "Captures user query prompts and filters.",
    icon: Sparkles,
    color: "text-zinc-400 border-zinc-800 bg-zinc-950/45",
    timingMetric: "Latency: <1ms",
    details: [
      "Formats query input string lengths",
      "Injects session context trackers",
      "Enforces string limit constraints",
    ],
    schemaSample: "{\n  \"query\": \"RAG performance parameters\",\n  \"session_id\": \"sess_5a1f22\"\n}",
  },
  {
    id: "router",
    title: "Router Node",
    description: "Evaluates semantic intent to route traffic.",
    icon: Compass,
    color: "text-blue-400 border-blue-500/20 bg-blue-500/5",
    timingMetric: "Latency: ~120ms",
    details: [
      "Performs LLM-based zero-shot classifications",
      "Routes to RAG, Web Search, or Memory managers",
      "Falls back to local documents database on fail",
    ],
    schemaSample: "{\n  \"agent\": \"rag\",\n  \"confidence\": 0.96,\n  \"reasoning\": \"Queries local docs\"\n}",
  },
  {
    id: "agent",
    title: "Agent Controller",
    description: "Coordinates state machine execution loops.",
    icon: Cpu,
    color: "text-purple-400 border-purple-500/20 bg-purple-500/5",
    timingMetric: "Latency: ~50ms",
    details: [
      "Tracks contextual graph memory arrays",
      "Saves loop executions traces",
      "Coordinates document extraction sequences",
    ],
    schemaSample: "{\n  \"agent_state\": \"running\",\n  \"trace\": [\"init\", \"route_rag\"]\n}",
  },
  {
    id: "retrieval",
    title: "Hybrid Search",
    description: "Combines keyword and semantic retrievals.",
    icon: Search,
    color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5",
    timingMetric: "Latency: ~180ms",
    details: [
      "Runs cosine similarity search on ChromaDB",
      "Executes local BM25 okapi search",
      "Combines ranks using Reciprocal Rank Fusion (RRF)",
    ],
    schemaSample: "{\n  \"vector_hits\": 20,\n  \"bm25_hits\": 20,\n  \"rrf_fused\": 5\n}",
  },
  {
    id: "reranker",
    title: "Cross-Reranker",
    description: "Optimizes matching chunks relevance.",
    icon: Layers,
    color: "text-indigo-400 border-indigo-500/20 bg-indigo-500/5",
    timingMetric: "Latency: ~85ms",
    details: [
      "Uses cross-encoder/ms-marco-MiniLM model",
      "Discards low-probability noisy elements",
      "Delivers top 5 chunks for LLM contexts",
    ],
    schemaSample: "{\n  \"top_chunk_id\": \"chk_2a8\",\n  \"rerank_score\": 0.941\n}",
  },
  {
    id: "provider",
    title: "Provider Engine",
    description: "Translates contexts into prompt answers.",
    icon: Database,
    color: "text-amber-400 border-amber-500/20 bg-amber-500/5",
    timingMetric: "Latency: ~1200ms",
    details: [
      "Triggers Ollama, Groq, or Gemini dynamically",
      "Tracks generated cost parameters",
      "Counts inputs and outputs tokens",
    ],
    schemaSample: "{\n  \"provider\": \"gemini\",\n  \"total_tokens\": 762,\n  \"cost\": 0.00014\n}",
  },
  {
    id: "response",
    title: "Response compiler",
    description: "Prepares citation cards and markdown.",
    icon: CheckCircle2,
    color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5",
    timingMetric: "Latency: <1ms",
    details: [
      "Renders clickable page citation lists",
      "Persists conversation turn on disk databases",
      "Closes execution loop metrics tracking",
    ],
    schemaSample: "{\n  \"answer\": \"Semantic RAG uses...\",\n  \"citations\": [\"report.pdf\"]\n}",
  },
];

export default function ArchitecturePage() {
  const [selectedNode, setSelectedNode] = useState<ArchitectureNode>(nodes[0]);
  const [hoveredNode, setHoveredNode] = useState<ArchitectureNode | null>(null);
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const startSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setActiveStep(0);
    setSelectedNode(nodes[0]);

    let step = 0;
    const interval = setInterval(() => {
      if (step < nodes.length - 1) {
        step++;
        setActiveStep(step);
        setSelectedNode(nodes[step]);
      } else {
        clearInterval(interval);
        setIsSimulating(false);
        setActiveStep(null);
      }
    }, 1200);
  };

  const nodeToShow = hoveredNode || selectedNode;

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/40 pb-5">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Cpu className="w-8 h-8 text-primary" />
            System Architecture
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            Visual pipeline trace diagram showing semantic routing, hybrid indexing, and cross-encoder structures.
          </p>
        </div>
        <Button
          onClick={startSimulation}
          disabled={isSimulating}
          variant="primary"
          size="sm"
          className="flex items-center gap-1.5 font-semibold"
        >
          <Play className="w-4 h-4 fill-current" />
          Trace Pipeline
        </Button>
      </div>

      {/* Visual Pipeline map */}
      <div className="p-8 rounded-2xl bg-zinc-950/30 border border-zinc-900 overflow-x-auto select-none relative backdrop-blur-md">
        {/* Glow pipeline line */}
        <div className="hidden lg:block absolute left-14 right-14 top-1/2 -translate-y-1/2 h-0.5 bg-zinc-850">
          {isSimulating && activeStep !== null && (
            <motion.div
              className="absolute left-0 h-0.5 bg-primary rounded-full shadow-[0_0_8px_rgba(139,92,246,0.5)]"
              initial={{ width: "0%" }}
              animate={{ width: `${(activeStep / (nodes.length - 1)) * 100}%` }}
              transition={{ duration: 0.5, ease: "easeInOut" }}
            />
          )}
        </div>
        
        <div className="flex flex-col lg:flex-row items-center justify-between gap-6 relative z-10 min-w-[900px] lg:min-w-0">
          {nodes.map((node, index) => {
            const Icon = node.icon;
            const isSelected = selectedNode.id === node.id;
            const isHovered = hoveredNode?.id === node.id;
            const isActiveSimNode = activeStep === index;

            return (
              <React.Fragment key={node.id}>
                {/* Node Box card */}
                <motion.div
                  onHoverStart={() => setHoveredNode(node)}
                  onHoverEnd={() => setHoveredNode(null)}
                  onClick={() => setSelectedNode(node)}
                  animate={isActiveSimNode ? { scale: 1.05 } : { scale: 1 }}
                  className={cn(
                    "w-36 p-4 rounded-xl border flex flex-col items-center text-center cursor-pointer transition-all duration-300 relative",
                    node.color,
                    isSelected || isHovered
                      ? "ring-1 ring-primary border-primary bg-zinc-900/60 shadow-[0_0_20px_0_rgba(139,92,246,0.15)]"
                      : "bg-zinc-950/40 hover:bg-zinc-900/20"
                  )}
                >
                  <Icon className="w-6 h-6 mb-2" />
                  <span className="text-[11px] font-bold text-zinc-200 tracking-wide">
                    {node.title}
                  </span>
                  
                  {isActiveSimNode && (
                    <span className="absolute -top-2 bg-primary text-primary-foreground px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider animate-bounce">
                      Running
                    </span>
                  )}
                </motion.div>

                {/* Arrow connector */}
                {index < nodes.length - 1 && (
                  <ArrowRight
                    className={cn(
                      "w-4 h-4 text-zinc-750 hidden lg:block shrink-0 transition-colors duration-300",
                      activeStep !== null && activeStep >= index ? "text-primary animate-pulse" : "text-zinc-800"
                    )}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Node explanation details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Core responsibilities */}
        <Card className="lg:col-span-2 glass-panel border-zinc-800/40">
          <CardHeader className="border-b border-zinc-800/20">
            <div className="flex justify-between items-center">
              <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-2">
                <span className="p-1.5 bg-primary/10 border border-primary/20 rounded-lg text-primary">
                  {React.createElement(nodeToShow.icon, { className: "w-4.5 h-4.5" })}
                </span>
                {nodeToShow.title} Component
              </CardTitle>
              <span className="font-mono text-[10px] bg-zinc-900 px-2.5 py-1 rounded text-zinc-400 border border-zinc-850/50">
                {nodeToShow.timingMetric}
              </span>
            </div>
            <CardDescription className="text-zinc-550 text-xs">
              {nodeToShow.description}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5 space-y-5">
            <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">
              Functional Responsibilities
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {nodeToShow.details.map((detail, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg bg-zinc-900/20 border border-zinc-800/30 text-xs text-zinc-300 leading-relaxed flex flex-col gap-1.5"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                  <span>{detail}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Schema representation */}
        <Card className="glass-panel border-zinc-800/40">
          <CardHeader className="border-b border-zinc-800/20">
            <CardTitle className="text-sm font-semibold text-zinc-100 flex items-center gap-1.5">
              <Info className="w-4.5 h-4.5 text-cyan-400" /> DTO Schema Structure
            </CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Pydantic JSON schema sample.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5">
            <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-850/40 font-mono text-[10px] text-zinc-400 leading-relaxed overflow-x-auto whitespace-pre">
              {nodeToShow.schemaSample}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
