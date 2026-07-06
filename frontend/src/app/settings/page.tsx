"use client";

import { useEffect, useState } from "react";
import { useSettingsStore } from "@/store/settingsStore";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Settings,
  Cpu,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
} from "lucide-react";

// ── Inline stat chip (glass-inset surface) ─────────────────────────────
function StatChip({
  label,
  value,
  accentColor = "rgba(214,91,180,0.80)",
}: {
  label: string;
  value: string;
  accentColor?: string;
}) {
  return (
    <div
      className="flex flex-col p-4 rounded-2xl relative overflow-hidden"
      style={{
        background: "var(--glass-fill-inset)",
        border: "1px solid var(--glass-border-subtle)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.22) inset, 0 1px 0 rgba(255,255,255,0.06)",
      }}
    >
      {/* Subtle accent glow at bottom */}
      <div
        className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
        style={{
          background: `linear-gradient(to right, transparent, ${accentColor}, transparent)`,
          opacity: 0.40,
        }}
        aria-hidden
      />
      <span
        className="text-[9px] font-medium uppercase tracking-[0.12em] mb-2 text-muted-foreground"
      >
        {label}
      </span>
      <span className="text-[15px] font-semibold text-foreground uppercase tracking-wide">
        {value}
      </span>
    </div>
  );
}

// ── Data row ───────────────────────────────────────────────────────────
function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="flex justify-between items-center py-2.5"
      style={{ borderBottom: "1px solid var(--glass-border-subtle)" }}
    >
      <span className="text-sm text-foreground/80">
        {label}
      </span>
      <span
        className="font-mono text-xs text-foreground px-2.5 py-1 rounded-lg"
        style={{
          background: "var(--glass-fill-inset)",
          border: "1px solid var(--glass-border-subtle)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.18) inset",
        }}
      >
        {value}
      </span>
    </div>
  );
}

// ── Env variable entry ─────────────────────────────────────────────────
function EnvEntry({
  name,
  description,
  codes,
}: {
  name: string;
  description: React.ReactNode;
  codes?: string[];
}) {
  return (
    <div className="space-y-1.5">
      <h4
        className="font-medium font-mono text-xs tracking-wide text-foreground"
      >
        {name}
      </h4>
      <p className="text-xs leading-relaxed text-muted-foreground">
        {description}
        {codes && (
          <span className="inline-flex flex-wrap gap-1 mt-1.5">
            {codes.map((c) => (
              <code
                key={c}
                className="font-mono text-[11px] px-1.5 py-0.5 rounded-md text-foreground/90"
                style={{
                  background: "var(--glass-fill-inset)",
                  border: "1px solid var(--glass-border-subtle)",
                }}
              >
                {c}
              </code>
            ))}
          </span>
        )}
      </p>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────
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

  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const handleSyncBackend = async () => {
    setSuccessMessage(null);
    const success = await reloadBackend();
    if (success) {
      setSuccessMessage(
        "Backend configuration successfully reloaded from .env file!"
      );
      setTimeout(() => setSuccessMessage(null), 5000);
    }
  };

  const handleTestDiagnostics = async () => {
    setSuccessMessage(null);
    const success = await testConnection();
    if (success) {
      setSuccessMessage(
        "Diagnostics passed: FastAPI endpoints and vector stores are healthy!"
      );
      setTimeout(() => setSuccessMessage(null), 5000);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">

      {/* ── Page Header ───────────────────────────────────────────────── */}
      <div className="pb-5 relative">
        {/* Glass divider line */}
        <div
          className="absolute bottom-0 left-0 right-0 h-px"
          style={{
            background:
              "linear-gradient(to right, transparent, var(--glass-border-strong) 20%, var(--glass-border-strong) 80%, transparent)",
          }}
          aria-hidden
        />
        <h1 className="text-[28px] font-semibold tracking-tight text-foreground flex items-center gap-3 mb-1">
          <span
            className="inline-flex items-center justify-center w-9 h-9 rounded-xl"
            style={{
              background: "var(--glass-fill-elevated)",
              border: "1px solid var(--glass-border)",
              boxShadow: "var(--glass-shadow-sm)",
            }}
          >
            <Settings className="w-4.5 h-4.5 text-primary" />
          </span>
          Settings
        </h1>
        <p className="text-sm ml-12 text-muted-foreground">
          Manage LLM engines, synchronize environment keys, and test service connections.
        </p>
      </div>

      {/* ── Main Grid ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Left column (2/3): Active Config + Diagnostics ──────────── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Active Model Orchestrator Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2.5">
                <span
                  className="inline-flex items-center justify-center w-7 h-7 rounded-lg shrink-0"
                  style={{
                    background: "rgba(139,92,246,0.12)",
                    border: "1px solid rgba(139,92,246,0.20)",
                  }}
                >
                  <Cpu className="w-3.5 h-3.5 text-primary" />
                </span>
                Active Model Orchestrator
              </CardTitle>
              <CardDescription
                className="text-xs ml-9 text-muted-foreground"
              >
                Active provider configuration loaded in server runtime memory.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-5">
              {/* Stat chips — glass inset surfaces */}
              <div className="grid grid-cols-2 gap-3">
                <StatChip
                  label="AI LLM Provider"
                  value={health?.llm_provider || "Unknown"}
                  accentColor="rgba(167,139,250,0.80)"
                />
                <StatChip
                  label="Vector Database"
                  value={health?.vector_store || "chromadb"}
                  accentColor="rgba(34,211,238,0.80)"
                />
              </div>

              {/* Data rows */}
              <div className="space-y-0 pt-1">
                <DataRow
                  label="Synthesis LLM Model"
                  value={health?.llm_model || "None"}
                />
                <DataRow
                  label="Vector Embedding Model"
                  value={health?.embedding_model || "None"}
                />
                <div
                  className="flex justify-between items-center py-2.5"
                >
                  <span className="text-sm text-foreground/80">
                    Documents Vectorized
                  </span>
                  <span
                    className="text-sm font-semibold text-foreground"
                  >
                    {health?.documents_indexed ?? 0}
                    <span
                      className="text-xs font-normal ml-1 text-muted-foreground/75"
                    >
                      documents
                    </span>
                  </span>
                </div>
              </div>
            </CardContent>

            <CardFooter className="flex justify-between items-center gap-4">
              <span
                className="text-[11px] leading-relaxed max-w-[65%] text-muted-foreground/70"
              >
                Settings are set by <code className="font-mono">.env</code> variables at server
                boot. Modify <code className="font-mono">.env</code> on disk to update.
              </span>
              <Button
                variant="outline"
                size="sm"
                className="flex items-center gap-1.5 shrink-0"
                onClick={handleSyncBackend}
                loading={isLoading}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Sync with .env
              </Button>
            </CardFooter>
          </Card>

          {/* System Connectivity & Diagnostics Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2.5">
                <span
                  className="inline-flex items-center justify-center w-7 h-7 rounded-lg shrink-0"
                  style={{
                    background: "rgba(52,211,153,0.12)",
                    border: "1px solid rgba(52,211,153,0.22)",
                  }}
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                </span>
                System Connectivity &amp; Diagnostics
              </CardTitle>
              <CardDescription
                className="text-xs ml-9 text-muted-foreground"
              >
                Check connection status of LLM API gateways and local embedding pipelines.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Error alert */}
              {error && (
                <div className="glass-alert glass-alert-error flex items-start gap-3 pl-6">
                  <XCircle
                    className="w-4 h-4 shrink-0 mt-0.5"
                    style={{ color: "rgba(251,113,133,0.95)" }}
                  />
                  <div className="text-xs leading-relaxed">
                    <span
                      className="font-semibold block mb-0.5"
                      style={{ color: "rgba(251,113,133,0.95)" }}
                    >
                      Sync / Diagnostic Error
                    </span>
                    <span style={{ color: "rgba(220,170,180,0.85)" }}>{error}</span>
                  </div>
                </div>
              )}

              {/* Success alert */}
              {successMessage && (
                <div className="glass-alert glass-alert-success flex items-start gap-3 pl-6">
                  <CheckCircle2
                    className="w-4 h-4 shrink-0 mt-0.5"
                    style={{ color: "rgba(52,211,153,0.95)" }}
                  />
                  <div className="text-xs leading-relaxed">
                    <span
                      className="font-semibold block mb-0.5"
                      style={{ color: "rgba(52,211,153,0.95)" }}
                    >
                      Success
                    </span>
                    <span style={{ color: "rgba(170,220,200,0.85)" }}>{successMessage}</span>
                  </div>
                </div>
              )}

              {/* Status rows */}
              <div className="space-y-0">
                <div
                  className="flex justify-between items-center py-2.5"
                  style={{ borderBottom: "1px solid var(--glass-border-subtle)" }}
                >
                  <span className="text-sm text-foreground/80">
                    Connection Status
                  </span>
                  <span className="flex items-center gap-1.5 text-sm font-semibold">
                    {connectionStatus === "testing" ? (
                      <span className="text-amber-500">Testing…</span>
                    ) : connectionStatus === "success" ? (
                      <span
                        className="flex items-center gap-1 text-emerald-500"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Normal
                      </span>
                    ) : connectionStatus === "failed" ? (
                      <span
                        className="flex items-center gap-1 text-rose-500"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Unhealthy
                      </span>
                    ) : (
                      <span className="text-muted-foreground/60">Idle</span>
                    )}
                  </span>
                </div>

                <div className="flex justify-between items-center py-2.5">
                  <span className="text-sm text-foreground/80">
                    Response Code Latency
                  </span>
                  <span
                    className="font-mono text-xs text-foreground/70"
                  >
                    FastAPI Ping: ~2ms
                  </span>
                </div>
              </div>
            </CardContent>

            <CardFooter>
              <Button
                variant="primary"
                size="default"
                className="w-full"
                onClick={handleTestDiagnostics}
                loading={connectionStatus === "testing"}
              >
                Run Diagnostics Test
              </Button>
            </CardFooter>
          </Card>
        </div>

        {/* ── Right column (1/3): Env Config Guide ────────────────────── */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2.5">
                <span
                  className="inline-flex items-center justify-center w-7 h-7 rounded-lg shrink-0"
                  style={{
                    background: "rgba(34,211,238,0.10)",
                    border: "1px solid rgba(34,211,238,0.20)",
                  }}
                >
                  <HelpCircle
                    className="w-3.5 h-3.5 text-sky-500"
                  />
                </span>
                Env Config Guide
              </CardTitle>
              <CardDescription
                className="text-xs ml-9 text-muted-foreground"
              >
                Edit variables by opening <code className="font-mono">.env</code> at project root.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-5">
              <EnvEntry
                name="LLM_PROVIDER"
                description="Specifies active orchestrator:"
                codes={["gemini", "groq", "ollama"]}
              />
              <div
                className="h-px"
                style={{ background: "var(--glass-border-subtle)" }}
                aria-hidden
              />
              <EnvEntry
                name="EMBEDDING_PROVIDER"
                description="Specifies vector parsing engine:"
                codes={["local", "gemini", "ollama"]}
              />
              <div
                className="h-px"
                style={{ background: "var(--glass-border-subtle)" }}
                aria-hidden
              />
              <EnvEntry
                name="GOOGLE_API_KEY"
                description="Used for active Gemini models. Must be a valid Gemini API key format."
              />
              <div
                className="h-px"
                style={{ background: "var(--glass-border-subtle)" }}
                aria-hidden
              />
              <EnvEntry
                name="OLLAMA_BASE_URL"
                description="URL of running local Ollama service, default:"
                codes={["http://localhost:11434"]}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
