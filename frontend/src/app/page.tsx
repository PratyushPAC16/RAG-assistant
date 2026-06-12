"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Activity,
  Cpu,
  Coins,
  Database,
  Search,
  Award,
  TrendingUp,
  UserCheck,
  Layers,
  Globe,
  ChevronRight,
  GraduationCap,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";

export default function LandingPage() {
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.05,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 200, damping: 20 } },
  };

  return (
    <div className="flex-grow overflow-y-auto bg-zinc-950 scroll-smooth custom-scrollbar">
      {/* 1. Header Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-md px-6 lg:px-12 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <span className="text-zinc-50 font-bold text-sm tracking-widest select-none">TM</span>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-zinc-100 text-sm leading-tight tracking-wider select-none">TalentMind AI</span>
            <span className="text-zinc-500 text-[9px] uppercase tracking-widest font-mono font-bold leading-none mt-0.5">Enterprise Agent</span>
          </div>
        </div>

        <nav className="hidden md:flex items-center gap-8 text-xs font-semibold text-zinc-400">
          <a href="#features" className="hover:text-zinc-200 transition-colors">Features</a>
          <a href="#architecture" className="hover:text-zinc-200 transition-colors">Architecture</a>
          <a href="#providers" className="hover:text-zinc-200 transition-colors">Providers</a>
          <a href="#resume" className="hover:text-zinc-200 transition-colors">Resume AI</a>
          <a href="#analytics" className="hover:text-zinc-200 transition-colors">Analytics</a>
        </nav>

        <Link href="/dashboard">
          <Button variant="primary" size="sm" className="bg-zinc-100 text-zinc-950 hover:bg-zinc-200 border-0 font-bold rounded-lg text-xs flex items-center gap-1">
            Launch Console
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </Link>
      </header>

      {/* 2. Hero Section */}
      <section className="relative px-6 lg:px-12 pt-20 pb-24 border-b border-zinc-900 overflow-hidden flex flex-col items-center justify-center text-center">
        {/* Abstract design matrix glow blobs */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[400px] h-[400px] bg-violet-600/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-1/3 left-1/3 w-[300px] h-[300px] bg-amber-400/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f1f23_1px,transparent_1px),linear-gradient(to_bottom,#1f1f23_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-30" />

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="max-w-4xl space-y-6 relative z-10"
        >
          {/* Tagline Announcement Badge */}
          <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-violet-500/25 bg-violet-500/5 text-violet-400 text-[10px] font-mono font-bold uppercase tracking-wider shadow-[0_0_15px_rgba(139,92,246,0.1)]">
            <Sparkles className="w-3 h-3 text-violet-400 animate-pulse" />
            Next-Gen RAG Orchestrator
          </motion.div>

          {/* Title and tagline */}
          <motion.h1 variants={itemVariants} className="text-4xl sm:text-6xl font-bold tracking-tight text-zinc-150 leading-tight">
            Orchestrate Agentic Knowledge <br />
            <span className="bg-gradient-to-r from-amber-400 via-primary to-amber-400 bg-clip-text text-transparent">
              TalentMind AI
            </span>
          </motion.h1>

          <motion.p variants={itemVariants} className="text-zinc-400 text-sm sm:text-base max-w-2xl mx-auto leading-relaxed">
            Enterprise Agentic Knowledge Intelligence Platform. Harness local and cloud LLM execution workflows, long-term memory syncs, and multi-vector search metrics.
          </motion.p>

          {/* Action CTAs */}
          <motion.div variants={itemVariants} className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/chat">
              <Button size="lg" className="w-full sm:w-auto px-8 font-bold text-xs bg-gradient-to-r from-violet-600 to-indigo-500 hover:from-violet-500 hover:to-indigo-400 text-zinc-100 border-0 shadow-lg shadow-violet-600/10 hover:shadow-violet-600/20 py-4 h-auto rounded-lg">
                Enter AI Console
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="lg" variant="outline" className="w-full sm:w-auto px-8 font-bold text-xs border-zinc-850 hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 py-4 h-auto rounded-lg">
                View System Telemetry
              </Button>
            </Link>
          </motion.div>
        </motion.div>

        {/* Dashboard Visual Mock Component */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, type: "spring", stiffness: 100, damping: 18 }}
          className="mt-16 w-full max-w-5xl rounded-2xl border border-zinc-900 bg-zinc-950/60 p-3 shadow-2xl relative z-10 backdrop-blur"
        >
          <div className="absolute -top-10 left-1/2 -translate-x-1/2 w-[500px] h-[100px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
          <div className="w-full rounded-xl border border-zinc-850 bg-zinc-950 overflow-hidden text-left font-sans select-none">
            {/* Mock Header */}
            <div className="border-b border-zinc-900 bg-zinc-950/50 px-4 py-2 flex items-center justify-between text-[10px] text-zinc-500 font-mono">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
                <span className="ml-2 font-bold text-zinc-400">RAG Trace Monitor</span>
              </div>
              <span>Session ID: TM-582a7f</span>
            </div>

            {/* Mock View */}
            <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2 space-y-3">
                <div className="bg-zinc-900/30 border border-zinc-900 p-3 rounded-lg text-xs leading-relaxed">
                  <span className="font-bold text-primary">Query: </span>
                  <span className="text-zinc-300">Extract vector storage limits and latency requirements from standard documentation.</span>
                </div>
                <div className="bg-zinc-900/10 border border-zinc-900 p-3 rounded-lg text-xs leading-relaxed space-y-1.5">
                  <div className="flex justify-between font-mono text-[9px] text-zinc-550 uppercase">
                    <span>Output generated (Gemini)</span>
                    <span className="text-emerald-400">Success</span>
                  </div>
                  <p className="text-zinc-350">Semantic RAG indices leverage cosine similarity vector coordinate matches, filtering top candidates in <strong>85ms</strong>, reducing prompt expenditures.</p>
                </div>
              </div>

              <div className="bg-zinc-900/20 border border-zinc-900 p-3 rounded-lg space-y-3">
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-zinc-500">Node Timings</div>
                <div className="space-y-2 text-[10px] font-mono">
                  {[
                    { label: "Router classification", val: "65ms", w: "40%", col: "bg-blue-400" },
                    { label: "Long-term memory scan", val: "90ms", w: "60%", col: "bg-emerald-400" },
                    { label: "Cosine vector search", val: "180ms", w: "90%", col: "bg-cyan-400" },
                    { label: "Response LLM synthesis", val: "1.2s", w: "100%", col: "bg-violet-400" },
                  ].map((item, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-zinc-400 text-[9px]">
                        <span>{item.label}</span>
                        <span>{item.val}</span>
                      </div>
                      <div className="w-full bg-zinc-950 h-1 rounded-full overflow-hidden">
                        <div className={cn("h-full rounded-full", item.col)} style={{ width: item.w }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* 3. Features Grid Section */}
      <section id="features" className="px-6 lg:px-12 py-24 border-b border-zinc-900">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3">
            <h2 className="text-[10px] uppercase font-bold tracking-widest text-primary font-mono">Core Infrastructure</h2>
            <h3 className="text-2xl sm:text-4xl font-bold tracking-tight text-zinc-200">
              Next-Generation Agentic Core
            </h3>
            <p className="text-zinc-500 text-xs sm:text-sm max-w-xl mx-auto leading-relaxed">
              Every component is modular, structured for low latencies, multi-provider model switches, and high citation coverage.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { title: "Agentic Router", desc: "Performs intent-based classification in 65ms, directing queries dynamically into parallel RAG, Web, or Memory branches.", icon: Compass },
              { title: "Long-Term Memory", desc: "Syncs fact databases to learn user preferences and previous prompt details, personalizing responses without prompt bloat.", icon: Database },
              { title: "Hybrid Search Engine", desc: "Combines dense vector similarity matching (ChromaDB) and sparse text keyword scans (BM25) via Reciprocal Rank Fusion (RRF).", icon: Search },
              { title: "Cross-Encoder Reranker", desc: "Trim retrieved records through semantic rescoring models, filtering out noise and presenting top contexts for synthesis.", icon: Layers },
              { title: "Provider Diagnostic", desc: "Compare local models (Ollama) and cloud APIs (Gemini, Groq) in parallel, capturing latency, token usage, and cost curves.", icon: Cpu },
              { title: "Security & Citations", desc: "Aggregates strict citation markers. Exposes expandable source cards detailing relevant document segments and score matches.", icon: ShieldCheck },
            ].map((f, i) => {
              const Icon = f.icon;
              return (
                <Card key={i} className="glass-panel border-zinc-900 bg-zinc-950/40 hover:border-zinc-850 hover:bg-zinc-900/20 transition-all duration-300 relative group overflow-hidden" glass>
                  <div className="absolute top-0 left-0 w-full h-[1.5px] bg-gradient-to-r from-transparent via-zinc-800 to-transparent group-hover:via-primary/20 transition-all duration-300" />
                  <CardContent className="pt-6 space-y-3">
                    <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-850 flex items-center justify-center text-primary group-hover:scale-105 transition-transform shrink-0">
                      <Icon className="w-5 h-5" />
                    </div>
                    <h4 className="text-sm font-bold text-zinc-200">{f.title}</h4>
                    <p className="text-zinc-500 text-xs leading-relaxed">{f.desc}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. Architecture Overview Section */}
      <section id="architecture" className="px-6 lg:px-12 py-24 border-b border-zinc-900 bg-zinc-950/20 relative">
        <div className="absolute top-1/2 left-1/4 w-[350px] h-[350px] bg-violet-600/5 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-6xl mx-auto space-y-12 relative z-10">
          <div className="text-center space-y-3">
            <h2 className="text-[10px] uppercase font-bold tracking-widest text-primary font-mono">Data Flow</h2>
            <h3 className="text-2xl sm:text-4xl font-bold tracking-tight text-zinc-200">
              Visual Execution Topology
            </h3>
            <p className="text-zinc-500 text-xs sm:text-sm max-w-xl mx-auto leading-relaxed">
              Explore how User queries execute chronologically through the agent graph. Connected by animated edges to illustrate data flow.
            </p>
          </div>

          {/* Timeline Pipeline display */}
          <div className="relative border border-zinc-900 rounded-2xl bg-zinc-950/40 p-6 flex flex-col md:flex-row items-center justify-between gap-6 max-w-5xl mx-auto overflow-x-auto overflow-y-hidden select-none">
            {[
              { step: "1", title: "User Query", desc: "Inits prompt" },
              { step: "2", title: "Router Node", desc: "Intent classification" },
              { step: "3", title: "Memory Sync", desc: "Context facts lookup" },
              { step: "4", title: "Hybrid Search", desc: "Vector + Text search" },
              { step: "5", title: "Reranker", desc: "MiniLM filter" },
              { step: "6", title: "LLM Synthesizer", desc: "Response generated" },
            ].map((s, idx) => (
              <React.Fragment key={idx}>
                <div className="w-36 text-center space-y-2 shrink-0">
                  <div className="w-8 h-8 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto text-xs font-mono font-bold text-zinc-400 group hover:border-primary transition-colors">
                    {s.step}
                  </div>
                  <h4 className="text-[11px] font-bold text-zinc-250 uppercase tracking-wide leading-none">{s.title}</h4>
                  <p className="text-[9px] text-zinc-550 font-mono leading-none">{s.desc}</p>
                </div>
                {idx < 5 && (
                  <ArrowRight className="w-4 h-4 text-zinc-800 hidden md:block shrink-0" />
                )}
              </React.Fragment>
            ))}
          </div>

          <div className="flex justify-center pt-2">
            <Link href="/workflow">
              <Button size="sm" variant="outline" className="border-zinc-900 hover:bg-zinc-900 text-xs font-bold text-zinc-400 hover:text-zinc-200 px-5 py-3 h-auto">
                Explore Interactive Canvas
                <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* 5. Provider Support Section */}
      <section id="providers" className="px-6 lg:px-12 py-24 border-b border-zinc-900">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3">
            <h2 className="text-[10px] uppercase font-bold tracking-widest text-primary font-mono">Multi-Model Support</h2>
            <h3 className="text-2xl sm:text-4xl font-bold tracking-tight text-zinc-200">
              Provider Agnostic Orchestration
            </h3>
            <p className="text-zinc-500 text-xs sm:text-sm max-w-xl mx-auto leading-relaxed">
              Dynamically swap local models with cloud APIs. Run simultaneous checks to rank cost vs quality performance.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { name: "Ollama", desc: "Local offline LLM hosting.", model: "Llama 3.2", badge: "🟢 Local Engine", col: "border-emerald-500/20 bg-emerald-500/5 text-emerald-400", details: "Zero API cost, fully secure." },
              { name: "Groq", desc: "Cloud server LPU acceleration.", model: "Llama 3 70B", badge: "🟠 Low Latency", col: "border-orange-500/20 bg-orange-500/5 text-orange-400", details: "Average latency under 200ms." },
              { name: "Gemini", desc: "Advanced Google LLM reasoning.", model: "Gemini 1.5 Flash", badge: "🟣 High Reasoning", col: "border-violet-500/20 bg-violet-500/5 text-violet-400", details: "Excellent logic, citation quality." },
            ].map((p, i) => (
              <Card key={i} className="glass-panel border-zinc-900 bg-zinc-950/40 relative group overflow-hidden" glass>
                <div className="absolute top-0 left-0 w-full h-[1.5px] bg-gradient-to-r from-transparent via-zinc-800 to-transparent group-hover:via-primary/20 transition-all duration-300" />
                <CardContent className="pt-6 space-y-4 text-center">
                  <span className={cn("inline-flex text-[9px] font-bold font-mono px-2 py-0.5 rounded border tracking-wide uppercase", p.col)}>
                    {p.badge}
                  </span>
                  <div className="space-y-1">
                    <h4 className="text-lg font-bold text-zinc-200 uppercase tracking-wider">{p.name}</h4>
                    <p className="text-[10px] text-zinc-500 font-mono">{p.model}</p>
                  </div>
                  <p className="text-zinc-400 text-xs leading-relaxed">{p.desc}</p>
                  <div className="border-t border-zinc-900 pt-3 text-[10px] font-mono text-zinc-500">
                    {p.details}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="flex justify-center pt-2">
            <Link href="/benchmarks">
              <Button size="sm" variant="outline" className="border-zinc-900 hover:bg-zinc-900 text-xs font-bold text-zinc-400 hover:text-zinc-200 px-5 py-3 h-auto">
                Open Benchmark Center
                <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* 6. Resume Intelligence Section */}
      <section id="resume" className="px-6 lg:px-12 py-24 border-b border-zinc-900 bg-zinc-950/20 relative">
        <div className="absolute top-1/3 left-2/3 w-[350px] h-[350px] bg-amber-400/5 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center relative z-10">
          <div className="space-y-6">
            <div className="space-y-3">
              <h2 className="text-[10px] uppercase font-bold tracking-widest text-amber-400 font-mono font-bold">ATS Scanners</h2>
              <h3 className="text-2xl sm:text-4xl font-bold tracking-tight text-zinc-200">
                Premium Resume Intelligence
              </h3>
              <p className="text-zinc-400 text-xs sm:text-sm leading-relaxed">
                Scan candidate resumes side-by-side against job description parameters. Extracted matching shapes, missing technologies, interview readiness gauges, and step-by-step roadmaps.
              </p>
            </div>

            <div className="space-y-3.5">
              {[
                { label: "Levels.fyi-style credential match tables" },
                { label: "Recharts Competency Radar match shape" },
                { label: "Staggered skill gap diagnostics matched vs missing" },
                { label: "Actionable roadmap steps to optimize candidate prep" },
              ].map((item, idx) => (
                <div key={idx} className="flex items-center gap-3 text-xs text-zinc-350">
                  <div className="w-5 h-5 rounded-full bg-amber-400/10 border border-amber-400/20 flex items-center justify-center shrink-0">
                    <Check className="w-3 h-3 text-amber-400" />
                  </div>
                  <span>{item.label}</span>
                </div>
              ))}
            </div>

            <div className="pt-2">
              <Link href="/resume">
                <Button size="sm" className="bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-zinc-950 border-0 font-bold rounded-lg text-xs px-5 py-3 h-auto">
                  Run ATS Scanner
                  <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </Link>
            </div>
          </div>

          {/* Visual Diagram Representation */}
          <div className="rounded-2xl border border-zinc-900 bg-zinc-950/80 p-5 space-y-4 shadow-xl select-none font-mono text-[10px] text-zinc-550 border-zinc-850/60 backdrop-blur">
            <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
              <span className="font-bold text-zinc-350 flex items-center gap-1.5 uppercase tracking-wider">
                <GraduationCap className="w-4 h-4 text-cyan-400" />
                Candidate Score Sheet
              </span>
              <span className="text-amber-400 font-bold bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/20">85% Match</span>
            </div>

            <div className="space-y-3.5">
              {[
                { label: "Technical Skills Alignment", val: "80%" },
                { label: "Project Narrative Overlaps", val: "75%" },
                { label: "Degree Prerequisites Checked", val: "100%" },
                { label: "Interview Readiness Gauge", val: "90%" },
              ].map((bar, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between">
                    <span>{bar.label}</span>
                    <span className="text-zinc-300 font-bold">{bar.val}</span>
                  </div>
                  <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-amber-400 h-full rounded-full" style={{ width: bar.val }} />
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-zinc-900 text-center flex flex-col items-center justify-center gap-1">
              <div className="text-zinc-500 uppercase tracking-widest text-[8px] font-bold">Preparation Roadmap generated</div>
              <div className="text-[10px] text-zinc-350 font-bold">Focus: Add ChromaDB & study LangGraph.</div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Analytics Section */}
      <section id="analytics" className="px-6 lg:px-12 py-24 border-b border-zinc-900">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3">
            <h2 className="text-[10px] uppercase font-bold tracking-widest text-primary font-mono">System Metrics</h2>
            <h3 className="text-2xl sm:text-4xl font-bold tracking-tight text-zinc-200">
              Cost & Latency Audits
            </h3>
            <p className="text-zinc-500 text-xs sm:text-sm max-w-xl mx-auto leading-relaxed">
              Track daily query volumes, detailed token payloads (prompt vs completion), and estimated expenditures.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { label: "Average Latency Tracker", val: "ms Tickers", desc: "Splits timing metric indicators across retrieval, reranker, and synthesis nodes in detail.", icon: Clock },
              { label: "Expenditure Calculations", val: "$ Estimations", desc: "Estimates cloud provider fees per query run automatically, tracking token sizes.", icon: Coins },
              { label: "Telemetry Log Records", val: "Recent Activity", desc: "Table logs tracking search hits, model names, query counts, and accurate latency stamps.", icon: TrendingUp },
            ].map((item, idx) => {
              const Icon = item.icon;
              return (
                <Card key={idx} className="glass-panel border-zinc-900 bg-zinc-950/40 relative group overflow-hidden" glass>
                  <div className="absolute top-0 left-0 w-full h-[1.5px] bg-gradient-to-r from-transparent via-zinc-800 to-transparent group-hover:via-primary/20 transition-all duration-300" />
                  <CardContent className="pt-6 space-y-3 text-center">
                    <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-850 flex items-center justify-center text-primary mx-auto group-hover:scale-105 transition-transform shrink-0">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="space-y-0.5">
                      <h4 className="text-xs font-bold text-zinc-200">{item.label}</h4>
                      <span className="text-[9px] text-zinc-500 font-mono font-bold uppercase">{item.val}</span>
                    </div>
                    <p className="text-zinc-500 text-xs leading-relaxed">{item.desc}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="flex justify-center pt-2">
            <Link href="/analytics">
              <Button size="sm" variant="outline" className="border-zinc-900 hover:bg-zinc-900 text-xs font-bold text-zinc-400 hover:text-zinc-200 px-5 py-3 h-auto">
                Open Analytics Panel
                <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* 8. Footer Section */}
      <footer className="px-6 lg:px-12 py-16 bg-zinc-950 text-zinc-500 border-t border-zinc-900 text-xs font-medium">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Col */}
          <div className="space-y-3 md:col-span-1">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center shrink-0">
                <span className="text-zinc-50 font-bold text-[10px] tracking-widest select-none">TM</span>
              </div>
              <span className="font-bold text-zinc-300 select-none">TalentMind AI</span>
            </div>
            <p className="text-[11px] text-zinc-600 leading-relaxed">
              Enterprise Agentic Knowledge Intelligence Platform. RAG workflows, preference memory, and multi-model benchmarking.
            </p>
          </div>

          {/* Links Col 1: Platform */}
          <div className="space-y-3">
            <h4 className="text-[10px] uppercase font-bold text-zinc-400 tracking-widest font-mono">AI Platform</h4>
            <div className="flex flex-col gap-2 font-mono text-[10px]">
              <Link href="/chat" className="hover:text-zinc-300 transition-colors">AI Chat Loop</Link>
              <Link href="/documents" className="hover:text-zinc-300 transition-colors">Vector Files Upload</Link>
              <Link href="/resume" className="hover:text-zinc-300 transition-colors">ATS Resume Matcher</Link>
              <Link href="/workflow" className="hover:text-zinc-300 transition-colors">React Flow Architecture</Link>
            </div>
          </div>

          {/* Links Col 2: Diagnostics */}
          <div className="space-y-3">
            <h4 className="text-[10px] uppercase font-bold text-zinc-400 tracking-widest font-mono">Telemetry</h4>
            <div className="flex flex-col gap-2 font-mono text-[10px]">
              <Link href="/dashboard" className="hover:text-zinc-300 transition-colors">TalentMind AI Dashboard</Link>
              <Link href="/analytics" className="hover:text-zinc-300 transition-colors">Extended Analytics</Link>
              <Link href="/benchmarks" className="hover:text-zinc-300 transition-colors">Provider Benchmarks</Link>
              <Link href="/settings" className="hover:text-zinc-300 transition-colors">Backend Settings</Link>
            </div>
          </div>

          {/* Copyright Info */}
          <div className="space-y-3 md:col-span-1 flex flex-col justify-between">
            <div className="text-[10px] font-mono text-zinc-650">
              System: Connected <br />
              Node Version: v20.17.9 <br />
              Next.js Version: 15.1.0
            </div>
            <div className="text-[10px] text-zinc-600 pt-4 md:pt-0">
              © 2026 TalentMind AI. <br /> All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
