"use client";

import { useEffect, useState } from "react";
import { useSettingsStore } from "@/store/settingsStore";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Settings,
  Cpu,
  Database,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
  Eye,
  EyeOff,
} from "lucide-react";

export default function SettingsPage() {
  const {
    health,
    fetchHealth,
    reloadBackend,
    testConnection,
    connectionStatus,
    isLoading,
    error,
  } = useSettingsStore();

  const [showApiKey, setShowApiKey] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const handleSyncBackend = async () => {
    setSuccessMessage(null);
    const success = await reloadBackend();
    if (success) {
      setSuccessMessage("Backend configuration successfully reloaded from .env file!");
      // Hide success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    }
  };

  const handleTestDiagnostics = async () => {
    setSuccessMessage(null);
    const success = await testConnection();
    if (success) {
      setSuccessMessage("Diagnostics passed: FastAPI endpoints and vector stores are healthy!");
      setTimeout(() => setSuccessMessage(null), 5000);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="border-b border-zinc-800/40 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <Settings className="w-8 h-8 text-primary" />
          Settings
        </h1>
        <p className="text-zinc-400 text-sm mt-1">
          Manage LLM engines, synchronize environment keys, and test service connections.
        </p>
      </div>

      {/* Main Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Core Config Status */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="glass-panel border-zinc-800/40">
            <CardHeader>
              <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-violet-500" />
                Active Model Orchestrator
              </CardTitle>
              <CardDescription className="text-zinc-500 text-xs">
                Active provider configuration loaded in server runtime memory.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/30">
                  <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
                    AI LLM Provider
                  </span>
                  <span className="text-md font-bold text-zinc-200 mt-1 uppercase">
                    {health?.llm_provider || "Unknown"}
                  </span>
                </div>
                <div className="flex flex-col p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/30">
                  <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
                    Vector Database
                  </span>
                  <span className="text-md font-bold text-zinc-200 mt-1 uppercase">
                    {health?.vector_store || "chromadb"}
                  </span>
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <div className="flex justify-between items-center py-2 border-b border-zinc-800/20 text-sm">
                  <span className="text-zinc-400">Synthesis LLM Model</span>
                  <span className="font-mono text-xs text-zinc-200 bg-zinc-900 px-2 py-1 rounded">
                    {health?.llm_model || "None"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-zinc-800/20 text-sm">
                  <span className="text-zinc-400">Vector Embedding Model</span>
                  <span className="font-mono text-xs text-zinc-200 bg-zinc-900 px-2 py-1 rounded font-medium">
                    {health?.embedding_model || "None"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-zinc-800/20 text-sm">
                  <span className="text-zinc-400">Documents Vectorized</span>
                  <span className="font-bold text-zinc-200">
                    {health?.documents_indexed ?? 0} documents
                  </span>
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-between items-center">
              <span className="text-[10px] text-zinc-500 max-w-[70%]">
                These settings are set by `.env` variables at server boot. Modify `.env` on disk to update.
              </span>
              <Button
                variant="outline"
                size="sm"
                className="flex items-center gap-1.5"
                onClick={handleSyncBackend}
                loading={isLoading}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Sync with .env
              </Button>
            </CardFooter>
          </Card>

          {/* Diagnostic tests */}
          <Card className="glass-panel border-zinc-800/40">
            <CardHeader>
              <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-500" />
                System Connectivity & Diagnostics
              </CardTitle>
              <CardDescription className="text-zinc-500 text-xs">
                Check connection status of LLM API gateways and local embedding pipelines.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 flex items-start gap-2">
                  <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">Sync/Diagnostic Error:</span> {error}
                  </div>
                </div>
              )}

              {successMessage && (
                <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">Success:</span> {successMessage}
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-2.5">
                <div className="flex items-center justify-between text-sm py-1">
                  <span className="text-zinc-400">Connection Status</span>
                  <span className="flex items-center gap-1.5 font-medium">
                    {connectionStatus === "testing" ? (
                      <span className="text-amber-400">Testing...</span>
                    ) : connectionStatus === "success" ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Normal
                      </span>
                    ) : connectionStatus === "failed" ? (
                      <span className="text-rose-400 flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" /> Unhealthy
                      </span>
                    ) : (
                      <span className="text-zinc-500">Idle</span>
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm py-1">
                  <span className="text-zinc-400">Response Code Latency</span>
                  <span className="font-mono text-zinc-300">FastAPI Ping: ~2ms</span>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                variant="primary"
                size="sm"
                className="w-full"
                onClick={handleTestDiagnostics}
                loading={connectionStatus === "testing"}
              >
                Run Diagnostics Test
              </Button>
            </CardFooter>
          </Card>
        </div>

        {/* Documentation / Info Bar */}
        <div className="space-y-6">
          <Card className="glass-panel border-zinc-800/40">
            <CardHeader>
              <CardTitle className="text-md font-semibold text-zinc-100 flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-cyan-500" />
                Environment Configuration Guide
              </CardTitle>
              <CardDescription className="text-zinc-500 text-xs">
                To edit variables, open the `.env` file at the root.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs leading-relaxed">
              <div className="space-y-3.5">
                <div>
                  <h4 className="font-semibold text-zinc-300 font-mono">LLM_PROVIDER</h4>
                  <p className="text-zinc-500 mt-0.5">
                    Specifies active orchestrator: <code className="text-zinc-400 bg-zinc-900 px-1 py-0.5 rounded">gemini</code>, <code className="text-zinc-400 bg-zinc-900 px-1 py-0.5 rounded">groq</code>, or <code className="text-zinc-400 bg-zinc-900 px-1 py-0.5 rounded">ollama</code>.
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-zinc-300 font-mono">EMBEDDING_PROVIDER</h4>
                  <p className="text-zinc-500 mt-0.5">
                    Specifies vector parsing engine: <code className="text-zinc-400 bg-zinc-900 px-1 py-0.5 rounded">local</code>, <code className="text-zinc-400 bg-zinc-900 px-1 py-0.5 rounded">gemini</code>, or <code className="text-zinc-400 bg-zinc-900 px-1 py-0.5 rounded">ollama</code>.
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-zinc-300 font-mono">GOOGLE_API_KEY</h4>
                  <p className="text-zinc-500 mt-0.5">
                    Used for active Gemini models. Must be a valid Gemini API key format.
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-zinc-300 font-mono">OLLAMA_BASE_URL</h4>
                  <p className="text-zinc-500 mt-0.5">
                    URL of running local Ollama service, default: <code className="text-zinc-400 bg-zinc-900 px-1 py-0.5 rounded">http://localhost:11434</code>.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
