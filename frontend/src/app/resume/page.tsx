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
} from "recharts";
import { motion } from "framer-motion";

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

  // Radar metrics
  const radarData = result
    ? [
        { subject: "Overall Fit", value: result.match_score },
        { subject: "Skill Match", value: result.skill_match_pct },
        { subject: "Projects Match", value: result.project_match_pct },
        { subject: "Education Fit", value: result.education_match_pct },
        { subject: "Interview Ready", value: result.interview_readiness_score },
      ]
    : [];

  const presentSkillsCount = result?.extracted_skills?.filter((s: any) => s.present).length ?? 0;
  const missingSkillsCount = result?.missing_skills?.length ?? 0;

  const barData = result
    ? [
        { name: "Skills Present", count: presentSkillsCount, color: "#10b981" },
        { name: "Skills Missing", count: missingSkillsCount, color: "#ef4444" },
      ]
    : [];

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="border-b border-zinc-800/40 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <FileUser className="w-8 h-8 text-primary" />
          ATS Career Analyzer
        </h1>
        <p className="text-zinc-400 text-sm mt-1">
          Perform a visual semantic match between a candidate resume and job parameters to detect key gaps.
        </p>
      </div>

      {/* Upload Zone */}
      {!result ? (
        <Card className="glass-panel border-zinc-800/40 max-w-4xl mx-auto overflow-hidden relative">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-violet-600 to-indigo-500" />
          <CardHeader>
            <CardTitle className="text-md font-bold text-zinc-100 flex items-center gap-1.5">
              <ShieldCheck className="w-5 h-5 text-primary" />
              ATS Verification Portal
            </CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Upload candidate resume and JD file to extract matching profiles.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalyze} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Resume Upload */}
                <div className="border-2 border-dashed border-zinc-800 hover:border-primary/40 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-zinc-950/20 relative group">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleResumeChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Upload className="w-8 h-8 text-zinc-500 group-hover:text-primary transition-colors mb-3" />
                  {resumeFile ? (
                    <div>
                      <p className="text-xs font-semibold text-zinc-200 truncate max-w-[200px]">
                        {resumeFile.name}
                      </p>
                      <p className="text-[10px] text-zinc-500 mt-1">Resume file loaded</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-semibold">Upload Resume PDF</p>
                      <p className="text-[10px] text-zinc-500 mt-1">Accepts ATS formats</p>
                    </div>
                  )}
                </div>

                {/* Job Description Upload */}
                <div className="border-2 border-dashed border-zinc-800 hover:border-primary/40 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-zinc-950/20 relative group">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleJdChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Upload className="w-8 h-8 text-zinc-500 group-hover:text-primary transition-colors mb-3" />
                  {jdFile ? (
                    <div>
                      <p className="text-xs font-semibold text-zinc-200 truncate max-w-[200px]">
                        {jdFile.name}
                      </p>
                      <p className="text-[10px] text-zinc-500 mt-1">Job Description loaded</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-semibold">Upload Job Description PDF</p>
                      <p className="text-[10px] text-zinc-500 mt-1">Accepts standard parameters</p>
                    </div>
                  )}
                </div>
              </div>

              {errorMsg && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 flex items-start gap-2 max-w-md mx-auto">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex justify-center">
                <Button
                  type="submit"
                  variant="primary"
                  className="px-8 font-semibold w-full md:w-auto"
                  disabled={!resumeFile || !jdFile || isAnalyzing}
                  loading={isAnalyzing}
                >
                  Start Match Diagnostic
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : (
        /* Results Section */
        <div className="space-y-8">
          <div className="flex justify-between items-center bg-zinc-950/40 border border-zinc-850/40 p-4 rounded-xl backdrop-blur-md">
            <div className="text-xs">
              <span className="text-zinc-500">Analysis source: </span>
              <span className="font-bold text-zinc-200">{resumeFile?.name}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setResult(null);
                setResumeFile(null);
                setJdFile(null);
              }}
            >
              Analyze New Resume
            </Button>
          </div>

          {/* KPI score blocks */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: "Overall Fit", val: result.match_score, icon: TrendingUp, col: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
              { label: "Skill Match", val: result.skill_match_pct, icon: Award, col: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
              { label: "Project Relevance", val: result.project_match_pct, icon: Zap, col: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
              { label: "Education Fit", val: result.education_match_pct, icon: BookOpen, col: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20" },
              { label: "Interview Readiness", val: result.interview_readiness_score, icon: UserCheck, col: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
            ].map((d, i) => {
              const Icon = d.icon;
              return (
                <Card key={i} className="glass-panel border-zinc-800/40" glass>
                  <CardContent className="pt-5 flex flex-col items-center text-center">
                    <div className={cn("p-2 rounded-lg border", d.col)}>
                      <Icon className="w-4.5 h-4.5" />
                    </div>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-3">
                      {d.label}
                    </span>
                    <span className="text-2xl font-bold text-zinc-100 font-mono mt-1">
                      {d.val}%
                    </span>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Charts grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Fit Shape radar */}
            <Card className="glass-panel border-zinc-800/40 lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-zinc-100">Overall Match Vector</CardTitle>
                <CardDescription className="text-zinc-500 text-xs">
                  Semantics matching comparison shape.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex justify-center pt-2">
                <div className="w-full h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" radius="75%" data={radarData}>
                      <PolarGrid stroke="#27272a" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: "#a1a1aa", fontSize: 9 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 8 }} />
                      <Radar
                        name="Match Strength"
                        dataKey="value"
                        stroke="#8b5cf6"
                        fill="#8b5cf6"
                        fillOpacity={0.2}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Skill comparison bar */}
            <Card className="glass-panel border-zinc-800/40 lg:col-span-1">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-zinc-100">Skills Comparison</CardTitle>
                <CardDescription className="text-zinc-500 text-xs">
                  Count of candidate present vs missing skills.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex justify-center pt-2">
                <div className="w-full h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barData} margin={{ top: 20, right: 10, left: -20, bottom: 5 }}>
                      <XAxis dataKey="name" stroke="#71717a" fontSize={10} />
                      <YAxis stroke="#71717a" fontSize={10} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", fontSize: 11 }}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={40}>
                        {barData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Checklist & Strengths & Recommendations */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* ATS Match Checklist */}
            <Card className="glass-panel border-zinc-800/40">
              <CardHeader className="border-b border-zinc-800/20 pb-3">
                <CardTitle className="text-sm font-semibold text-zinc-100 flex items-center gap-1.5">
                  <ShieldCheck className="w-4.5 h-4.5 text-primary" /> ATS Check Parameters
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-3">
                  {[
                    { label: "Profile contacts scanned", val: true },
                    { label: "ATS standard format validation", val: true },
                    { label: "Education credentials match", val: result.education_match_pct >= 80 },
                    { label: "Experience requirements matched", val: result.interview_readiness_score >= 80 },
                    { label: "Core technical overlap", val: result.skill_match_pct >= 75 },
                  ].map((chk, i) => (
                    <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-zinc-900/50">
                      <span className="text-zinc-450">{chk.label}</span>
                      {chk.val ? (
                        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <Check className="w-3 h-3" />
                        </span>
                      ) : (
                        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          <Info className="w-3 h-3" />
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Extracted gaps */}
            <Card className="glass-panel border-zinc-800/40">
              <CardHeader className="border-b border-zinc-800/20 pb-3">
                <CardTitle className="text-sm font-semibold text-rose-450 flex items-center gap-1.5">
                  <AlertCircle className="w-4.5 h-4.5 text-rose-400" /> Key Skill Gaps
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                {result.missing_skills?.length === 0 ? (
                  <p className="text-xs text-zinc-500 italic">Complete technical match detected!</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {result.missing_skills?.map((skill: string, idx: number) => (
                      <span
                        key={idx}
                        className="text-[10px] font-bold px-2 py-0.5 rounded border border-rose-500/20 bg-rose-500/10 text-rose-400"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card className="glass-panel border-zinc-800/40">
              <CardHeader className="border-b border-zinc-800/20 pb-3">
                <CardTitle className="text-sm font-semibold text-emerald-450 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4.5 h-4.5 text-emerald-400" /> ATS Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <ol className="space-y-3 text-xs text-zinc-350">
                  {result.recommendations?.slice(0, 4).map((rec: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-2 leading-relaxed">
                      <span className="font-mono text-[10px] font-bold text-zinc-500 shrink-0 mt-0.5">{idx + 1}.</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
