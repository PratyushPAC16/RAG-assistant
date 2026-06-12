"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Cpu,
  Clock,
  Coins,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Play,
  Trash2,
  History,
  Sparkles,
  ChevronDown,
  ChevronUp,
  FileCode,
  Check,
  TrendingUp,
  ShieldCheck,
  Zap,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { BenchmarkRun, BenchmarkProviderResult } from "@/types";

export default function BenchmarksPage() {
  const [query, setQuery] = useState("Explain vector database indexing and how semantic retrieval differs from keyword-based search.");
  const [useRag, setUseRag] = useState(true);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [activeRun, setActiveRun] = useState<BenchmarkRun | null>(null);
  const [history, setHistory] = useState<BenchmarkRun[]>([]);
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load history and default active run on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await api.getBenchmarkHistory(30);
      setHistory(res.runs || []);
      // If there's history and no active run yet, load the latest run
      if (res.runs && res.runs.length > 0 && !activeRun) {
        setActiveRun(res.runs[0]);
      }
    } catch (err: any) {
      console.error("Failed to fetch benchmark history:", err);
    }
  };

  const handleRunBenchmark = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isBenchmarking) return;

    setIsBenchmarking(true);
    setErrorMsg(null);
    setExpandedProvider(null);

    try {
      const run = await api.runBenchmark(query, useRag);
      setActiveRun(run);
      await fetchHistory();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute benchmark query.");
    } finally {
      setIsBenchmarking(false);
    }
  };

  const handleClearHistory = async () => {
    if (!confirm("Are you sure you want to clear all historical benchmark runs?")) return;
    try {
      await api.clearBenchmarkHistory();
      setHistory([]);
      setActiveRun(null);
    } catch (err: any) {
      console.error("Failed to clear benchmark history:", err);
    }
  };

  // Process provider lists from active run
  const providers = activeRun
    ? Object.entries(activeRun.results).map(([providerName, res]) => ({
        provider: providerName,
        model: res.model,
        latency: res.latency_s,
        promptTokens: res.prompt_tokens,
        completionTokens: res.completion_tokens,
        totalTokens: res.total_tokens,
        cost: res.cost_usd,
        length: res.response_length_chars,
        quality: res.composite_score,
        reasoning: res.evaluation_reasoning,
        response: res.response,
        citations: res.citations,
        error: res.error,
      }))
    : [];

  // Sort providers by rank (composite score desc, then latency asc for tie-break)
  const rankedProviders = [...providers]
    .filter(p => !p.error)
    .sort((a, b) => {
      if (b.quality !== a.quality) return b.quality - a.quality;
      return a.latency - b.latency;
    });

  // Identify top-performing providers
  const fastestProvider = [...providers]
    .filter(p => !p.error)
    .sort((a, b) => a.latency - b.latency)[0]?.provider;

  const cheapestProvider = [...providers]
    .filter(p => !p.error)
    .sort((a, b) => a.cost - b.cost)[0]?.provider;

  const highestQualityProvider = [...providers]
    .filter(p => !p.error)
    .sort((a, b) => b.quality - a.quality)[0]?.provider;

  // Visual medal mapping
  const getRankBadge = (idx: number) => {
    if (idx === 0) return "🥇 1st";
    if (idx === 1) return "🥈 2nd";
    if (idx === 2) return "🥉 3rd";
    return `${idx + 1}th`;
  };

  // Charts processing
  const latencyChartData = providers.map(p => ({
    name: p.provider.toUpperCase(),
    Latency: p.error ? 0 : parseFloat(p.latency.toFixed(2)),
  }));

  const tokenChartData = providers.map(p => ({
    name: p.provider.toUpperCase(),
    Input: p.error ? 0 : p.promptTokens,
    Output: p.error ? 0 : p.completionTokens,
  }));

  const efficiencyChartData = providers.map(p => ({
    name: p.provider.toUpperCase(),
    Quality: p.error ? 0 : parseFloat((p.quality * 10).toFixed(0)), // scale 0-10 to 0-100
    Cost: p.error ? 0 : parseFloat((p.cost * 1000).toFixed(4)), // cost per 1K tokens
  }));

  // Historical trend processing
  const historyTrendData = [...history]
    .reverse()
    .map(h => {
      const date = new Date(h.timestamp);
      const formattedDate = `${date.getMonth() + 1}/${date.getDate()}`;
      
      const entry: Record<string, any> = { date: formattedDate };
      Object.entries(h.results).forEach(([prov, res]) => {
        if (!res.error) {
          entry[prov] = parseFloat(res.latency_s.toFixed(2));
        }
      });
      return entry;
    });

  // Stagger animation definitions
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 25 } },
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-8 select-none bg-zinc-950/20">
      {/* Title Header */}
      <div className="border-b border-zinc-900 pb-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Cpu className="w-8 h-8 text-primary shrink-0 animate-pulse" />
            Provider Benchmark Center
          </h1>
          <p className="text-zinc-500 text-xs mt-1 leading-relaxed">
            Trigger parallel tests across local and cloud API providers (Ollama, Groq, Gemini) to measure response times, input costs, and quality scores.
          </p>
        </div>

        {history.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearHistory}
            className="border-zinc-900 hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/20 text-zinc-500 font-bold transition-all text-xs"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1" />
            Clear History
          </Button>
        )}
      </div>

      {/* Trigger & Loader Box */}
      <Card className="glass-panel border-zinc-900 overflow-hidden relative shadow-2xl">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-violet-600 via-primary to-violet-600" />
        <CardContent className="pt-6">
          <form onSubmit={handleRunBenchmark} className="space-y-4">
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-bold font-mono text-zinc-500 uppercase tracking-wider">
                Benchmark Testing Query
              </label>
              <textarea
                rows={2}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isBenchmarking}
                placeholder="Type benchmark prompt..."
                className="w-full bg-zinc-900/40 dark:bg-zinc-950/40 border border-zinc-850 focus:border-primary/50 rounded-xl px-4 py-3 text-xs focus:outline-none focus:ring-1 focus:ring-primary/30 shadow-inner resize-none text-zinc-200 placeholder-zinc-650"
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
              <div className="flex items-center gap-4 text-xs">
                <label className="flex items-center gap-1.5 text-zinc-450 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={useRag}
                    onChange={(e) => setUseRag(e.target.checked)}
                    disabled={isBenchmarking}
                    className="rounded border-zinc-800 bg-zinc-950 text-primary focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5"
                  />
                  <span className="font-semibold text-zinc-400">Apply RAG Context</span>
                </label>
              </div>

              <Button
                type="submit"
                variant="primary"
                className="px-8 font-bold text-xs bg-gradient-to-r from-violet-600 to-indigo-500 hover:from-violet-500 hover:to-indigo-400 text-zinc-100 border-0 shadow-lg shadow-violet-600/10 hover:shadow-violet-600/20 py-3.5 h-auto rounded-lg"
                disabled={!query.trim() || isBenchmarking}
                loading={isBenchmarking}
              >
                <Play className="w-3.5 h-3.5 mr-1 text-zinc-300" />
                Simultaneous Benchmark Loop
              </Button>
            </div>
          </form>

          {/* Running Stepper Status */}
          <AnimatePresence>
            {isBenchmarking && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-6 border-t border-zinc-900/60 pt-5 space-y-4"
              >
                <div className="flex items-center justify-between text-[10px] font-mono text-zinc-550 uppercase tracking-widest">
                  <span>Simultaneous Thread Diagnostics</span>
                  <span className="animate-pulse text-primary font-bold">Querying Endpoints...</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {[
                    { name: "Ollama", desc: "Polling local Llama3 server...", col: "border-emerald-500/25 bg-emerald-500/5 text-emerald-400" },
                    { name: "Groq", desc: "Querying cloud API client...", col: "border-orange-500/25 bg-orange-500/5 text-orange-400" },
                    { name: "Gemini", desc: "Calling Google LLM vertex...", col: "border-violet-500/25 bg-violet-500/5 text-violet-400" },
                  ].map((p, i) => (
                    <div key={i} className={cn("p-3 rounded-lg border flex items-center gap-3", p.col)}>
                      <div className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />
                      <div className="min-w-0 font-mono text-[10px]">
                        <div className="font-bold uppercase tracking-wider">{p.name}</div>
                        <div className="text-zinc-500 mt-0.5 truncate">{p.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {errorMsg && (
            <div className="p-3.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-[11px] text-rose-450 flex items-start gap-2 max-w-lg mx-auto mt-4 select-text">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Results View */}
      {activeRun && (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-8"
        >
          {/* Active Run Subtitle */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-zinc-950/40 border border-zinc-900 px-5 py-4 rounded-2xl backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                <ShieldCheck className="w-4.5 h-4.5 text-primary" />
              </div>
              <div className="text-[11px] font-mono select-text">
                <span className="text-zinc-500 uppercase tracking-wider font-bold">Run Prompt: </span>
                <span className="font-bold text-zinc-350">"{activeRun.query}"</span>
              </div>
            </div>
            
            <div className="text-[10px] font-mono text-zinc-500 shrink-0">
              {new Date(activeRun.timestamp).toLocaleTimeString()}
            </div>
          </div>

          {/* 1. Levels.fyi-style Leaderboard */}
          <motion.div variants={itemVariants}>
            <Card className="glass-panel border-zinc-900/60 overflow-hidden relative">
              <CardHeader className="border-b border-zinc-900 pb-3 bg-zinc-950/20">
                <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">
                  Performance Leaderboard
                </CardTitle>
                <CardDescription className="text-zinc-500 text-[10px] font-medium leading-relaxed">
                  Providers ranked dynamically based on quality, latency, and token cost balance.
                </CardDescription>
              </CardHeader>
              <div className="overflow-x-auto select-text">
                <table className="w-full text-left border-collapse text-[11px] font-mono">
                  <thead>
                    <tr className="border-b border-zinc-900/60 bg-zinc-950/10 text-zinc-500 font-bold uppercase tracking-wider text-[9px]">
                      <th className="p-4 pl-6">Rank</th>
                      <th className="p-4">Provider</th>
                      <th className="p-4">Model Used</th>
                      <th className="p-4 text-right">Latency</th>
                      <th className="p-4 text-right">Estimated Cost</th>
                      <th className="p-4 text-right">Output Length</th>
                      <th className="p-4 text-right">Quality Score</th>
                      <th className="p-4 pr-6 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/40">
                    {providers.map((p, index) => {
                      const rankIndex = rankedProviders.findIndex(rp => rp.provider === p.provider);
                      const isOnline = !p.error;

                      return (
                        <tr
                          key={p.provider}
                          className={cn(
                            "hover:bg-zinc-900/20 transition-colors cursor-pointer",
                            !isOnline && "opacity-55"
                          )}
                          onClick={() => setExpandedProvider(expandedProvider === p.provider ? null : p.provider)}
                        >
                          <td className="p-4 pl-6 font-bold text-zinc-300">
                            {isOnline ? getRankBadge(rankIndex) : "--"}
                          </td>
                          <td className="p-4">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-zinc-200 uppercase tracking-wide">{p.provider}</span>
                              {isOnline && p.provider === fastestProvider && (
                                <span className="text-[8px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded font-bold uppercase">🥇 Fastest</span>
                              )}
                              {isOnline && p.provider === cheapestProvider && (
                                <span className="text-[8px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded font-bold uppercase">🥇 Cheapest</span>
                              )}
                            </div>
                          </td>
                          <td className="p-4 text-zinc-400 truncate max-w-[130px]">{p.model.split("/").pop()}</td>
                          <td className="p-4 text-right font-bold text-zinc-200">
                            {isOnline ? `${p.latency.toFixed(2)}s` : "--"}
                          </td>
                          <td className="p-4 text-right text-emerald-400 font-bold">
                            {isOnline ? `$${(p.cost).toFixed(5)}` : "--"}
                          </td>
                          <td className="p-4 text-right text-zinc-450">{isOnline ? `${p.length} chars` : "--"}</td>
                          <td className="p-4 text-right">
                            {isOnline ? (
                              <span className="font-bold text-amber-400 bg-amber-400/5 border border-amber-400/20 px-2 py-0.5 rounded">
                                {(p.quality * 10).toFixed(0)} / 100
                              </span>
                            ) : "--"}
                          </td>
                          <td className="p-4 pr-6 text-center">
                            {isOnline ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                <Check className="w-3 h-3" />
                              </span>
                            ) : (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-rose-500/10 text-rose-450 border border-rose-500/20" title={p.error}>
                                <X className="w-3 h-3" />
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>

          {/* 2. Charts comparison grid (Recharts) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chart 1: Latency */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Response Latency (s)</CardTitle>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="w-full h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={latencyChartData} margin={{ top: 20, right: 10, left: -25, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" />
                        <XAxis dataKey="name" stroke="#55555c" fontSize={9} tickLine={false} />
                        <YAxis stroke="#55555c" fontSize={9} tickLine={false} unit="s" />
                        <Tooltip
                          cursor={{ fill: "rgba(255,255,255,0.02)" }}
                          contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", borderRadius: 8, fontSize: 10, fontFamily: "monospace" }}
                        />
                        <Bar dataKey="Latency" radius={[4, 4, 0, 0]} barSize={35}>
                          {latencyChartData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={
                                entry.name.toLowerCase() === "gemini" ? "#8b5cf6" :
                                entry.name.toLowerCase() === "groq" ? "#f97316" : "#10b981"
                              }
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Chart 2: Token consumption (Stacked) */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Token Allocation (Prompt vs Completion)</CardTitle>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="w-full h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={tokenChartData} margin={{ top: 20, right: 10, left: -20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" />
                        <XAxis dataKey="name" stroke="#55555c" fontSize={9} tickLine={false} />
                        <YAxis stroke="#55555c" fontSize={9} tickLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", borderRadius: 8, fontSize: 10, fontFamily: "monospace" }}
                        />
                        <Legend wrapperStyle={{ fontSize: 9 }} />
                        <Bar dataKey="Input" stackId="a" fill="#1e3a8a" radius={[0, 0, 0, 0]} barSize={35} />
                        <Bar dataKey="Output" stackId="a" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={35} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Chart 3: Quality vs Cost */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Quality vs Cost per 1K Tokens</CardTitle>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="w-full h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={efficiencyChartData} margin={{ top: 20, right: 10, left: -20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" />
                        <XAxis dataKey="name" stroke="#55555c" fontSize={9} tickLine={false} />
                        <YAxis yAxisId="left" stroke="#8884d8" fontSize={9} orientation="left" />
                        <YAxis yAxisId="right" stroke="#82ca9d" fontSize={9} orientation="right" unit="¢" />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", borderRadius: 8, fontSize: 10, fontFamily: "monospace" }}
                        />
                        <Legend wrapperStyle={{ fontSize: 9 }} />
                        <Bar yAxisId="left" dataKey="Quality" fill="#f59e0b" name="Quality Score (0-100)" barSize={20} radius={[4, 4, 0, 0]} />
                        <Bar yAxisId="right" dataKey="Cost" fill="#10b981" name="Cost per 1K tok (¢)" barSize={20} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Chart 4: Historical Run Trends */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Historical Response Trends (Latency s)</CardTitle>
                </CardHeader>
                <CardContent className="pt-2">
                  {historyTrendData.length === 0 ? (
                    <div className="w-full h-[220px] flex items-center justify-center text-zinc-650 text-xs">
                      Awaiting multiple historical runs to plot trends.
                    </div>
                  ) : (
                    <div className="w-full h-[220px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={historyTrendData} margin={{ top: 15, right: 20, left: -25, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" />
                          <XAxis dataKey="date" stroke="#55555c" fontSize={9} tickLine={false} />
                          <YAxis stroke="#55555c" fontSize={9} tickLine={false} unit="s" />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", borderRadius: 8, fontSize: 10, fontFamily: "monospace" }}
                          />
                          <Legend wrapperStyle={{ fontSize: 9 }} />
                          <Line type="monotone" dataKey="gemini" stroke="#8b5cf6" activeDot={{ r: 5 }} strokeWidth={2} name="Gemini" connectNulls />
                          <Line type="monotone" dataKey="groq" stroke="#f97316" activeDot={{ r: 5 }} strokeWidth={2} name="Groq" connectNulls />
                          <Line type="monotone" dataKey="ollama" stroke="#10b981" activeDot={{ r: 5 }} strokeWidth={2} name="Ollama" connectNulls />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* 3. Detailed response accordion blocks */}
          <div className="space-y-4">
            <div className="text-[10px] font-bold font-mono text-zinc-500 uppercase tracking-widest pl-1">
              Detailed Provider Evaluations
            </div>
            
            {providers.map((p) => {
              const isExpanded = expandedProvider === p.provider;
              const isOnline = !p.error;

              return (
                <motion.div key={p.provider} variants={itemVariants}>
                  <Card
                    className={cn(
                      "glass-panel border-zinc-900/60 overflow-hidden transition-all duration-300",
                      isExpanded ? "border-primary/20 shadow-lg shadow-primary/5" : "hover:border-zinc-800"
                    )}
                  >
                    {/* Header trigger bar */}
                    <div
                      onClick={() => setExpandedProvider(isExpanded ? null : p.provider)}
                      className="p-4 flex items-center justify-between cursor-pointer select-none bg-zinc-950/10 hover:bg-zinc-950/20"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{
                          backgroundColor:
                            p.provider.toLowerCase() === "gemini" ? "#8b5cf6" :
                            p.provider.toLowerCase() === "groq" ? "#f97316" : "#10b981"
                        }} />
                        <div>
                          <span className="text-xs font-bold text-zinc-250 uppercase tracking-wide">{p.provider}</span>
                          <span className="text-[10px] text-zinc-550 font-mono ml-2">({p.model.split("/").pop()})</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 text-[10px] font-mono text-zinc-500">
                        {isOnline ? (
                          <>
                            <span>Latency: <strong className="text-zinc-350">{p.latency.toFixed(2)}s</strong></span>
                            <span className="hidden sm:inline">Cost: <strong className="text-emerald-450">${p.cost.toFixed(5)}</strong></span>
                            <span>Score: <strong className="text-amber-400">{(p.quality * 10).toFixed(0)}%</strong></span>
                          </>
                        ) : (
                          <span className="text-rose-400 font-bold uppercase tracking-wider bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">Offline / Error</span>
                        )}
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-zinc-500" /> : <ChevronDown className="w-4 h-4 text-zinc-500" />}
                      </div>
                    </div>

                    {/* Collapsible panel body */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.25, ease: "easeInOut" }}
                          className="overflow-hidden border-t border-zinc-900/60"
                        >
                          <div className="p-5 space-y-6">
                            {/* Evaluation reasoning text */}
                            {isOnline && p.reasoning && (
                              <div className="p-4 rounded-xl bg-amber-400/5 border border-amber-400/15 text-xs select-text">
                                <div className="flex items-center gap-1.5 text-amber-400 font-bold mb-1.5 text-[10px] uppercase tracking-wider">
                                  <Sparkles className="w-4 h-4" />
                                  Orchestrator Quality Evaluation
                                </div>
                                <p className="text-zinc-350 leading-relaxed italic">
                                  "{p.reasoning}"
                                </p>
                              </div>
                            )}

                            {/* Response content details */}
                            <div className="space-y-2 select-text">
                              <div className="text-[10px] font-bold font-mono text-zinc-550 uppercase tracking-widest flex items-center gap-1.5">
                                <FileCode className="w-4 h-4 text-zinc-650" />
                                Raw Model Response
                              </div>
                              <div className="rounded-xl border border-zinc-900 bg-zinc-950 p-4 max-h-72 overflow-y-auto font-mono text-[11px] text-zinc-300 leading-relaxed custom-scrollbar whitespace-pre-wrap select-all cursor-text">
                                {isOnline ? p.response : `ERROR DIAGNOSTICS:\n${p.error}`}
                              </div>
                            </div>

                            {/* Citations used if present */}
                            {isOnline && p.citations && p.citations.length > 0 && (
                              <div className="space-y-2 select-text">
                                <div className="text-[10px] font-bold font-mono text-zinc-550 uppercase tracking-widest flex items-center gap-1.5">
                                  <FileText className="w-4 h-4 text-zinc-650" />
                                  Citations Context ({p.citations.length})
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  {p.citations.map((c, ci) => (
                                    <span
                                      key={ci}
                                      className="text-[9px] font-bold font-mono px-2 py-0.5 border border-zinc-850 bg-zinc-900/40 text-zinc-450 rounded"
                                    >
                                      📄 {c}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* 4. History log of runs */}
          <motion.div variants={itemVariants}>
            <Card className="glass-panel border-zinc-900/60 overflow-hidden relative">
              <CardHeader className="border-b border-zinc-900/60 pb-3.5 bg-zinc-950/20">
                <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-450 flex items-center gap-1.5">
                  <History className="w-4 h-4 text-zinc-650" />
                  Historical Benchmark Runs ({history.length})
                </CardTitle>
                <CardDescription className="text-zinc-500 text-[10px] font-medium leading-relaxed">
                  Select previous parallel benchmark runs to load historical stats.
                </CardDescription>
              </CardHeader>
              <div className="max-h-60 overflow-y-auto custom-scrollbar">
                <table className="w-full text-left border-collapse text-[10px] font-mono select-text">
                  <thead>
                    <tr className="border-b border-zinc-900/60 bg-zinc-950/10 text-zinc-500 font-bold uppercase tracking-wider text-[8px]">
                      <th className="p-3 pl-5">Timestamp</th>
                      <th className="p-3">Query Prompt</th>
                      <th className="p-3 text-right">Gemini Latency</th>
                      <th className="p-3 text-right">Groq Latency</th>
                      <th className="p-3 text-right">Ollama Latency</th>
                      <th className="p-3 text-right">RAG</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/40">
                    {history.map((run) => {
                      const isActive = activeRun.run_id === run.run_id;
                      return (
                        <tr
                          key={run.run_id}
                          onClick={() => {
                            setActiveRun(run);
                            setExpandedProvider(null);
                          }}
                          className={cn(
                            "hover:bg-zinc-900/10 transition-colors cursor-pointer text-[10px]",
                            isActive ? "bg-primary/5 text-zinc-200 border-l-[2px] border-primary" : "text-zinc-450"
                          )}
                        >
                          <td className="p-3 pl-5">{new Date(run.timestamp).toLocaleString()}</td>
                          <td className="p-3 truncate max-w-[200px]" title={run.query}>"{run.query}"</td>
                          <td className="p-3 text-right font-bold">
                            {run.results.gemini?.error ? "Error" : `${run.results.gemini?.latency_s?.toFixed(2)}s`}
                          </td>
                          <td className="p-3 text-right font-bold">
                            {run.results.groq?.error ? "Error" : `${run.results.groq?.latency_s?.toFixed(2)}s`}
                          </td>
                          <td className="p-3 text-right font-bold">
                            {run.results.ollama?.error ? "Error" : `${run.results.ollama?.latency_s?.toFixed(2)}s`}
                          </td>
                          <td className="p-3 text-right">
                            <span className={cn("text-[8px] font-bold px-1.5 py-0.5 rounded",
                              run.use_rag ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-zinc-850 text-zinc-500"
                            )}>
                              {run.use_rag ? "RAG" : "Vanilla"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
