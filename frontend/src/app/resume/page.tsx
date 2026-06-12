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
} from "recharts";

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
      setErrorMsg(err.message || "Failed to analyze files. Make sure they are valid PDF formats.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Prepare chart data
  const radarData = result
    ? [
        { subject: "Overall Fit", value: result.match_score },
        { subject: "Skill Match", value: result.skill_match_pct },
        { subject: "Project Relevance", value: result.project_match_pct },
        { subject: "Education Fit", value: result.education_match_pct },
        { subject: "Interview Readiness", value: result.interview_readiness_score },
      ]
    : [];

  const skillData = result
    ? [
        { name: "Skills Present", count: result.extracted_skills?.filter((s: any) => s.present).length ?? 0 },
        { name: "Skills Missing", count: result.missing_skills?.length ?? 0 },
      ]
    : [];

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="border-b border-zinc-800/40 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <FileUser className="w-8 h-8 text-primary" />
          Resume ATS Matcher
        </h1>
        <p className="text-zinc-400 text-sm mt-1">
          Upload a candidate resume PDF and a target job description PDF to evaluate match metrics, gaps, and recommendations.
        </p>
      </div>

      {/* Upload zone row */}
      {!result ? (
        <Card className="glass-panel border-zinc-800/40 max-w-4xl mx-auto">
          <CardHeader>
            <CardTitle className="text-md font-semibold text-zinc-100">Upload Evaluation Files</CardTitle>
            <CardDescription className="text-zinc-500 text-xs">
              Ensure both files are PDF formats (ATS guidelines standard).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalyze} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Resume Upload */}
                <div className="border-2 border-dashed border-zinc-800 hover:border-primary/40 rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-zinc-950/20 relative group">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleResumeChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Upload className="w-8 h-8 text-zinc-500 group-hover:text-primary transition-colors mb-3" />
                  {resumeFile ? (
                    <div>
                      <p className="text-xs font-semibold text-zinc-200 truncate max-w-[180px]">
                        {resumeFile.name}
                      </p>
                      <p className="text-[10px] text-zinc-500">Resume PDF Loaded</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-medium">Upload Candidate Resume</p>
                      <p className="text-[10px] text-zinc-500">PDF format only</p>
                    </div>
                  )}
                </div>

                {/* Job Description Upload */}
                <div className="border-2 border-dashed border-zinc-800 hover:border-primary/40 rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-zinc-950/20 relative group">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleJdChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Upload className="w-8 h-8 text-zinc-500 group-hover:text-primary transition-colors mb-3" />
                  {jdFile ? (
                    <div>
                      <p className="text-xs font-semibold text-zinc-200 truncate max-w-[180px]">
                        {jdFile.name}
                      </p>
                      <p className="text-[10px] text-zinc-500">Job Description PDF Loaded</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-zinc-300 font-medium">Upload Job Description</p>
                      <p className="text-[10px] text-zinc-500">PDF format only</p>
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
                  Analyze Resume Fit
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : (
        /* Results Dashboard */
        <div className="space-y-8">
          <div className="flex justify-between items-center bg-zinc-950/30 border border-zinc-800/40 p-4 rounded-xl">
            <div className="text-sm">
              <span className="text-zinc-400">Analysis completed for: </span>
              <span className="font-semibold text-zinc-200">{resumeFile?.name}</span>
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
              Start New Analysis
            </Button>
          </div>

          {/* Dials Cards Row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: "Overall Fit", val: result.match_score, icon: TrendingUp, col: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
              { label: "Skill Match", val: result.skill_match_pct, icon: Award, col: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
              { label: "Project Match", val: result.project_match_pct, icon: Zap, col: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
              { label: "Education Match", val: result.education_match_pct, icon: BookOpen, col: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20" },
              { label: "Interview Readiness", val: result.interview_readiness_score, icon: UserCheck, col: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
            ].map((d, i) => {
              const Icon = d.icon;
              return (
                <Card key={i} className="glass-panel border-zinc-800/40" glass>
                  <CardContent className="pt-5 flex flex-col items-center text-center">
                    <div className={`p-1.5 rounded-lg border ${d.col}`}>
                      <Icon className="w-4.5 h-4.5" />
                    </div>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold mt-3">
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

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <Card className="glass-panel border-zinc-800/40">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-zinc-100">Overall Fit Analysis Shape</CardTitle>
                <CardDescription className="text-zinc-500 text-xs">
                  Evaluation vector representation.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex justify-center pt-2">
                <div className="w-full h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" radius="70%" data={radarData}>
                      <PolarGrid stroke="#27272a" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: "#a1a1aa", fontSize: 9 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 8 }} />
                      <Radar
                        name="Candidate Match"
                        dataKey="value"
                        stroke="#8b5cf6"
                        fill="#8b5cf6"
                        fillOpacity={0.25}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="glass-panel border-zinc-800/40">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-zinc-100">Skills Breakdown</CardTitle>
                <CardDescription className="text-zinc-500 text-xs">
                  Count of candidate present vs missing skills requested.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex justify-center pt-2">
                <div className="w-full h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={skillData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                      <XAxis dataKey="name" stroke="#71717a" fontSize={10} />
                      <YAxis stroke="#71717a" fontSize={10} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", fontSize: 11 }}
                      />
                      <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Details Row (Strengths, Gaps, Recommendations) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Strengths */}
            <Card className="glass-panel border-zinc-800/40">
              <CardHeader className="border-b border-zinc-800/20 pb-3">
                <CardTitle className="text-sm font-semibold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Candidate Strengths
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <ul className="space-y-2 text-xs text-zinc-300">
                  {result.strengths?.map((str: string, index: number) => (
                    <li key={index} className="flex items-start gap-2 leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 mt-1.5" />
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {/* Gaps / Missing Skills */}
            <Card className="glass-panel border-zinc-800/40">
              <CardHeader className="border-b border-zinc-800/20 pb-3">
                <CardTitle className="text-sm font-semibold text-rose-400 flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4" /> Missing Skill Gaps
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                {result.missing_skills?.length === 0 ? (
                  <p className="text-xs text-zinc-500 italic">No missing skills detected! Complete overlap.</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {result.missing_skills?.map((skill: string, index: number) => (
                      <span
                        key={index}
                        className="text-[10px] font-semibold px-2 py-0.5 rounded border border-rose-500/20 bg-rose-500/10 text-rose-400"
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
                <CardTitle className="text-sm font-semibold text-zinc-100 flex items-center gap-1.5">
                  <Award className="w-4 h-4 text-violet-400" /> Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <ol className="space-y-2 text-xs text-zinc-300">
                  {result.recommendations?.map((rec: string, index: number) => (
                    <li key={index} className="flex items-start gap-2 leading-relaxed">
                      <span className="font-mono text-[10px] text-zinc-500 mt-0.5 font-bold shrink-0">{index + 1}.</span>
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
