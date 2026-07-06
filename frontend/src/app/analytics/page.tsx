"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  BarChart3,
  TrendingUp,
  Clock,
  Coins,
  Cpu,
  Layers,
} from "lucide-react";
import { formatDateTime } from "@/lib/utils";

const COLORS = ["#D65BB4", "#66415C", "#ACFF5D", "#FF9F5B", "#E05B5B"];

/** Explicit shape for Recharts pie chart data items */
interface ChartDataItem {
  name: string;
  value: number;
}

export default function AnalyticsPage() {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ["analytics-extended"],
    queryFn: () => api.getExtendedAnalytics(),
    refetchInterval: 15000,
  });

  if (isLoading) {
    return (
      <div className="flex-grow flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm text-zinc-500 font-medium animate-pulse">Loading Analytics Dials...</span>
        </div>
      </div>
    );
  }

  // Fallbacks
  const dailyTrend = analytics?.daily_trend || [];
  const agentDist = analytics?.agent_distribution || {};
  const providerDist = analytics?.provider_usage || {};
  const recentLogs = analytics?.recent_metrics || [];

  // Parse Pie charts — explicitly typed so entry.value is number in JSX
  const agentChartData: ChartDataItem[] = Object.entries(agentDist).map(([key, val]) => ({
    name: key.toUpperCase(),
    value: val,
  }));

  const providerChartData: ChartDataItem[] = Object.entries(providerDist).map(([key, val]) => ({
    name: key.toUpperCase(),
    value: val,
  }));

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="border-b border-zinc-800/40 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <BarChart3 className="w-8 h-8 text-primary" />
          System Analytics
        </h1>
        <p className="text-zinc-400 text-sm mt-1">
          Detailed metrics tracking query volumes, latency distributions, model usage, and prompt expenditures.
        </p>
      </div>

      {/* Dials Summary Card Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          { label: "Total Queries", val: analytics?.total_queries ?? 0, desc: "Queries processed", icon: TrendingUp },
          { label: "Average Latency", val: `${analytics?.avg_total_latency_ms ?? 0} ms`, desc: `LLM Synthesis: ${analytics?.avg_llm_ms ?? 0}ms`, icon: Clock },
          { label: "Wasted Costs (Est)", val: `$${(analytics?.total_cost_usd ?? 0).toFixed(4)}`, desc: `${analytics?.total_tokens ?? 0} total tokens`, icon: Coins },
          { label: "Active Engine", val: (analytics?.llm_provider || "N/A").toUpperCase(), desc: "Model configuration sync", icon: Cpu },
        ].map((d, i) => {
          const Icon = d.icon;
          return (
            <Card key={i} className="glass-panel border-zinc-800/40" glass>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                  {d.label}
                </CardTitle>
                <Icon className="w-4 h-4 text-zinc-400" />
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold text-zinc-100 font-mono">{d.val}</div>
                <p className="text-[10px] text-zinc-500 mt-1">{d.desc}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Main Charts grids */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Daily Query Volumes Area Chart */}
        <Card className="glass-panel border-zinc-800/40">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-zinc-100">Daily Query Volume & Costs</CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Daily query frequency compared with token costs.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 flex justify-center">
            {dailyTrend.length === 0 ? (
              <div className="h-[250px] flex items-center justify-center text-zinc-500 text-xs">
                No history recorded.
              </div>
            ) : (
              <div className="w-full h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dailyTrend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#D65BB4" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#D65BB4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#30232E" />
                    <XAxis dataKey="date" stroke="#858585" fontSize={9} />
                    <YAxis stroke="#858585" fontSize={9} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#1A171B", borderColor: "#30232E", borderRadius: 12, fontSize: 10 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="queries"
                      stroke="#D65BB4"
                      fillOpacity={1}
                      fill="url(#colorQueries)"
                      name="Queries"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Latency Stacked Area Chart */}
        <Card className="glass-panel border-zinc-800/40">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-zinc-100">Latency Breakdown Trends</CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Latency share across retrieval, reranking, and synthesis phases.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 flex justify-center">
            {dailyTrend.length === 0 ? (
              <div className="h-[250px] flex items-center justify-center text-zinc-500 text-xs">
                No latency history recorded.
              </div>
            ) : (
              <div className="w-full h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dailyTrend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorLlm" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#D65BB4" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#D65BB4" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorRet" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#66415C" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#66415C" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#30232E" />
                    <XAxis dataKey="date" stroke="#858585" fontSize={9} />
                    <YAxis stroke="#858585" fontSize={9} unit="ms" />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#1A171B", borderColor: "#30232E", borderRadius: 12, fontSize: 10 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Area
                      type="monotone"
                      dataKey="avg_latency"
                      stackId="1"
                      stroke="#D65BB4"
                      fill="url(#colorLlm)"
                      name="Overall Latency"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Agent Splits Pie Chart */}
        <Card className="glass-panel border-zinc-800/40">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-zinc-100">Agent Routing Splits</CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Queries handled by RAG, Web Search, or Memory managers.
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[250px] flex justify-center items-center">
            {agentChartData.length === 0 ? (
              <span className="text-zinc-500 text-xs">No routing data available.</span>
            ) : (
              <div className="w-full h-full flex items-center justify-around">
                <div className="w-[180px] h-[180px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={agentChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={75}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {agentChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1A171B", borderColor: "#30232E", borderRadius: 12, fontSize: 10 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-400">
                  {agentChartData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span>{entry.name}:</span>
                      <span className="font-bold text-zinc-200">{entry.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Model Providers splits Pie Chart */}
        <Card className="glass-panel border-zinc-800/40">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-zinc-100">Model Provider Usage</CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Distribution across Gemini, Groq, and Ollama.
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[250px] flex justify-center items-center">
            {providerChartData.length === 0 ? (
              <span className="text-zinc-500 text-xs">No provider data available.</span>
            ) : (
              <div className="w-full h-full flex items-center justify-around">
                <div className="w-[180px] h-[180px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={providerChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={75}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {providerChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1A171B", borderColor: "#30232E", borderRadius: 12, fontSize: 10 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-400">
                  {providerChartData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: COLORS[(index + 2) % COLORS.length] }}
                      />
                      <span>{entry.name}:</span>
                      <span className="font-bold text-zinc-200">{entry.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Observability detailed list */}
      <Card className="glass-panel border-zinc-800/40 overflow-hidden">
        <CardHeader className="border-b border-zinc-800/20 pb-4">
          <CardTitle className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            Detailed Query Telemetry Log
          </CardTitle>
          <CardDescription className="text-zinc-500 text-xs">
            Query-by-query token lengths, cost calculations, and stage breakdowns.
          </CardDescription>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[11px] select-none">
            <thead>
              <tr className="border-b border-zinc-800/50 bg-zinc-950/20 text-zinc-400 font-medium">
                <th className="p-3">Query</th>
                <th className="p-3">Agent</th>
                <th className="p-3 text-right">RAG Hits</th>
                <th className="p-3 text-right">Rerank Size</th>
                <th className="p-3 text-right">Latency</th>
                <th className="p-3 text-right">Tokens</th>
                <th className="p-3 text-right">Cost</th>
                <th className="p-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/30">
              {recentLogs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-zinc-500 font-medium">
                    No logged telemetry. Run queries in the chat tab.
                  </td>
                </tr>
              ) : (
                recentLogs.slice(0, 15).reverse().map((log: any, index: number) => (
                  <tr key={index} className="hover:bg-zinc-800/10 transition-colors">
                    <td className="p-3 font-medium text-zinc-200 truncate max-w-[150px]" title={log.query}>
                      "{log.query}"
                    </td>
                    <td className="p-3 uppercase font-semibold text-primary">{log.agent_type}</td>
                    <td className="p-3 text-right font-mono text-zinc-300">{log.num_retrieved}</td>
                    <td className="p-3 text-right font-mono text-zinc-300">{log.num_reranked}</td>
                    <td className="p-3 text-right font-mono font-medium text-zinc-200">
                      {log.total_latency_ms?.toFixed(0)} ms
                    </td>
                    <td className="p-3 text-right font-mono text-zinc-400">{log.total_tokens}</td>
                    <td className="p-3 text-right font-mono text-emerald-400 font-medium">
                      ${log.cost_usd?.toFixed(5)}
                    </td>
                    <td className="p-3 text-zinc-500">{formatDateTime(log.timestamp)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
