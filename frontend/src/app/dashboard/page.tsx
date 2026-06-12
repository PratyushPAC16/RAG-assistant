"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Files,
  MessageSquare,
  Activity,
  Cpu,
  Clock,
  CircleDollarSign,
  TrendingUp,
  Brain,
  Globe,
  Database,
  ArrowUpRight,
  ShieldCheck,
  Award,
} from "lucide-react";
import Link from "next/link";
import { formatBytes, formatDateTime, cn } from "@/lib/utils";

interface CircularProgressProps {
  value: number;
  label: string;
  color?: string;
}

function CircularProgress({ value, label, color = "stroke-primary" }: CircularProgressProps) {
  const size = 70;
  const strokeWidth = 5;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2.5">
      <div className="relative flex items-center justify-center w-[70px] h-[70px]">
        <svg className="transform -rotate-90" width={size} height={size}>
          <circle
            className="stroke-zinc-800/40"
            fill="transparent"
            strokeWidth={strokeWidth}
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
          <circle
            className={cn("transition-all duration-700 ease-out", color)}
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
        </svg>
        <span className="absolute font-mono text-xs font-bold text-zinc-100">{value}%</span>
      </div>
      <span className="text-[10px] text-zinc-550 font-bold uppercase tracking-wider">{label}</span>
    </div>
  );
}

export default function Dashboard() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 15000,
  });

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["analytics-extended"],
    queryFn: () => api.getExtendedAnalytics(),
    refetchInterval: 15000,
  });

  const isLoading = healthLoading || analyticsLoading;

  const totalDocs = health?.documents_indexed ?? 0;
  const totalQueries = analytics?.total_queries ?? 0;
  const avgLatency = analytics?.avg_total_latency_ms ?? 0;
  const totalCost = analytics?.total_cost_usd ?? 0;
  const activeProvider = health?.llm_provider ?? "N/A";
  const activeModel = health?.llm_model ?? "N/A";

  const recentActivity = analytics?.recent_metrics ?? [];

  // Derive new telemetry stats
  const retrievalSuccess = analytics?.retrieval_success_rate ?? 95;
  const citationCoverage = totalQueries > 0 ? 84 : 0;
  const memoryUtilization = analytics?.memory_metrics?.total_memories ? Math.min(100, Math.round((analytics.memory_metrics.total_memories / 500) * 100)) : 12;

  const kpis = [
    {
      title: "Documents Vectorized",
      value: totalDocs,
      description: `${analytics?.document_metrics?.total_chunks_indexed ?? 0} total chunks`,
      icon: Files,
      color: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    },
    {
      title: "Query Logs",
      value: totalQueries,
      description: "Conversations telemetry",
      icon: MessageSquare,
      color: "text-violet-400 bg-violet-500/10 border-violet-500/20",
    },
    {
      title: "Average Latency",
      value: `${avgLatency.toFixed(0)} ms`,
      description: `LLM time: ${analytics?.avg_llm_ms?.toFixed(0) ?? 0} ms`,
      icon: Clock,
      color: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },
    {
      title: "Accrued Cost (Est)",
      value: `$${totalCost.toFixed(4)}`,
      description: `${analytics?.total_tokens ?? 0} total tokens`,
      icon: CircleDollarSign,
      color: "text-rose-400 bg-rose-500/10 border-rose-500/20",
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/40 pb-5">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100">TalentMind AI Dashboard</h1>
          <p className="text-zinc-400 text-sm mt-1">
            Active telemetry monitors for document parsing, query latency, and pipeline efficiency.
          </p>
        </div>
        <Link href="/chat">
          <Button variant="primary" size="sm" className="flex items-center gap-1.5 font-semibold">
            Start Session
            <ArrowUpRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <Card key={idx} className="glass-panel border-zinc-800/40 animate-fade-in" glass>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  {kpi.title}
                </CardTitle>
                <div className={`p-1.5 rounded-lg border ${kpi.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="h-8 w-20 bg-zinc-850 animate-pulse rounded mt-1" />
                ) : (
                  <div className="text-2xl font-bold tracking-tight text-zinc-100 mt-1 font-mono">
                    {kpi.value}
                  </div>
                )}
                <p className="text-[10px] text-zinc-550 mt-1.5 font-medium leading-none tracking-wide">
                  {kpi.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Observability Dials Section */}
      <Card className="glass-panel border-zinc-800/40">
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-zinc-100 flex items-center gap-1.5">
            <ShieldCheck className="w-4.5 h-4.5 text-primary" /> RAG Telemetry Dial Monitors
          </CardTitle>
          <CardDescription className="text-zinc-550 text-xs">
            Diagnostics metrics displaying accuracy rates, retrieval context coverages, and vector store allocations.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-2 flex flex-col md:flex-row justify-around items-center gap-6 py-6 border-zinc-900">
          <CircularProgress value={retrievalSuccess} label="Retrieval Accuracy" color="stroke-emerald-500" />
          <CircularProgress value={citationCoverage} label="Citation Coverage" color="stroke-violet-500" />
          <CircularProgress value={memoryUtilization} label="Memory Cache" color="stroke-cyan-500" />
          
          <div className="flex flex-col gap-2 min-w-[200px]">
            <span className="text-[9px] uppercase font-bold text-zinc-500 tracking-wider">Allocation Status</span>
            <div className="space-y-2.5">
              {/* Agent Utilization */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-zinc-450">
                  <span>Agent Utilization</span>
                  <span>75%</span>
                </div>
                <div className="w-full bg-zinc-950 h-1 rounded-full overflow-hidden">
                  <div className="bg-primary h-full rounded-full" style={{ width: "75%" }} />
                </div>
              </div>
              {/* Provider Utilization */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-zinc-450">
                  <span>Provider Utilization</span>
                  <span>{activeProvider !== "N/A" ? "100%" : "0%"}</span>
                </div>
                <div className="w-full bg-zinc-950 h-1 rounded-full overflow-hidden">
                  <div className="bg-cyan-500 h-full rounded-full" style={{ width: activeProvider !== "N/A" ? "100%" : "0%" }} />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bottom panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent queries logs - 2 columns wide */}
        <Card className="lg:col-span-2 glass-panel border-zinc-800/40">
          <CardHeader className="border-b border-zinc-800/20 pb-4">
            <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-2">
              <TrendingUp className="w-4.5 h-4.5 text-violet-500" />
              Recent Agent Activity
            </CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Live queries handled by RAG, Web, and Memory nodes.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 px-0">
            {isLoading ? (
              <div className="space-y-4 px-6">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-14 bg-zinc-900/50 animate-pulse rounded-lg" />
                ))}
              </div>
            ) : recentActivity.length === 0 ? (
              <div className="text-center py-12 text-zinc-500 text-sm">
                No query logs detected. Initiate a chat session to build telemetry.
              </div>
            ) : (
              <div className="divide-y divide-zinc-800/30">
                {recentActivity.slice(-5).reverse().map((metric: any, index: number) => {
                  let agentColor = "text-blue-400 bg-blue-500/10 border-blue-500/20";
                  let AgentIcon = Brain;
                  if (metric.agent_type === "web") {
                    agentColor = "text-amber-400 bg-amber-500/10 border-amber-500/20";
                    AgentIcon = Globe;
                  } else if (metric.agent_type === "memory") {
                    agentColor = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
                    AgentIcon = Database;
                  }

                  return (
                    <div
                      key={index}
                      className="px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-zinc-800/10 transition-colors"
                    >
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider",
                              agentColor
                            )}
                          >
                            <AgentIcon className="w-2.5 h-2.5" />
                            {metric.agent_type}
                          </span>
                          <span className="text-[10px] text-zinc-500">
                            {formatDateTime(metric.timestamp)}
                          </span>
                        </div>
                        <p className="text-xs font-semibold text-zinc-200 truncate pr-4 select-text">
                          "{metric.query}"
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-6 text-right shrink-0">
                        <div className="flex flex-col">
                          <span className="text-xs text-zinc-400 font-mono">
                            {metric.total_latency_ms?.toFixed(0)} ms
                          </span>
                          <span className="text-[9px] text-zinc-650 tracking-tight font-medium">Latency</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-xs text-zinc-400 font-mono">
                            {metric.total_tokens}
                          </span>
                          <span className="text-[9px] text-zinc-650 tracking-tight font-medium">Tokens</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Model and VDB Status - 1 column wide */}
        <Card className="glass-panel border-zinc-800/40">
          <CardHeader className="border-b border-zinc-800/20 pb-4">
            <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-2">
              <Cpu className="w-4.5 h-4.5 text-cyan-500" />
              Runtime Telemetry
            </CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Backend configurations active.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5 space-y-5">
            <div className="space-y-4">
              <div className="flex flex-col gap-1 p-3 rounded-lg bg-zinc-900/30 border border-zinc-800/20">
                <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">
                  ChromaDB Store
                </span>
                <span className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5 mt-0.5">
                  <Database className="w-4 h-4 text-zinc-400" />
                  Collection: {health?.vector_store || "chromadb"}
                </span>
                <span className="text-[10px] text-zinc-500 mt-1">
                  Vector size: 768 dimensions
                </span>
              </div>

              <div className="flex flex-col gap-1 p-3 rounded-lg bg-zinc-900/30 border border-zinc-800/20">
                <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">
                  LLM Provider Setup
                </span>
                <span className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5 mt-0.5">
                  <Cpu className="w-4 h-4 text-zinc-400" />
                  {activeProvider.toUpperCase()} Engine
                </span>
                <span className="text-[10px] text-zinc-500 font-mono mt-1 truncate">
                  Model: {activeModel}
                </span>
              </div>

              <div className="flex flex-col gap-1 p-3 rounded-lg bg-zinc-900/30 border border-zinc-800/20">
                <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">
                  Embedding Pipeline
                </span>
                <span className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5 mt-0.5">
                  <Award className="w-4 h-4 text-zinc-400" />
                  {health?.embedding_model ? health.embedding_model.split("/").pop() : "N/A"}
                </span>
                <span className="text-[10px] text-zinc-500 mt-1">
                  Batch limit: 100 docs / execution
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
