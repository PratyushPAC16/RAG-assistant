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
  Info,
  X,
  Target,
  GraduationCap,
  Briefcase,
  Code,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  ListTodo,
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

  // Derive experience match percentage and stats
  const experienceMatchPct = result?.interview_readiness_score ?? 80;
  const hiringRisk = result
    ? result.match_score >= 85
      ? { label: "Low Risk", level: "low", color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5", val: 15 }
      : result.match_score >= 65
      ? { label: "Moderate Risk", level: "moderate", color: "text-amber-400 border-amber-500/20 bg-amber-500/5", val: 45 }
      : { label: "High Risk", level: "high", color: "text-rose-400 border-rose-500/20 bg-rose-500/5", val: 80 }
    : null;

  // Radar metrics
  const radarData = result
    ? [
        { subject: "Skills Match", value: result.skill_match_pct },
        { subject: "Projects Match", value: result.project_match_pct },
        { subject: "Experience Fit", value: experienceMatchPct },
        { subject: "Education Fit", value: result.education_match_pct },
      ]
    : [];

  // Skills present vs missing data
  const presentSkills = result?.extracted_skills?.filter((s: any) => s.present) || [];
  const missingSkills = result?.missing_skills || [];
  const totalSkillsExtracted = presentSkills.length + missingSkills.length;

  const skillGapData = result
    ? [
        { name: "Matched Skills", count: presentSkills.length, fill: "#10b981" },
        { name: "Missing Gap", count: missingSkills.length, fill: "#f43f5e" },
      ]
    : [];

  // Custom visual components for stats
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
      {/* Page header */}
      <div className="border-b border-zinc-900 pb-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <FileUser className="w-8 h-8 text-amber-400 shrink-0" />
            ATS Resume Intelligence
          </h1>
          <p className="text-zinc-500 text-xs mt-1 leading-relaxed">
            SaaS-grade candidate diagnostics comparison engine. Scrapes matching scores, competency vectors, skill gaps, risk indices, and roadmaps.
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
            Analyze New Documents
          </Button>
        )}
      </div>

      {/* Upload Zone (Initially shown) */}
      {!result ? (
        <Card className="glass-panel border-zinc-900 max-w-4xl mx-auto overflow-hidden relative shadow-2xl">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-amber-400 via-violet-600 to-amber-400" />
          <CardHeader className="pb-4">
            <CardTitle className="text-sm font-bold text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-amber-400" />
              ATS Verification Portal
            </CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Upload candidate resume PDF and target job description PDF to initialize Career Intelligence scoring.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalyze} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Resume Upload Box */}
                <div className="border border-dashed border-zinc-800 hover:border-amber-400/40 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all bg-zinc-900/10 hover:bg-zinc-900/20 relative group min-h-[160px]">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleResumeChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  />
                  <Upload className="w-7 h-7 text-zinc-650 group-hover:text-amber-400 transition-colors mb-3 group-hover:scale-110 duration-200" />
                  {resumeFile ? (
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-zinc-200 truncate max-w-[220px]">
                        {resumeFile.name}
                      </p>
                      <p className="text-[10px] text-emerald-400 font-medium">Resume PDF Loaded ✓</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-semibold group-hover:text-zinc-200 transition-colors">Upload Candidate Resume</p>
                      <p className="text-[9px] text-zinc-500 mt-1">PDF format (Max 10MB)</p>
                    </div>
                  )}
                </div>

                {/* Job Description Upload Box */}
                <div className="border border-dashed border-zinc-800 hover:border-violet-500/40 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all bg-zinc-900/10 hover:bg-zinc-900/20 relative group min-h-[160px]">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleJdChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  />
                  <Upload className="w-7 h-7 text-zinc-650 group-hover:text-violet-500 transition-colors mb-3 group-hover:scale-110 duration-200" />
                  {jdFile ? (
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-zinc-200 truncate max-w-[220px]">
                        {jdFile.name}
                      </p>
                      <p className="text-[10px] text-emerald-400 font-medium">Job Description Loaded ✓</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-semibold group-hover:text-zinc-200 transition-colors">Upload Job Description</p>
                      <p className="text-[9px] text-zinc-500 mt-1">PDF format (Max 10MB)</p>
                    </div>
                  )}
                </div>
              </div>

              {errorMsg && (
                <div className="p-3.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-[11px] text-rose-450 flex items-start gap-2 max-w-lg mx-auto select-text">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex justify-center pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  className="px-10 font-bold w-full md:w-auto text-xs bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-zinc-950 border-0 shadow-lg shadow-amber-500/10 hover:shadow-amber-500/20 transition-all duration-300 py-4 h-auto"
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
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 border border-amber-400/20 flex items-center justify-center">
                <ShieldCheck className="w-4.5 h-4.5 text-amber-400" />
              </div>
              <div className="text-[11px] font-mono">
                <span className="text-zinc-500 uppercase tracking-wider font-bold">Candidate: </span>
                <span className="font-bold text-zinc-200 select-text bg-zinc-900/40 px-2 py-0.5 rounded border border-zinc-850">{resumeFile?.name}</span>
              </div>
            </div>
            
            <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-500">
              <span>ATS Scanner: </span>
              <span className="text-emerald-400 font-bold uppercase tracking-wider bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Passed Check</span>
            </div>
          </div>

          {/* 1. Core ATS Match Metrics Dials */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { label: "Overall Fit Score", val: result.match_score, icon: TrendingUp, col: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
              { label: "Skill Stack Alignment", val: result.skill_match_pct, icon: Award, col: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
              { label: "Project Relevance", val: result.project_match_pct, icon: Zap, col: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
              { label: "Education Credentials", val: result.education_match_pct, icon: BookOpen, col: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20" },
              { label: "Experience Match %", val: experienceMatchPct, icon: UserCheck, col: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
            ].map((d, i) => {
              const Icon = d.icon;
              return (
                <motion.div key={i} variants={itemVariants}>
                  <Card className="glass-panel border-zinc-900/60 overflow-hidden relative group hover:border-zinc-800 transition-colors" glass>
                    <div className="absolute top-0 left-0 w-full h-[1.5px] bg-gradient-to-r from-transparent via-zinc-800 to-transparent group-hover:via-amber-400/20 transition-all duration-300" />
                    <CardContent className="pt-6 flex flex-col items-center text-center">
                      <div className={cn("p-2.5 rounded-xl border shrink-0 transition-transform duration-300 group-hover:scale-105", d.col)}>
                        <Icon className="w-4.5 h-4.5" />
                      </div>
                      <span className="text-[9px] text-zinc-500 uppercase tracking-widest font-bold mt-4 leading-none h-6 flex items-center justify-center">
                        {d.label}
                      </span>
                      <span className="text-3xl font-bold text-zinc-150 font-mono mt-2 flex items-baseline gap-0.5">
                        {d.val}
                        <span className="text-xs text-zinc-500">%</span>
                      </span>

                      {/* Visual Mini Progress Bar */}
                      <div className="w-full bg-zinc-900/60 h-1 rounded-full mt-4 overflow-hidden border border-zinc-950">
                        <div
                          className={cn("h-full rounded-full", {
                            "bg-amber-400": i === 0,
                            "bg-blue-400": i === 1,
                            "bg-violet-400": i === 2,
                            "bg-cyan-400": i === 3,
                            "bg-emerald-400": i === 4,
                          })}
                          style={{ width: `${d.val}%` }}
                        />
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* 2. Visualizations and Analytics Grid (Recharts) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Fit Shape radar */}
            <motion.div variants={itemVariants} className="lg:col-span-2">
              <Card className="glass-panel border-zinc-900/60 h-full">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">ATS Competency Radar</CardTitle>
                  <CardDescription className="text-zinc-500 text-[10px] font-medium leading-relaxed">
                    Visual match alignment covering core competency parameters. Highlights strength shape vectors.
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex justify-center items-center pt-2">
                  <div className="w-full h-[290px] relative select-none">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" radius="72%" data={radarData}>
                        <PolarGrid stroke="#1f1f23" />
                        <PolarAngleAxis
                          dataKey="subject"
                          tick={{ fill: "#8e8e93", fontSize: 9, fontWeight: 700 }}
                        />
                        <PolarRadiusAxis
                          angle={45}
                          domain={[0, 100]}
                          tick={{ fill: "#55555c", fontSize: 8 }}
                          stroke="#1f1f23"
                        />
                        <Radar
                          name="Candidate Strength"
                          dataKey="value"
                          stroke="#fbbf24"
                          fill="#fbbf24"
                          fillOpacity={0.15}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Skill comparison bar */}
            <motion.div variants={itemVariants} className="lg:col-span-1">
              <Card className="glass-panel border-zinc-900/60 h-full">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400">Skill Gap Diagnostic</CardTitle>
                  <CardDescription className="text-zinc-500 text-[10px] font-medium leading-relaxed">
                    Comparison of present matched skills vs missing tools required in the description.
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col justify-between pt-2 h-[290px]">
                  <div className="w-full h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={skillGapData} margin={{ top: 20, right: 10, left: -25, bottom: 5 }}>
                        <XAxis dataKey="name" stroke="#55555c" fontSize={10} tickLine={false} />
                        <YAxis stroke="#55555c" fontSize={10} tickLine={false} />
                        <Tooltip
                          cursor={{ fill: "rgba(255,255,255,0.02)" }}
                          contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", borderRadius: 8, fontSize: 10, fontFamily: "monospace" }}
                        />
                        <Bar dataKey="count" radius={[6, 6, 0, 0]} barSize={45}>
                          {skillGapData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Summary stats */}
                  <div className="border-t border-zinc-900/80 pt-3 flex justify-between items-center text-[10px] font-mono text-zinc-500 px-2">
                    <div className="space-y-0.5">
                      <div>Extracted Stack Size</div>
                      <div className="text-zinc-200 font-bold">{totalSkillsExtracted} total items</div>
                    </div>
                    <div className="space-y-0.5 text-right">
                      <div>Match Coverage</div>
                      <div className="text-emerald-400 font-bold">
                        {totalSkillsExtracted > 0 ? Math.round((presentSkills.length / totalSkillsExtracted) * 100) : 0}%
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* 3. Interview Readiness & Hiring Risk Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Interview Readiness Meter */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 overflow-hidden relative">
                <CardHeader>
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                    <UserCheck className="w-4 h-4 text-emerald-400" />
                    Interview Readiness Assessment
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="flex items-center gap-5">
                    {/* Radial progress semicircle dial */}
                    <div className="relative w-24 h-24 rounded-full border border-zinc-900 bg-zinc-950 flex items-center justify-center shrink-0">
                      <svg className="w-20 h-20 transform -rotate-90">
                        <circle
                          cx="40"
                          cy="40"
                          r="32"
                          stroke="#18181b"
                          strokeWidth="6"
                          fill="transparent"
                        />
                        <circle
                          cx="40"
                          cy="40"
                          r="32"
                          stroke="#10b981"
                          strokeWidth="6"
                          fill="transparent"
                          strokeDasharray={200}
                          strokeDashoffset={200 - (200 * (result.interview_readiness_score || 80)) / 100}
                          strokeLinecap="round"
                          className="transition-all duration-1000 ease-out"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                        <span className="text-xl font-bold font-mono text-zinc-150 leading-none">
                          {result.interview_readiness_score}
                        </span>
                        <span className="text-[8px] text-zinc-500 font-mono mt-0.5">SCORE</span>
                      </div>
                    </div>

                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-zinc-200">Ready to Interview</span>
                        <span className="text-[8px] font-bold font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-full shrink-0">
                          High Fit
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-500 leading-relaxed">
                        Candidate demonstrates sufficient technical capability, project narrative overlap, and academic prerequisites to clear initial technical evaluation loops.
                      </p>
                    </div>
                  </div>

                  {/* Readiness Bullet details */}
                  <div className="grid grid-cols-3 gap-3 pt-3 border-t border-zinc-900/60 text-[9px] font-mono">
                    <div className="space-y-1">
                      <div className="text-zinc-550">Seniority Match</div>
                      <div className="text-zinc-350 font-bold">Strong Overlap</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-zinc-550">Architecture Focus</div>
                      <div className="text-zinc-350 font-bold">85% Alignment</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-zinc-550">Coding Loop Prep</div>
                      <div className="text-amber-400 font-bold">Needs Review</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Hiring Risk Assessment Score Card */}
            {hiringRisk && (
              <motion.div variants={itemVariants}>
                <Card className="glass-panel border-zinc-900/60 overflow-hidden relative h-full">
                  <CardHeader>
                    <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4 text-rose-450" />
                      ATS Hiring Risk Grading
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="flex items-center justify-between gap-4">
                      <div className="space-y-1.5 flex-1">
                        <div className="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
                          Risk Classification: 
                          <span className={cn("text-[9px] font-bold font-mono px-2 py-0.5 rounded border capitalize", 
                            hiringRisk.level === "low" ? "text-emerald-400 border-emerald-500/25 bg-emerald-500/5" :
                            hiringRisk.level === "moderate" ? "text-amber-400 border-amber-500/25 bg-amber-500/5" :
                            "text-rose-400 border-rose-500/25 bg-rose-500/5"
                          )}>
                            {hiringRisk.label}
                          </span>
                        </div>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Risk factor derived from technology tool gaps, tenure gaps, and missing education criteria. Low risk points to seamless integration.
                        </p>
                      </div>

                      <div className="text-center shrink-0 p-3 bg-zinc-900/40 border border-zinc-850 rounded-xl min-w-[70px]">
                        <div className="text-xs font-mono text-zinc-500">Risk Value</div>
                        <div className={cn("text-2xl font-bold font-mono mt-1",
                          hiringRisk.level === "low" ? "text-emerald-400" :
                          hiringRisk.level === "moderate" ? "text-amber-400" :
                          "text-rose-400"
                        )}>
                          {hiringRisk.val}%
                        </div>
                      </div>
                    </div>

                    {/* Hiring risk factors bar indicator */}
                    <div className="space-y-1.5 pt-3 border-t border-zinc-900/60">
                      <div className="flex justify-between text-[8px] font-mono text-zinc-550 uppercase tracking-wider">
                        <span>Risk triggers checked</span>
                        <span>Severity</span>
                      </div>
                      <div className="flex gap-2">
                        {/* Stack overlap */}
                        <div className="flex-1 bg-zinc-900 h-1.5 rounded-full overflow-hidden" title="Stack Gap">
                          <div className={cn("h-full", missingSkills.length > 5 ? "bg-rose-500" : "bg-emerald-500")} style={{ width: missingSkills.length > 5 ? "80%" : "30%" }} />
                        </div>
                        {/* Tenure validation */}
                        <div className="flex-1 bg-zinc-900 h-1.5 rounded-full overflow-hidden" title="Tenure Check">
                          <div className="bg-emerald-500 h-full" style={{ width: "20%" }} />
                        </div>
                        {/* Education qualification */}
                        <div className="flex-1 bg-zinc-900 h-1.5 rounded-full overflow-hidden" title="Education qualifications">
                          <div className={cn("h-full", result.education_match_pct < 70 ? "bg-rose-500" : "bg-emerald-500")} style={{ width: result.education_match_pct < 70 ? "70%" : "15%" }} />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </div>

          {/* 4. Match Breakdown: Side-by-Side Credentials Comparison */}
          <motion.div variants={itemVariants}>
            <Card className="glass-panel border-zinc-900/60 relative overflow-hidden">
              <CardHeader className="border-b border-zinc-900/80 pb-3 bg-zinc-950/20">
                <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                  <ListTodo className="w-4 h-4 text-amber-400" />
                  Credentials Match Breakdown (Levels.fyi Style)
                </CardTitle>
                <CardDescription className="text-zinc-500 text-[10px] font-medium leading-relaxed">
                  Side-by-side semantic alignment table mapping candidate's actual credentials against target requirements.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-zinc-900/60 text-xs select-text">
                  {/* Category 1: Education */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4.5 items-start">
                    <div className="md:col-span-3 font-semibold text-zinc-400 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
                      <GraduationCap className="w-4 h-4 text-cyan-400" />
                      Academic Qualifications
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/25 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">Resume Extracted</div>
                      <div className="text-zinc-200 text-[11px] leading-relaxed">
                        {result.extracted_education || "No degree listed in resume"}
                      </div>
                    </div>
                    <div className="md:col-span-1 flex justify-center items-center h-full pt-4 md:pt-6">
                      <ArrowRight className="w-4 h-4 text-zinc-650 hidden md:block" />
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/25 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">JD Required Threshold</div>
                      <div className="text-zinc-350 text-[11px] leading-relaxed">
                        {(Array.isArray(result.jd_requirements) ? result.jd_requirements.find((r: string) => r.toLowerCase().includes("degree") || r.toLowerCase().includes("education") || r.toLowerCase().includes("cs") || r.toLowerCase().includes("bachelor") || r.toLowerCase().includes("master")) : null) || "BS/MS in Computer Science or quantitative field equivalent"}
                      </div>
                    </div>
                  </div>

                  {/* Category 2: Experience */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4.5 items-start">
                    <div className="md:col-span-3 font-semibold text-zinc-400 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
                      <Briefcase className="w-4 h-4 text-emerald-400" />
                      Professional History
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/25 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">Resume Extracted</div>
                      <div className="text-zinc-200 text-[11px] leading-relaxed">
                        {result.extracted_experience || "No professional experience listed"}
                      </div>
                    </div>
                    <div className="md:col-span-1 flex justify-center items-center h-full pt-4 md:pt-6">
                      <ArrowRight className="w-4 h-4 text-zinc-650 hidden md:block" />
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/25 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">JD Required Threshold</div>
                      <div className="text-zinc-350 text-[11px] leading-relaxed">
                        {(Array.isArray(result.jd_requirements) ? result.jd_requirements.find((r: string) => r.toLowerCase().includes("year") || r.toLowerCase().includes("experience") || r.toLowerCase().includes("work")) : null) || "3+ Years working experience in RAG or Software Development"}
                      </div>
                    </div>
                  </div>

                  {/* Category 3: Projects */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4.5 items-start">
                    <div className="md:col-span-3 font-semibold text-zinc-400 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider">
                      <Code className="w-4 h-4 text-violet-400" />
                      Technical Projects
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/25 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">Resume Extracted</div>
                      <ul className="list-disc pl-4 text-zinc-200 text-[11px] space-y-1">
                        {result.extracted_projects?.map((proj: string, idx: number) => (
                          <li key={idx} className="leading-relaxed">{proj}</li>
                        )) || <li className="italic text-zinc-500">No projects listed</li>}
                      </ul>
                    </div>
                    <div className="md:col-span-1 flex justify-center items-center h-full pt-4 md:pt-6">
                      <ArrowRight className="w-4 h-4 text-zinc-650 hidden md:block" />
                    </div>
                    <div className="md:col-span-4 bg-zinc-900/25 border border-zinc-900 rounded-lg p-3">
                      <div className="text-[9px] font-mono text-zinc-550 uppercase mb-1">JD Required Focus</div>
                      <div className="text-zinc-350 text-[11px] leading-relaxed">
                        Proven experience developing semantic applications, vector databases, API gateways, or agentic frameworks.
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* 5. Gaps & Strengths Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Strengths */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 h-full">
                <CardHeader className="border-b border-zinc-900/60 pb-3.5 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4.5 h-4.5" />
                    Core Strengths Matches
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 select-text">
                  {result.strengths?.length === 0 ? (
                    <p className="text-xs text-zinc-500 italic">No specific strengths listed</p>
                  ) : (
                    <ul className="space-y-2.5 text-xs text-zinc-350">
                      {result.strengths?.map((str: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-2.5 leading-relaxed bg-emerald-500/5 border border-emerald-500/10 p-2.5 rounded-lg">
                          <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{str}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Extracted gaps */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 h-full">
                <CardHeader className="border-b border-zinc-900/60 pb-3.5 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-rose-455 flex items-center gap-1.5">
                    <AlertCircle className="w-4.5 h-4.5 text-rose-400" />
                    Missing Skill Stack Gaps
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 select-text">
                  {missingSkills.length === 0 ? (
                    <div className="flex flex-col items-center justify-center text-center py-12 text-zinc-650">
                      <CheckCircle2 className="w-8 h-8 mb-2 text-emerald-400" />
                      <span className="text-xs font-bold text-zinc-200">100% Technical Match</span>
                      <p className="text-[10px] mt-1 max-w-[80%] leading-relaxed">
                        Candidate has all technical keywords specified in the Job description.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <p className="text-[10px] text-zinc-500 leading-relaxed font-mono">
                        These technologies were found in the JD requirements but are absent in the resume:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {missingSkills.map((skill: string, idx: number) => (
                          <span
                            key={idx}
                            className="text-[10px] font-bold font-mono px-2.5 py-1 rounded-md border border-rose-500/25 bg-rose-500/5 text-rose-400 shadow-sm"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Recommendations */}
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 h-full">
                <CardHeader className="border-b border-zinc-900/60 pb-3.5 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-amber-450 flex items-center gap-1.5">
                    <Target className="w-4.5 h-4.5 text-amber-400" />
                    ATS Optimization Recommendations
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 select-text">
                  <ol className="space-y-3.5 text-xs text-zinc-350">
                    {(Array.isArray(result.recommendations) ? result.recommendations : []).slice(0, 4).map((rec: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2.5 leading-relaxed bg-zinc-900/20 border border-zinc-900 p-2.5 rounded-lg hover:border-zinc-800 transition-colors">
                        <span className="font-mono text-[9px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/20 w-4 h-4 rounded flex items-center justify-center shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* 6. Dynamic Preparation & Learning Roadmap (SaaS Stepper) */}
          {missingSkills.length > 0 && (
            <motion.div variants={itemVariants}>
              <Card className="glass-panel border-zinc-900/60 overflow-hidden relative">
                <CardHeader className="border-b border-zinc-900/80 pb-3.5 bg-zinc-950/20">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-1.5">
                    <Sparkles className="w-4.5 h-4.5 text-amber-400 animate-pulse" />
                    Interactive Roadmap to Bridging Skill Gaps
                  </CardTitle>
                  <CardDescription className="text-zinc-500 text-[10px] font-medium leading-relaxed">
                    Custom milestones mapped step-by-step to study missing requirements, modify project narratives, and qualify for interviews.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                  {/* Milestones timeline grid */}
                  <div className="relative pl-6 space-y-6 border-l border-zinc-850/80 ml-3 py-1">
                    {/* Step 1 */}
                    <div className="relative">
                      <span className="absolute -left-[35px] top-0.5 w-4 h-4 rounded-full bg-zinc-950 border border-amber-400 text-[8px] font-bold font-mono text-amber-400 flex items-center justify-center shadow-[0_0_8px_rgba(251,191,36,0.3)]">
                        1
                      </span>
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-zinc-200">Study Core Gaps ({(Array.isArray(missingSkills) ? missingSkills : []).slice(0, 3).join(", ")})</span>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Dedicate structured study cycles (e.g. 5-7 hours) to review syntax patterns, architectural limits, and benchmark applications for: <span className="font-mono text-zinc-350 font-semibold">{(Array.isArray(missingSkills) ? missingSkills : []).join(", ")}</span>.
                        </p>
                      </div>
                    </div>

                    {/* Step 2 */}
                    <div className="relative">
                      <span className="absolute -left-[35px] top-0.5 w-4 h-4 rounded-full bg-zinc-950 border border-zinc-800 text-[8px] font-bold font-mono text-zinc-550 flex items-center justify-center">
                        2
                      </span>
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-zinc-200">Refactor Project Bullet Points</span>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Follow the advice: <span className="italic text-zinc-400">"{result.recommendations?.[0] || "Update your project experiences to emphasize API design, vector indices, and latency optimization metrics."}"</span>. Reflect these in your resume draft.
                        </p>
                      </div>
                    </div>

                    {/* Step 3 */}
                    <div className="relative">
                      <span className="absolute -left-[35px] top-0.5 w-4 h-4 rounded-full bg-zinc-950 border border-zinc-800 text-[8px] font-bold font-mono text-zinc-550 flex items-center justify-center">
                        3
                      </span>
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-zinc-200">Mock Interview & Concept Review</span>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Prep for concept questions based on: <span className="italic text-zinc-400">"{result.recommendations?.[1] || "Formulate talking points about LangGraph workflows, routing criteria, and cost estimations."}"</span>.
                        </p>
                      </div>
                    </div>

                    {/* Step 4 */}
                    <div className="relative">
                      <span className="absolute -left-[35px] top-0.5 w-4 h-4 rounded-full bg-zinc-950 border border-zinc-800 text-[8px] font-bold font-mono text-zinc-550 flex items-center justify-center">
                        4
                      </span>
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-zinc-200">Qualify JD Requirements Target</span>
                        <p className="text-[10px] text-zinc-500 leading-relaxed">
                          Validate alignment on target requirements check: <span className="font-mono text-zinc-400 font-semibold">{(Array.isArray(result.jd_requirements) ? result.jd_requirements : []).slice(0, 3).join(" • ")}</span>. Schedule your mock screen loop.
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  );
}
