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
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ArchitectureNode {
  id: string;
  title: string;
  description: string;
  icon: any;
  color: string;
  details: string[];
}

const nodes: ArchitectureNode[] = [
  {
    id: "query",
    title: "User Query",
    description: "Accepts search query and filters.",
    icon: Sparkles,
    color: "text-zinc-400 border-zinc-800/40 bg-zinc-950/40 hover:border-zinc-700/60",
    details: [
      "Performs client-side request stripping",
      "Injects conversation Session UUID",
      "Appends optional file filter scopes",
    ],
  },
  {
    id: "router",
    title: "Router Node",
    description: "Evaluates intent and routes traffic.",
    icon: Compass,
    color: "text-blue-400 border-blue-500/20 bg-blue-500/5 hover:border-blue-500/40",
    details: [
      "Uses prompt templates for zero-shot routing",
      "Supports RAG, Web Search, or Memory agents",
      "Applies rule-based overrides on empty documents",
    ],
  },
  {
    id: "agent",
    title: "Agent (LangGraph)",
    description: "Drives conversational state machine.",
    icon: Cpu,
    color: "text-purple-400 border-purple-500/20 bg-purple-500/5 hover:border-purple-500/40",
    details: [
      "Manages StateGraph contextual dictionaries",
      "Controls recursive execution checks",
      "Decides when to synthesise or fetch memory",
    ],
  },
  {
    id: "retrieval",
    title: "Hybrid Retrieval",
    description: "Queries vector and keyword indexes.",
    icon: Search,
    color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5 hover:border-cyan-500/40",
    details: [
      "Queries ChromaDB using Gemini Embeddings",
      "Runs local BM25 okapi keyword scoring",
      "Fuses scores via Reciprocal Rank Fusion (RRF)",
    ],
  },
  {
    id: "reranker",
    title: "Reranker Node",
    description: "Refines chunk relevance scores.",
    icon: Layers,
    color: "text-indigo-400 border-indigo-500/20 bg-indigo-500/5 hover:border-indigo-500/40",
    details: [
      "Uses cross-encoder/ms-marco-MiniLM model",
      "Filters out low-score noisy context chunks",
      "Saves top 5 most-relevant chunks",
    ],
  },
  {
    id: "provider",
    title: "Provider Layer",
    description: "Invokes selected LLM runtime engine.",
    icon: Database,
    color: "text-amber-400 border-amber-500/20 bg-amber-500/5 hover:border-amber-500/40",
    details: [
      "Connects to Gemini Cloud or Groq APIs",
      "Queries Ollama local models (e.g. Llama 3.2)",
      "Monitors token lengths and pricing estimates",
    ],
  },
  {
    id: "response",
    title: "Response Output",
    description: "Compiles cited Markdown markdown answers.",
    icon: CheckCircle2,
    color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5 hover:border-emerald-500/40",
    details: [
      "Renders markdown syntax tables and lists",
      "Injects clickable document citations",
      "Updates conversation persistence managers",
    ],
  },
];

export default function ArchitecturePage() {
  const [selectedNode, setSelectedNode] = useState<ArchitectureNode>(nodes[0]);
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
    }, 1500);
  };

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
            Visual pipeline representation. Track how User Queries flow through routing classifiers, hybrid search engines, and cross-encoders.
          </p>
        </div>
        <Button
          onClick={startSimulation}
          disabled={isSimulating}
          variant="primary"
          size="sm"
          className="flex items-center gap-1.5"
        >
          <Play className="w-4 h-4 fill-current" />
          Simulate Execution
        </Button>
      </div>

      {/* Visual Pipeline Loop - Horizontal on desktop, grid on mobile */}
      <div className="p-8 rounded-2xl bg-zinc-950/30 border border-zinc-900 overflow-x-auto select-none relative backdrop-blur-md">
        {/* Glow path overlay */}
        <div className="hidden lg:block absolute left-14 right-14 top-1/2 -translate-y-1/2 h-0.5 bg-zinc-850" />
        
        <div className="flex flex-col lg:flex-row items-center justify-between gap-6 relative z-10 min-w-[900px] lg:min-w-0">
          {nodes.map((node, index) => {
            const Icon = node.icon;
            const isSelected = selectedNode.id === node.id;
            const isActiveSimNode = activeStep === index;

            return (
              <React.Fragment key={node.id}>
                {/* Node Box */}
                <motion.div
                  onClick={() => setSelectedNode(node)}
                  animate={isActiveSimNode ? { scale: 1.05 } : { scale: 1 }}
                  className={cn(
                    "w-36 p-4 rounded-xl border flex flex-col items-center text-center cursor-pointer transition-all duration-300 relative",
                    node.color,
                    isSelected
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
                      Active
                    </span>
                  )}
                </motion.div>

                {/* Arrow connector */}
                {index < nodes.length - 1 && (
                  <ArrowRight
                    className={cn(
                      "w-4 h-4 text-zinc-700 hidden lg:block shrink-0 transition-colors duration-300",
                      activeStep !== null && activeStep >= index && "text-primary animate-pulse"
                    )}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Component Details Block */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Component explanation */}
        <Card className="lg:col-span-2 glass-panel border-zinc-800/40">
          <CardHeader className="border-b border-zinc-800/20">
            <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-2">
              <span className="p-1.5 bg-primary/10 border border-primary/20 rounded-lg text-primary">
                {React.createElement(selectedNode.icon, { className: "w-4.5 h-4.5" })}
              </span>
              {selectedNode.title} Node
            </CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              {selectedNode.description}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5 space-y-4">
            <h4 className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">
              Functional Responsibilities
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {selectedNode.details.map((detail, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg bg-zinc-900/20 border border-zinc-800/30 text-xs text-zinc-300 leading-relaxed flex items-start gap-2"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0 mt-1.5" />
                  <span>{detail}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Observability Details Guide */}
        <Card className="glass-panel border-zinc-800/40">
          <CardHeader className="border-b border-zinc-800/20">
            <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-1.5">
              <HelpCircle className="w-5 h-5 text-cyan-400" /> System Guide
            </CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Understanding state pipelines.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5 space-y-4 text-xs leading-relaxed text-zinc-400">
            <p>
              Our multi-agent assistant leverages a State Graph Orchestrator pattern. Each card represents a dedicated stage execution thread in the backend.
            </p>
            <div className="space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span>Router: Zero-shot classification</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-500" />
                <span>Retrieval: ChromaDB vector match + BM25 keyword</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                <span>Reranker: Cross-Encoder score optimization</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
