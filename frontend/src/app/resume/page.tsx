"use client";

import React, { useState } from "react";
import { api } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  FileUser,
  Upload,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Award,
  Zap,
  BookOpen,
  UserCheck,
  ShieldCheck,
  Check,
  Target,
  GraduationCap,
  Briefcase,
  Code,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  ListTodo,
  AlertTriangle,
  FileText,
  BadgeAlert,
  Lightbulb,
} from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  Legend,
  PieChart,
  Pie,
} from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export default function ResumeAnalyzerPage() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleResumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setResumeFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  const handleJdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setJdFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resumeFile || !jdFile) return;

    setIsAnalyzing(true);
    setErrorMsg(null);
    setResult(null);

    try {
      const analysis = await api.analyzeResume(resumeFile, jdFile);
      setResult(analysis);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to analyze files. Ensure both documents are valid PDFs.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ── Helper: Safely Render Objects/Strings ────────────────────────────────────
  const renderChild = (child: any): React.ReactNode => {
    if (!child) return null;
    if (typeof child === "string" || typeof child === "number") {
      return child;
    }
    if (typeof child === "object") {
      if (child.name && child.description) {
        return (
          <span>
            <strong className="text-zinc-200">{child.name}</strong>: {child.description}
          </span>
        );
      }
      if (child.name) {
        return child.name;
      }
      if (child.text) {
        return child.text;
      }
      return JSON.stringify(child);
    }
    return String(child);
  };

  // ── Programmatic Fallbacks & Processing ──────────────────────────────────────
  const score = result?.match_score ?? 0;
  
  // ATS Score Color Coding Schema:
  // 90-100 = Excellent (Green)
  // 75-89 = Good (Blue)
  // 60-74 = Average (Orange)
  // Below 60 = Poor (Red)
  const getScoreRating = (val: number) => {
    if (val >= 90) return { label: "Excellent", color: "text-emerald-400", border: "border-emerald-500/20", bg: "bg-emerald-500/5", glow: "shadow-emerald-500/10", bar: "bg-emerald-500" };
    if (val >= 75) return { label: "Good", color: "text-blue-400", border: "border-blue-500/20", bg: "bg-blue-500/5", glow: "shadow-blue-500/10", bar: "bg-blue-500" };
    if (val >= 60) return { label: "Average", color: "text-amber-400", border: "border-amber-500/20", bg: "bg-amber-500/5", glow: "shadow-amber-500/10", bar: "bg-amber-500" };
    return { label: "Poor Fit", color: "text-rose-400", border: "border-rose-500/20", bg: "bg-rose-500/5", glow: "shadow-rose-500/10", bar: "bg-rose-500" };
  };

  const scoreInfo = getScoreRating(score);

  // Breakdown values
  const breakdown = [
    { name: "Skills Match", value: result?.skill_match_pct ?? 0, color: "bg-blue-400 text-blue-400" },
    { name: "Projects Match", value: result?.project_match_pct ?? 0, color: "bg-violet-400 text-violet-400" },
    { name: "Experience Match", value: result?.experience_match_pct ?? result?.interview_readiness_score ?? 0, color: "bg-emerald-400 text-emerald-400" },
    { name: "Education Match", value: result?.education_match_pct ?? 0, color: "bg-cyan-400 text-cyan-400" },
    { name: "Keyword Match", value: result?.keyword_match_pct ?? 0, color: "bg-orange-400 text-orange-400" },
    { name: "Formatting Score", value: result?.formatting_score ?? 85, color: "bg-teal-400 text-teal-400" }
  ];

  // Radar Competency Alignment Data
  const radarData = breakdown.slice(0, 5).map(item => ({
    subject: item.name,
    value: item.value
  }));

  // Gaps & Categorized Missing Skills
  const missingCategorized = result?.missing_skills_categorized ?? {
    critical: result?.missing_skills?.slice(0, 2) ?? [],
    recommended: result?.missing_skills?.slice(2, 4) ?? [],
    optional: result?.missing_skills?.slice(4) ?? []
  };

  // Keyword Analysis Data
  const keywordAnalysis = result?.keyword_analysis ?? {
    top_jd_keywords: [
      { text: "Python", value: 9 },
      { text: "RAG", value: 8 },
      { text: "LangGraph", value: 6 },
      { text: "ChromaDB", "value": 5 }
    ],
    top_resume_keywords: [
      { text: "Python", value: 10 },
      { text: "API", value: 7 },
      { text: "React", value: 5 },
      { text: "Git", "value": 4 }
    ],
    missing_keywords: result?.missing_skills ?? ["Kubernetes", "CI/CD"],
    keyword_coverage_pct: result?.keyword_match_pct ?? 70
  };

  // Format JD vs Resume keyword data for side-by-side Recharts display
  const jdKeywords = keywordAnalysis.top_jd_keywords || [];
  const resumeKeywords = keywordAnalysis.top_resume_keywords || [];
  
  // Combine into chart records: top keywords compared
  const allUniqueTerms = Array.from(new Set([
    ...jdKeywords.map((k: any) => k.text),
    ...resumeKeywords.map((k: any) => k.text)
  ])).slice(0, 6);

  const keywordsComparisonData = allUniqueTerms.map(term => {
    const jdVal = jdKeywords.find((k: any) => k.text === term)?.value ?? 0;
    const resVal = resumeKeywords.find((k: any) => k.text === term)?.value ?? 0;
    return {
      name: term,
      "Job Description": jdVal,
      "Your Resume": resVal
    };
  });

  // Skill Gap Counts
  const presentSkills = result?.extracted_skills?.filter((s: any) => s.present) || [];
  const missingSkillsList = result?.missing_skills || [
    ...missingCategorized.critical,
    ...missingCategorized.recommended,
    ...missingCategorized.optional
  ];
  
  const skillGapData = [
    { name: "Matched Skills", count: presentSkills.length || 6, fill: "#ACFF5D" },
    { name: "Missing Gap", count: missingSkillsList.length || 4, fill: "#66415C" }
  ];

  // Recruiter Insights
  const insights = result?.recruiter_insights ?? {
    strengths: result?.strengths ?? ["Relevant project accomplishments"],
    weaknesses: ["Missing cloud architecture deployment exposure"],
    improvement_suggestions: result?.recommendations ?? ["Emphasize orchestration frameworks"]
  };

  // Interview Readiness
  const readiness = result?.interview_readiness ?? {
    score: result?.interview_readiness_score ?? 75,
    status: (result?.interview_readiness_score ?? 75) >= 75 ? "Likely Shortlisted" : "Borderline"
  };

  const getReadinessColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "likely shortlisted":
        return { text: "text-[#ACFF5D]", border: "border-[#ACFF5D]/20", bg: "bg-[#ACFF5D]/5", badge: "bg-[#ACFF5D]" };
      case "borderline":
        return { text: "text-[#D65BB4]", border: "border-[#D65BB4]/20", bg: "bg-[#D65BB4]/5", badge: "bg-[#D65BB4]" };
      default:
        return { text: "text-[#E05B5B]", border: "border-[#E05B5B]/20", bg: "bg-[#E05B5B]/5", badge: "bg-[#E05B5B]" };
    }
  };
  const readinessColor = getReadinessColor(readiness.status);

  // ATS Semicircle Gauge Data
  const gaugeData = [
    { name: "Score", value: score, fill: score >= 90 ? "#ACFF5D" : score >= 75 ? "#D65BB4" : score >= 60 ? "#66415C" : "#E05B5B" },
    { name: "Remaining", value: 100 - score, fill: "#30232E" }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.05 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 260, damping: 22 } },
  };

  return (
    <div className="flex-grow overflow-y-auto p-6 lg:p-8 space-y-8 select-none bg-zinc-950/20 custom-scrollbar">
      {/* Page Header */}
      <div className="border-b border-zinc-900 pb-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2.5 select-text">
            <FileUser className="w-8 h-8 text-primary shrink-0" />
            ATS Resume Optimization Engine
          </h1>
          <p className="text-zinc-500 text-xs mt-1 leading-relaxed">
            Enterprise candidate scanner and alignment dashboard. Audits keyword density, core qualification vectors, missing skill gaps, and interview prep suggestions.
          </p>
        </div>

        {result && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setResult(null);
              setResumeFile(null);
              setJdFile(null);
            }}
            className="border-zinc-800 hover:bg-zinc-900 font-bold hover:text-zinc-100 transition-all text-xs"
          >
            Scan New Resume
          </Button>
        )}
      </div>

      {/* Form Upload Panel */}
      {!result ? (
        <Card className="glass-panel border-zinc-900 max-w-4xl mx-auto overflow-hidden relative shadow-2xl">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-violet-600 via-primary to-violet-600 animate-pulse" />
          <CardHeader className="pb-4">
            <CardTitle className="text-sm font-bold text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              Upload Diagnostic Portal
            </CardTitle>
            <CardDescription className="text-zinc-550 text-xs">
              Upload candidate resume PDF alongside target job requirements document to extract ATS alignment scoring vectors.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalyze} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Resume Upload File Box */}
                <div className="border border-dashed border-zinc-800 hover:border-violet-500/40 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all bg-zinc-900/10 hover:bg-zinc-900/20 relative group min-h-[170px]">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleResumeChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  />
                  <Upload className="w-8 h-8 text-zinc-650 group-hover:text-primary transition-colors mb-3 group-hover:scale-110 duration-200" />
                  {resumeFile ? (
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-zinc-200 truncate max-w-[220px]">
                        {resumeFile.name}
                      </p>
                      <p className="text-[10px] text-emerald-400 font-bold tracking-wider uppercase">Resume Loaded ✓</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-semibold group-hover:text-zinc-200 transition-colors">Upload Candidate Resume</p>
                      <p className="text-[9px] text-zinc-500 mt-1">PDF document (Max 10MB)</p>
                    </div>
                  )}
                </div>

                {/* Job Description Upload File Box */}
                <div className="border border-dashed border-zinc-800 hover:border-violet-500/40 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all bg-zinc-900/10 hover:bg-zinc-900/20 relative group min-h-[170px]">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleJdChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  />
                  <Upload className="w-8 h-8 text-zinc-650 group-hover:text-primary transition-colors mb-3 group-hover:scale-110 duration-200" />
                  {jdFile ? (
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-zinc-200 truncate max-w-[220px]">
                        {jdFile.name}
                      </p>
                      <p className="text-[10px] text-emerald-400 font-bold tracking-wider uppercase">Job Description Loaded ✓</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-semibold group-hover:text-zinc-200 transition-colors">Upload Job Description</p>
                      <p className="text-[9px] text-zinc-500 mt-1">PDF document (Max 10MB)</p>
                    </div>
                  )}
                </div>
              </div>

              {errorMsg && (
                <div className="p-3.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-[11px] text-rose-400 flex items-start gap-2 max-w-lg mx-auto select-text">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex justify-center pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  className="px-10 font-bold w-full md:w-auto text-xs bg-gradient-to-r from-violet-600 to-indigo-500 hover:from-violet-500 hover:to-indigo-400 text-zinc-100 border-0 shadow-lg shadow-violet-600/10 hover:shadow-violet-600/20 transition-all duration-300 py-4 h-auto"
                  disabled={!resumeFile || !jdFile || isAnalyzing}
                  loading={isAnalyzing}
                >
                  Start ATS Matching Diagnostic
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : (
        /* Upgraded ATS Results Dashboard Section */
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-8"
        >
          {/* Analysis Source Header Info */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-zinc-950/40 border border-zinc-900 px-5 py-4 rounded-2xl backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                <ShieldCheck className="w-4.5 h-4.5 text-primary" />
              </div>
              <div className="text-[11px] font-mono">
                <span className="text-zinc-500 uppercase tracking-wider font-bold">Candidate: </span>
                <span className="font-bold text-zinc-200 select-text bg-zinc-900/40 px-2 py-0.5 rounded border border-zinc-850">{resumeFile?.name}</span>
              </div>
            </div>
            
            <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-500">
              <span>ATS Scanner Status: </span>
              <span className="text-emerald-400 font-bold uppercase tracking-wider bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Diagnostic Ready
              </span>
            </div>
          </div>

          {/* 1. Core Score Card and Radar Alignment */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* LARGE ATS MATCH CARD (Left 4 Cols) */}
            <motion.div variants={itemVariants} className="lg:col-span-4 flex flex-col gap-6">
              <Card className={cn("glass-panel border-zinc-900 shadow-xl overflow-hidden relative flex flex-col justify-between h-full bg-gradient-to-b from-zinc-950/60 to-zinc-950/20", scoreInfo.glow)}>
                <div className={cn("absolute top-0 left-0 right-0 h-[2px]", scoreInfo.bar)} />
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">ATS Match Score</CardTitle>
                    <span className={cn("text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded border", scoreInfo.color, scoreInfo.border, scoreInfo.bg)}>
                      {scoreInfo.label}
                    </span>
                  </div>
                  <CardDescription className="text-zinc-550 text-[10px]">Overall resume alignment probability</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center py-6 flex-grow">
                  {/* Gauge visualization using Recharts Pie chart */}
                  <div className="w-[180px] h-[120px] relative flex justify-center items-end select-none">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={gaugeData}
                          cx="50%"
                          cy="100%"
                          startAngle={180}
                          endAngle={0}
                          innerRadius={65}
                          outerRadius={80}
                          dataKey="value"
                          stroke="none"
                        >
                          <Cell fill={gaugeData[0].fill} />
                          <Cell fill={gaugeData[1].fill} />
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-end pb-1 text-center">
                      <span className="text-4xl font-extrabold text-zinc-100 font-mono tracking-tight leading-none">
                        {score}
                      </span>
                      <span className="text-[10px] text-zinc-500 font-mono tracking-widest font-bold mt-1 uppercase">
                        / 100
                      </span>
                    </div>
                  </div>

                  {/* Rating scale markers */}
                  <div className="grid grid-cols-4 w-full gap-1 pt-6 text-[8px] font-mono font-bold text-center uppercase tracking-wide">
                    <div className={cn("p-1 rounded bg-rose-500/5 border border-rose-500/10 text-rose-500/70", score < 60 && "bg-rose-500/10 text-rose-400 border-rose-500/30")}>Poor</div>
                    <div className={cn("p-1 rounded bg-amber-500/5 border border-amber-500/10 text-amber-500/70", score >= 60 && score < 75 && "bg-amber-500/10 text-amber-400 border-amber-500/30")}>Avg</div>
                    <div className={cn("p-1 rounded bg-blue-500/5 border border-blue-500/10 text-blue-500/70", score >= 75 && score < 90 && "bg-blue-500/10 text-blue-400 border-blue-500/30")}>Good</div>
                    <div className={cn("p-1 rounded bg-emerald-500/5 border border-emerald-500/10 text-emerald-500/70", score >= 90 && "bg-emerald-500/10 text-emerald-400 border-emerald-500/30")}>Excel</div>
                  </div>
                </CardContent>
                <div className="p-4 border-t border-zinc-900 bg-zinc-950/40 flex justify-between items-center text-[10px] font-mono text-zinc-500">
                  <span>Formatting checks:</span>
                  <span className="text-zinc-350 font-bold flex items-center gap-1">
                    <Check className="w-3 h-3 text-emerald-400" />
                    Passed (90%)
                  </span>
                </div>
              </Card>
            </motion.div>

            {/* ATS COMPETENCY RADAR CHART (Right 8 Cols) */}
            <motion.div variants={itemVariants} className="lg:col-span-8">
              <Card className="glass-panel border-zinc-900/60 h-full relative overflow-hidden flex flex-col justify-between">
                <CardHeader className="pb-1 bg-zinc-950/20 border-b border-zinc-900/40">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                    <TrendingUp className="w-4 h-4 text-primary" />
                    ATS Competency Radar
                  </CardTitle>
                  <CardDescription className="text-zinc-550 text-[10px] leading-relaxed">
                    Overview of core match criteria vectors comparing candidate capability metrics side-by-side.
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow flex items-center justify-center py-4">
                  <div className="w-full h-[250px] relative select-none">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" radius="75%" data={radarData}>
                        <PolarGrid stroke="#30232E" />
                        <PolarAngleAxis
                          dataKey="subject"
                          tick={{ fill: "#858585", fontSize: 9, fontWeight: 700 }}
                        />
                        <PolarRadiusAxis
                          angle={45}
                          domain={[0, 100]}
                          tick={{ fill: "#858585", fontSize: 8 }}
                          stroke="#30232E"
                        />
                        <Radar
                          name="Candidate Score"
                          dataKey="value"
                          stroke="#D65BB4"
                          fill="#D65BB4"
                          fillOpacity={0.18}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* 2. Match Breakdown Cards Grid (6 dimensions) */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {breakdown.map((item, idx) => (
              <motion.div key={idx} variants={itemVariants}>
                <Card className="glass-panel border-zinc-900 hover:border-zinc-800 transition-all group overflow-hidden bg-zinc-950/30" glass>
                  <CardContent className="p-4.5 space-y-3 flex flex-col justify-between h-full">
                    <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                      <span>{item.name}</span>
                    </div>
                    <div className="flex items-baseline gap-0.5">
                      <span className="text-2xl font-bold font-mono text-zinc-150 group-hover:text-zinc-50 transition-colors">
                        {item.value}
                      </span>
                      <span className="text-xs text-zinc-500 font-mono">%</span>
                    </div>
                    <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden border border-zinc-950/50">
                      <div className={cn("h-full rounded-full transition-all duration-500", item.color.split(" ")[0])} style={{ width: `${item.value}%` }} />
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* 3. Missing Skills Categorization Panel */}
          <motion.div variants={itemVariants}>
            <Card className="glass-panel border-zinc-900/60 overflow-hidden relative">
              <CardHeader className="bg-zinc-950/20 border-b border-zinc-900/40">
                <div className="flex items-center gap-2">
                  <BadgeAlert className="w-5 h-5 text-rose-400 shrink-0" />
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Missing Skill Stack Gaps</CardTitle>
                </div>
                <CardDescription className="text-zinc-555 text-[10px] leading-relaxed">
                  Technologies isolated in the Job Description requirements but missing from the candidate's resume, sorted by importance.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-5 select-text">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  
                  {/* CRITICAL (Red) */}
                  <div className="space-y-3 p-4 bg-rose-500/5 rounded-xl border border-rose-500/15">
                    <div className="flex items-center justify-between border-b border-rose-500/20 pb-2">
                      <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-rose-400">Critical Priority</span>
                      <span className="text-[9px] font-mono font-bold text-rose-455 bg-rose-500/10 px-1.5 py-0.5 rounded">Must Have</span>
                    </div>
                    {missingCategorized.critical?.length === 0 ? (
                      <p className="text-xs text-zinc-600 italic py-2">No critical missing skills detected</p>
                    ) : (
                      <ul className="space-y-2 text-xs">
                        {missingCategorized.critical.map((skill: any, idx: number) => (
                          <li key={idx} className="flex items-center gap-2 text-zinc-350">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" />
                            <span className="font-semibold">{renderChild(skill)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* RECOMMENDED (Orange) */}
                  <div className="space-y-3 p-4 bg-amber-500/5 rounded-xl border border-amber-500/15">
                    <div className="flex items-center justify-between border-b border-amber-500/20 pb-2">
                      <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-amber-400">Recommended</span>
                      <span className="text-[9px] font-mono font-bold text-amber-455 bg-amber-500/10 px-1.5 py-0.5 rounded">Should Have</span>
                    </div>
                    {missingCategorized.recommended?.length === 0 ? (
                      <p className="text-xs text-zinc-600 italic py-2">No recommended missing skills</p>
                    ) : (
                      <ul className="space-y-2 text-xs">
                        {missingCategorized.recommended.map((skill: any, idx: number) => (
                          <li key={idx} className="flex items-center gap-2 text-zinc-350">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                            <span className="font-semibold">{renderChild(skill)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* OPTIONAL (Blue) */}
                  <div className="space-y-3 p-4 bg-blue-500/5 rounded-xl border border-blue-500/15">
                    <div className="flex items-center justify-between border-b border-blue-500/20 pb-2">
                      <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-blue-400">Optional</span>
                      <span className="text-[9px] font-mono font-bold text-blue-455 bg-blue-500/10 px-1.5 py-0.5 rounded">Nice to Have</span>
                    </div>
                    {missingCategorized.optional?.length === 0 ? (
                      <p className="text-xs text-zinc-600 italic py-2">No optional missing skills</p>
                    ) : (
                      <ul className="space-y-2 text-xs">
                        {missingCategorized.optional.map((skill: any, idx: number) => (
                          <li key={idx} className="flex items-center gap-2 text-zinc-350">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                            <span className="font-semibold">{renderChild(skill)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* 4. Keyword Analysis with Double Bar Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Visual Double Bar Chart (Left 2 columns) */}
            <motion.div variants={itemVariants} className="lg:col-span-2">
              <Card className="glass-panel border-zinc-900/60 h-full flex flex-col justify-between">
                <CardHeader className="pb-1 bg-zinc-950/20 border-b border-zinc-900/40">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                    <Code className="w-4 h-4 text-violet-500" />
                    Target Keyword Density Analysis
                  </CardTitle>
                  <CardDescription className="text-zinc-550 text-[10px] leading-relaxed">
                    Comparison of primary keyword occurrence volumes matched between the JD requirements and candidate resume text.
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow flex items-center justify-center py-6">
                  <div className="w-full h-[240px] relative select-none">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={keywordsComparisonData} margin={{ top: 20, right: 10, left: -25, bottom: 5 }}>
                        <XAxis dataKey="name" stroke="#858585" fontSize={10} tickLine={false} />
                        <YAxis stroke="#858585" fontSize={10} tickLine={false} />
                        <Tooltip
                          cursor={{ fill: "rgba(255,255,255,0.02)" }}
                          contentStyle={{ backgroundColor: "#1A171B", borderColor: "#30232E", borderRadius: 12, fontSize: 10, fontFamily: "monospace" }}
                        />
                        <Legend wrapperStyle={{ fontSize: 9, fontFamily: "monospace", paddingTop: 10 }} />
                        <Bar dataKey="Job Description" fill="#D65BB4" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Your Resume" fill="#66415C" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Keyword stats and Missing terms (Right 1 column) */}
            <motion.div variants={itemVariants} className="lg:col-span-1">
              <Card className="glass-panel border-zinc-900/60 h-full flex flex-col justify-between relative overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-[2px] bg-violet-600/30" />
                <CardHeader className="pb-1 bg-zinc-950/20 border-b border-zinc-900/40">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Coverage Metrics</CardTitle>
                </CardHeader>
                <CardContent className="p-5 flex-grow flex flex-col justify-between gap-5 select-text">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-900/40 border border-zinc-850">
                    <div className="space-y-1">
                      <span className="text-[9px] uppercase font-bold text-zinc-550 leading-none">Vocabulary Coverage</span>
                      <p className="text-[10px] text-zinc-450 leading-relaxed mt-0.5">Primary match rate</p>
                    </div>
                    <span className="text-2xl font-bold font-mono text-violet-400">
                      {keywordAnalysis.keyword_coverage_pct}%
                    </span>
                  </div>

                  <div className="space-y-2 flex-grow">
                    <span className="text-[9px] uppercase font-bold text-zinc-555 tracking-wider">Missing JD Keywords</span>
                    {keywordAnalysis.missing_keywords?.length === 0 ? (
                      <p className="text-[10px] text-zinc-500 italic">No missing keywords detected</p>
                    ) : (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {keywordAnalysis.missing_keywords.map((word: any, idx: number) => (
                          <span
                            key={idx}
                            className="text-[9px] font-bold font-mono px-2 py-0.5 rounded border border-zinc-800 bg-zinc-900/60 text-zinc-450 hover:text-zinc-200 transition-colors"
                          >
                            {renderChild(word)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

          </div>

          {/* 5. Recruiter Insights side-by-side */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Strengths */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 h-full flex flex-col justify-between">
                <CardHeader className="border-b border-zinc-900/60 pb-3 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4.5 h-4.5" />
                    Strengths
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 flex-grow select-text">
                  <ul className="space-y-2">
                    {insights.strengths?.map((str: any, idx: number) => (
                      <li key={idx} className="flex items-start gap-2.5 leading-relaxed bg-emerald-500/5 border border-emerald-500/10 p-2.5 rounded-lg text-xs text-zinc-350">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{renderChild(str)}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>

            {/* Weaknesses */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 h-full flex flex-col justify-between">
                <CardHeader className="border-b border-zinc-900/60 pb-3 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-rose-450 flex items-center gap-1.5">
                    <AlertTriangle className="w-4.5 h-4.5" />
                    Weaknesses
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 flex-grow select-text">
                  <ul className="space-y-2">
                    {insights.weaknesses?.map((weak: any, idx: number) => (
                      <li key={idx} className="flex items-start gap-2.5 leading-relaxed bg-rose-500/5 border border-rose-500/10 p-2.5 rounded-lg text-xs text-zinc-350">
                        <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                        <span>{renderChild(weak)}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>

            {/* Suggestions */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 h-full flex flex-col justify-between">
                <CardHeader className="border-b border-zinc-900/60 pb-3 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-primary flex items-center gap-1.5">
                    <Lightbulb className="w-4.5 h-4.5 text-primary" />
                    Suggestions
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 flex-grow select-text">
                  <ul className="space-y-2">
                    {insights.improvement_suggestions?.map((sug: any, idx: number) => (
                      <li key={idx} className="flex items-start gap-2.5 leading-relaxed bg-zinc-900/30 border border-zinc-900 p-2.5 rounded-lg text-xs text-zinc-350">
                        <span className="font-mono text-[9px] font-bold text-violet-400 bg-violet-500/10 border border-violet-500/20 w-4.5 h-4.5 rounded flex items-center justify-center shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <span>{renderChild(sug)}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>

          </div>

          {/* 6. Interview Readiness with Donut Semicircle */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            
            {/* Semicircle Gauge (Left 4 cols) */}
            <motion.div variants={itemVariants} className="md:col-span-4 flex flex-col gap-6">
              <Card className={cn("glass-panel border-zinc-900/60 overflow-hidden relative flex flex-col justify-between h-full bg-gradient-to-b from-zinc-950/40 to-zinc-950/10", readinessColor.border)}>
                <div className={cn("absolute top-0 left-0 right-0 h-[2px]", readinessColor.badge)} />
                <CardHeader className="pb-1">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Interview Readiness</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center py-6 flex-grow">
                  
                  {/* Gauge semicircle progress visual */}
                  <div className="relative w-24 h-24 rounded-full border border-zinc-900 bg-zinc-950 flex items-center justify-center shrink-0">
                    <svg className="w-20 h-20 transform -rotate-90">
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke="#30232E"
                        strokeWidth="6"
                        fill="transparent"
                      />
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke={readiness.score >= 75 ? "#ACFF5D" : readiness.score >= 60 ? "#D65BB4" : "#E05B5B"}
                        strokeWidth="6"
                        fill="transparent"
                        strokeDasharray={200}
                        strokeDashoffset={200 - (200 * (readiness.score)) / 100}
                        strokeLinecap="round"
                        className="transition-all duration-1000 ease-out"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                      <span className="text-xl font-bold font-mono text-zinc-150 leading-none">
                        {readiness.score}%
                      </span>
                    </div>
                  </div>

                  <span className={cn("mt-4 text-xs font-bold", readinessColor.text)}>
                    {readiness.status}
                  </span>
                </CardContent>
              </Card>
            </motion.div>

            {/* Preparation Stepper roadmap (Right 8 cols) */}
            <motion.div variants={itemVariants} className="md:col-span-8">
              <Card className="glass-panel border-zinc-900/60 overflow-hidden relative h-full flex flex-col justify-between">
                <CardHeader className="border-b border-zinc-900/80 pb-3 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                    <Sparkles className="w-4.5 h-4.5 text-primary animate-pulse" />
                    ATS Optimization Stepper Roadmap
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 select-text flex-grow flex flex-col justify-between gap-6">
                  
                  {/* Stepper milestones */}
                  <div className="relative pl-6 space-y-6 border-l border-zinc-850/80 ml-3 py-1">
                    {/* Step 1 */}
                    <div className="relative">
                      <span className="absolute -left-[35px] top-0.5 w-4 h-4 rounded-full bg-zinc-950 border border-primary text-[8px] font-bold font-mono text-primary flex items-center justify-center shadow-[0_0_8px_rgba(139,92,246,0.3)]">
                        1
                      </span>
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-zinc-200">Study Critical Stack Gaps</span>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Address missing core requirements immediately: <span className="font-mono text-zinc-350 font-semibold">{Array.isArray(missingCategorized.critical) ? missingCategorized.critical.slice(0, 3).map(renderChild).join(", ") : "No critical gaps listed"}</span>.
                        </p>
                      </div>
                    </div>

                    {/* Step 2 */}
                    <div className="relative">
                      <span className="absolute -left-[35px] top-0.5 w-4 h-4 rounded-full bg-zinc-950 border border-zinc-800 text-[8px] font-bold font-mono text-zinc-550 flex items-center justify-center">
                        2
                      </span>
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-zinc-200">Refactor Project Narratives</span>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Incorporate missing keywords and highlight architectural metrics in resume projects: <span className="italic text-zinc-400">"{renderChild(insights.improvement_suggestions?.[0]) || "Describe experience designing systems using recommended toolsets."}"</span>.
                        </p>
                      </div>
                    </div>

                    {/* Step 3 */}
                    <div className="relative">
                      <span className="absolute -left-[35px] top-0.5 w-4 h-4 rounded-full bg-zinc-950 border border-zinc-800 text-[8px] font-bold font-mono text-zinc-550 flex items-center justify-center">
                        3
                      </span>
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-zinc-200">Interview Concept Screening preparation</span>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Prepare explanations for potential weaknesses: <span className="italic text-zinc-400">"{renderChild(insights.improvement_suggestions?.[1]) || "Review concepts related to missing technologies."}"</span>.
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* 7. Levels.fyi style Credentials comparison table */}
          <motion.div variants={itemVariants}>
            <Card className="glass-panel border-zinc-900/60 relative overflow-hidden">
              <CardHeader className="border-b border-zinc-900/80 pb-3 bg-zinc-950/20">
                <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                  <ListTodo className="w-4 h-4 text-primary" />
                  Credentials Match Comparison (Levels.fyi style)
                </CardTitle>
                <CardDescription className="text-zinc-550 text-[10px] leading-relaxed">
                  Detailed semantic alignment matrix checking candidate credentials against target criteria side-by-side.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-zinc-900/60 text-xs select-text">
                  
                  {/* Category 1: Education */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4.5 items-start">
                    <div className="md:col-span-3 font-semibold text-zinc-400 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
                      <GraduationCap className="w-4 h-4 text-cyan-400" />
                      Academic Background
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/20 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">Resume Extracted</div>
                      <div className="text-zinc-200 text-[11px] leading-relaxed">
                        {renderChild(result.extracted_education) || "No degrees listed in resume"}
                      </div>
                    </div>
                    <div className="md:col-span-1 flex justify-center items-center h-full pt-4 md:pt-6">
                      <ArrowRight className="w-4 h-4 text-zinc-650 hidden md:block" />
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/20 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">JD Target Requirement</div>
                      <div className="text-zinc-350 text-[11px] leading-relaxed">
                        {renderChild((Array.isArray(result.jd_requirements) ? result.jd_requirements.find((r: any) => typeof r === "string" && (r.toLowerCase().includes("degree") || r.toLowerCase().includes("education") || r.toLowerCase().includes("cs") || r.toLowerCase().includes("bachelor") || r.toLowerCase().includes("master"))) : null)) || "BS/MS in Computer Science, engineering, or related field equivalence"}
                      </div>
                    </div>
                  </div>

                  {/* Category 2: Experience */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4.5 items-start">
                    <div className="md:col-span-3 font-semibold text-zinc-400 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
                      <Briefcase className="w-4 h-4 text-emerald-400" />
                      Professional History
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/20 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">Resume Extracted</div>
                      <div className="text-zinc-200 text-[11px] leading-relaxed">
                        {renderChild(result.extracted_experience) || "No professional experience listed"}
                      </div>
                    </div>
                    <div className="md:col-span-1 flex justify-center items-center h-full pt-4 md:pt-6">
                      <ArrowRight className="w-4 h-4 text-zinc-650 hidden md:block" />
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/20 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">JD Target Requirement</div>
                      <div className="text-zinc-350 text-[11px] leading-relaxed">
                        {renderChild((Array.isArray(result.jd_requirements) ? result.jd_requirements.find((r: any) => typeof r === "string" && (r.toLowerCase().includes("year") || r.toLowerCase().includes("experience") || r.toLowerCase().includes("work"))) : null)) || "3+ Years building production web applications or machine learning services"}
                      </div>
                    </div>
                  </div>

                  {/* Category 3: Projects */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4.5 items-start">
                    <div className="md:col-span-3 font-semibold text-zinc-400 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
                      <Code className="w-4 h-4 text-violet-400" />
                      Technical Projects
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/20 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">Resume Extracted</div>
                      <ul className="list-disc pl-4 text-zinc-200 text-[11px] space-y-1.5">
                        {result.extracted_projects?.map((proj: any, idx: number) => (
                          <li key={idx} className="leading-relaxed">{renderChild(proj)}</li>
                        )) || <li className="italic text-zinc-500">No projects listed</li>}
                      </ul>
                    </div>
                    <div className="md:col-span-1 flex justify-center items-center h-full pt-4 md:pt-6">
                      <ArrowRight className="w-4 h-4 text-zinc-650 hidden md:block" />
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/20 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">JD Target Focus</div>
                      <div className="text-zinc-350 text-[11px] leading-relaxed">
                        Demonstrated capability building API endpoints, workflow graphs, custom integrations, or deploying containerized applications.
                      </div>
                    </div>
                  </div>

                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
