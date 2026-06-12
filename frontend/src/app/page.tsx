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
} from "lucide-react";
import Link from "next/link";
import { formatBytes, formatDateTime } from "@/lib/utils";

export default function Dashboard() {
  // Fetch Health for active LLM configs and docs count
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 15000, // Refresh every 15s
  });

  // Fetch Extended Analytics
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["analytics-extended"],
    queryFn: () => api.getExtendedAnalytics(),
    refetchInterval: 15000,
  });

  const isLoading = healthLoading || analyticsLoading;

  // Derive stats
  const totalDocs = health?.documents_indexed ?? 0;
  const totalQueries = analytics?.total_queries ?? 0;
  const avgLatency = analytics?.avg_total_latency_ms ?? 0;
  const totalCost = analytics?.total_cost_usd ?? 0;
  const activeProvider = health?.llm_provider ?? "N/A";
  const activeModel = health?.llm_model ?? "N/A";

  const recentActivity = analytics?.recent_metrics ?? [];

  const kpis = [
    {
      title: "Total Documents",
      value: totalDocs,
      description: `${analytics?.document_metrics?.total_chunks_indexed ?? 0} vectorized chunks`,
      icon: Files,
      color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
    },
    {
      title: "Total Queries",
      value: totalQueries,
      description: "Across all sessions",
      icon: MessageSquare,
      color: "text-violet-500 bg-violet-500/10 border-violet-500/20",
    },
    {
      title: "Average Latency",
      value: `${avgLatency} ms`,
      description: `LLM time: ${analytics?.avg_llm_ms ?? 0} ms`,
      icon: Clock,
      color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
    },
    {
      title: "Provider",
      value: activeProvider.toUpperCase(),
      description: "Host: Local / Cloud",
      icon: Cpu,
      color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
    },
    {
      title: "Active Model",
      value: activeModel.split("/").pop() ?? "N/A",
      description: `Embeddings: ${health?.embedding_model.split("/").pop() ?? "N/A"}`,
      icon: Activity,
      color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20",
    },
    {
      title: "Cost Saved (Est.)",
      value: `$${totalCost.toFixed(4)}`,
      description: `${analytics?.total_tokens ?? 0} tokens generated`,
      icon: CircleDollarSign,
      color: "text-rose-500 bg-rose-500/10 border-rose-500/20",
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/40 pb-5">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100">System Dashboard</h1>
          <p className="text-zinc-400 text-sm mt-1">
            Real-time telemetry and indexing logs for the Enterprise RAG Agent.
          </p>
        </div>
        <Link href="/chat">
          <Button variant="primary" size="sm" className="flex items-center gap-1.5 font-medium">
            Start New Chat
            <ArrowUpRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <Card key={idx} className="glass-panel border-zinc-800/40" glass>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  {kpi.title}
                </CardTitle>
                <div className={`p-2 rounded-lg border ${kpi.color}`}>
                  <Icon className="w-4.5 h-4.5" />
                </div>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="h-8 w-24 bg-zinc-800/40 animate-pulse rounded mt-1" />
                ) : (
                  <div className="text-2xl font-bold tracking-tight text-zinc-100 mt-1">
                    {kpi.value}
                  </div>
                )}
                <p className="text-[11px] text-zinc-500 mt-1.5 tracking-wide leading-none">
                  {kpi.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Bottom Observability panels */}
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
                            className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider ${agentColor}`}
                          >
                            <AgentIcon className="w-3 h-3" />
                            {metric.agent_type}
                          </span>
                          <span className="text-[10px] text-zinc-500">
                            {formatDateTime(metric.timestamp)}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-zinc-200 truncate pr-4">
                          "{metric.query}"
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-6 text-right shrink-0">
                        <div className="flex flex-col">
                          <span className="text-xs text-zinc-400 font-mono">
                            {metric.total_latency_ms} ms
                          </span>
                          <span className="text-[10px] text-zinc-500 tracking-tight">Latency</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-xs text-zinc-400 font-mono">
                            {metric.total_tokens}
                          </span>
                          <span className="text-[10px] text-zinc-500 tracking-tight">Tokens</span>
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
                <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
                  ChromaDB Store
                </span>
                <span className="text-sm font-semibold text-zinc-200 flex items-center gap-1.5 mt-0.5">
                  <Database className="w-4 h-4 text-zinc-400" />
                  Collection: {health?.vector_store || "chromadb"}
                </span>
                <span className="text-xs text-zinc-400 mt-1">
                  Vector size: 768 dimensions
                </span>
              </div>

              <div className="flex flex-col gap-1 p-3 rounded-lg bg-zinc-900/30 border border-zinc-800/20">
                <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
                  LLM Provider Setup
                </span>
                <span className="text-sm font-semibold text-zinc-200 flex items-center gap-1.5 mt-0.5">
                  <Cpu className="w-4 h-4 text-zinc-400" />
                  {activeProvider.toUpperCase()} Engine
                </span>
                <span className="text-xs text-zinc-400 font-mono mt-1 truncate">
                  Model: {activeModel}
                </span>
              </div>

              <div className="flex flex-col gap-1 p-3 rounded-lg bg-zinc-900/30 border border-zinc-800/20">
                <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
                  Embedding Pipeline
                </span>
                <span className="text-sm font-semibold text-zinc-200 flex items-center gap-1.5 mt-0.5">
                  <Activity className="w-4 h-4 text-zinc-400" />
                  {health?.embedding_model ? health.embedding_model.split("/").pop() : "N/A"}
                </span>
                <span className="text-xs text-zinc-400 mt-1">
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
