"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  MessageSquare,
  Files,
  FileUser,
  BarChart3,
  Settings,
  Activity,
  RefreshCw,
  Sun,
  Moon,
  Cpu,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/store/settingsStore";

const LogoIcon = () => (
  <svg className="w-8 h-8 shrink-0 select-none" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logo-pink-purple" x1="0" y1="0" x2="0" y2="100" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#D65BB4" />
        <stop offset="100%" stopColor="#8b5cf6" />
      </linearGradient>
    </defs>

    {/* Left Brain Outline */}
    <path
      d="M 46,16 C 34,16 26,22 26,32 C 16,34 14,48 20,54 C 15,64 26,72 36,70 C 40,72 44,70 46,67"
      stroke="url(#logo-pink-purple)"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    
    {/* Right edge vertical line for brain */}
    <path
      d="M 46,16 L 46,45 M 46,51 L 46,67"
      stroke="url(#logo-pink-purple)"
      strokeWidth="2.5"
      strokeLinecap="round"
    />

    {/* Neural Connections */}
    <path
      d="M 46,48 C 38,48 38,42 42,38"
      stroke="#D65BB4"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <path d="M 41,39 L 34,33" stroke="#D65BB4" strokeWidth="2" strokeLinecap="round" />
    <circle cx="34" cy="33" r="2" fill="#D65BB4" />
    
    <path d="M 39,43 L 30,43" stroke="#D65BB4" strokeWidth="2" strokeLinecap="round" />
    <circle cx="30" cy="43" r="2" fill="#D65BB4" />

    <path d="M 44,47 L 35,53" stroke="#D65BB4" strokeWidth="2" strokeLinecap="round" />
    <circle cx="35" cy="53" r="2" fill="#D65BB4" />

    {/* Documents */}
    <path
      d="M 58,16 L 68,16 L 74,22 L 74,48 L 58,48 Z"
      stroke="#8b5cf6"
      strokeWidth="1.8"
      strokeLinejoin="round"
      opacity="0.5"
    />
    <path
      d="M 54,21 L 64,21 L 70,27 L 70,53 L 54,53 Z"
      stroke="#8b5cf6"
      strokeWidth="1.8"
      strokeLinejoin="round"
      opacity="0.8"
    />
    <path
      d="M 50,26 L 60,26 L 66,32 L 66,58 L 50,58 Z"
      stroke="url(#logo-pink-purple)"
      strokeWidth="2"
      strokeLinejoin="round"
    />
    
    {/* Content lines */}
    <line x1="54" y1="34" x2="62" y2="34" stroke="#22d3ee" strokeWidth="1.8" strokeLinecap="round" />
    <line x1="54" y1="40" x2="62" y2="40" stroke="#22d3ee" strokeWidth="1.8" strokeLinecap="round" />
    <line x1="54" y1="46" x2="62" y2="46" stroke="#22d3ee" strokeWidth="1.8" strokeLinecap="round" />
    <line x1="54" y1="52" x2="58" y2="52" stroke="#22d3ee" strokeWidth="1.8" strokeLinecap="round" />

    {/* Dots */}
    <circle cx="50" cy="65" r="1" fill="#8b5cf6" />
    <circle cx="54" cy="65" r="1" fill="#8b5cf6" />
    <circle cx="58" cy="65" r="1" fill="#8b5cf6" />

    {/* Network Graph */}
    <line x1="72" y1="72" x2="82" y2="58" stroke="#22d3ee" strokeWidth="1.8" />
    <line x1="72" y1="72" x2="88" y2="70" stroke="#22d3ee" strokeWidth="1.8" />
    <line x1="82" y1="58" x2="90" y2="60" stroke="#22d3ee" strokeWidth="1.8" />
    <line x1="82" y1="58" x2="88" y2="70" stroke="#22d3ee" strokeWidth="1.8" />
    <line x1="90" y1="60" x2="88" y2="70" stroke="#22d3ee" strokeWidth="1.8" />

    <circle cx="72" cy="72" r="3" fill="#22d3ee" />
    <circle cx="82" cy="58" r="3" fill="#22d3ee" />
    <circle cx="90" cy="60" r="3" fill="#22d3ee" />
    <circle cx="88" cy="70" r="3" fill="#22d3ee" />
  </svg>
);

export default function Sidebar() {
  const pathname = usePathname();
  const { health, fetchHealth, reloadBackend, isLoading } = useSettingsStore();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    fetchHealth();
    const isLight = document.documentElement.classList.contains("light");
    setTheme(isLight ? "light" : "dark");
    const collapsed = localStorage.getItem("sidebar_collapsed") === "true";
    setIsCollapsed(collapsed);
  }, [fetchHealth]);

  const handleCollapseToggle = () => {
    const nextCollapsed = !isCollapsed;
    setIsCollapsed(nextCollapsed);
    localStorage.setItem("sidebar_collapsed", String(nextCollapsed));
  };

  const toggleTheme = () => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.remove("dark");
      root.classList.add("light");
      setTheme("light");
    } else {
      root.classList.remove("light");
      root.classList.add("dark");
      setTheme("dark");
    }
  };

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "AI Chat", href: "/chat", icon: MessageSquare },
    { name: "Documents", href: "/documents", icon: Files },
    { name: "Resume Analyzer", href: "/resume", icon: FileUser },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Benchmarks", href: "/benchmarks", icon: Activity },
    { name: "Architecture", href: "/workflow", icon: Cpu },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  const isHealthy = health?.status === "healthy";

  if (pathname === "/") return null;

  return (
    <div
      className={cn(
        // Outer wrapper: owns the width transition and the p-3 inset margin
        "flex flex-col h-screen shrink-0 p-3 transition-all duration-300 ease-[var(--ease-smooth)]",
        isCollapsed ? "w-[4.75rem]" : "w-[17rem]"
      )}
    >
    <aside
      className={cn(
        // Glass panel floating inset — detaches from window edge
        "glass-panel rounded-2xl flex flex-col h-full overflow-hidden select-none relative",
      )}
    >
      {/* Top inner-highlight shimmer line (specular edge on rounded panel) */}
      <div
        className="absolute top-0 left-4 right-4 h-px pointer-events-none z-20"
        style={{
          background:
            "linear-gradient(to right, transparent, rgba(255,255,255,0.12) 20%, rgba(255,255,255,0.12) 80%, transparent)",
        }}
        aria-hidden
      />

      {/* ── Logo Header ─────────────────────────────────────────────────── */}
      <div
        className={cn(
          "p-5 flex items-center justify-between gap-3",
          "border-b border-[var(--glass-border)]",
          isCollapsed && "p-3.5 flex-col gap-2.5"
        )}
      >
        {!isCollapsed ? (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center shrink-0">
              <LogoIcon />
            </div>

            <div className="flex flex-col min-w-0">
              <div className="flex items-baseline font-bold text-sm tracking-wide select-none">
                <span className="text-white">Talent</span>
                <span className="text-[#D65BB4]">Mind</span>
                <span className="ml-1 text-[8px] px-1 py-0.5 rounded border border-[#22d3ee] text-[#22d3ee] font-extrabold uppercase leading-none self-center">AI</span>
              </div>
              <span className="text-[9px] text-zinc-400 font-medium leading-tight mt-1 select-none">
                Intelligent <span className="text-[#22d3ee]">Agents.</span> Smarter Decisions<span className="text-[#D65BB4]">.</span>
              </span>
            </div>
          </div>
        ) : (
          /* Collapsed logo */
          <div className="w-8 h-8 flex items-center justify-center shrink-0">
            <LogoIcon />
          </div>
        )}

        {/* Collapse toggle — glass icon button */}
        <button
          onClick={handleCollapseToggle}
          aria-label={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          className={cn(
            "relative p-1.5 rounded-lg shrink-0",
            "text-[rgba(160,145,175,0.80)]",
            "border border-transparent",
            "transition-all duration-200",
            "hover:bg-[var(--glass-fill)] hover:border-[var(--glass-border)]",
            "hover:text-white hover:shadow-[var(--glass-shadow-sm)]",
            "active:scale-90",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(214,91,180,0.45)]"
          )}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* ── Navigation ──────────────────────────────────────────────────── */}
      <nav
        className={cn(
          "flex-1 py-4 space-y-0.5 overflow-y-auto",
          isCollapsed ? "px-2" : "px-3"
        )}
      >
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              title={isCollapsed ? item.name : undefined}
              className={cn(
                "relative flex items-center gap-3 rounded-xl text-sm transition-all duration-200 group",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(214,91,180,0.45)]",
                isCollapsed ? "justify-center px-0 py-2.5" : "px-3 py-2.5",
                isActive
                  ? [
                      // Active: lit glass pill — primary tint + magenta glow
                      "bg-primary/15 border border-primary/25 text-primary font-medium",
                      "shadow-[0_0_20px_-4px_rgba(214,91,180,0.40)]",
                    ]
                  : [
                      // Inactive: ghost hover
                      "text-[rgba(160,145,175,0.80)]",
                      "hover:text-white",
                      "hover:bg-[var(--glass-fill)]",
                      "hover:border-[var(--glass-border-subtle)]",
                      "border border-transparent",
                    ]
              )}
            >
              <Icon
                className={cn(
                  "shrink-0 transition-transform duration-200",
                  isCollapsed ? "w-4.5 h-4.5" : "w-4 h-4",
                  !isActive && "group-hover:scale-110"
                )}
                strokeWidth={isActive ? 2.2 : 1.8}
              />
              {!isCollapsed && <span className="leading-none">{item.name}</span>}

              {/* Active indicator dot when collapsed */}
              {isCollapsed && isActive && (
                <span
                  className="absolute right-1 top-1 w-1.5 h-1.5 rounded-full"
                  style={{ background: "rgba(214,91,180,0.90)" }}
                  aria-hidden
                />
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── Bottom Status & Controls ─────────────────────────────────────── */}
      <div
        className={cn(
          "border-t border-[var(--glass-border)] space-y-3",
          isCollapsed ? "p-2.5" : "p-4"
        )}
        style={{ background: "rgba(0,0,0,0.12)" }}
      >
        {/* Connection status */}
        {!isCollapsed ? (
          <div
            className="flex items-center justify-between px-3 py-2 rounded-xl"
            style={{
              background: "var(--glass-fill-inset)",
              border: "1px solid var(--glass-border-subtle)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.18) inset",
            }}
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "w-2 h-2 rounded-full shrink-0",
                  isHealthy
                    ? "bg-emerald-400 animate-pulse-glow"
                    : "bg-rose-400"
                )}
                aria-label={isHealthy ? "API online" : "API offline"}
              />
              <span
                className="text-[11px] font-medium"
                style={{ color: isHealthy ? "rgba(110,231,183,0.90)" : "rgba(251,113,133,0.90)" }}
              >
                {isHealthy ? "API Connected" : "API Offline"}
              </span>
            </div>
            <button
              onClick={() => (isHealthy ? reloadBackend() : fetchHealth())}
              disabled={isLoading}
              aria-label={isHealthy ? "Reload configuration" : "Retry connection"}
              title={isHealthy ? "Reload Config & Services" : "Retry Connection"}
              className={cn(
                "p-1 rounded-lg transition-all duration-200",
                "text-[rgba(150,135,165,0.70)] hover:text-white",
                "hover:bg-[var(--glass-fill)] hover:shadow-[var(--glass-shadow-sm)]",
                "disabled:opacity-40 active:scale-90"
              )}
            >
              <RefreshCw
                className={cn("w-3.5 h-3.5", isLoading && "animate-spin")}
              />
            </button>
          </div>
        ) : (
          /* Collapsed status */
          <div
            className="flex flex-col items-center gap-2 py-2 rounded-xl"
            style={{
              background: "var(--glass-fill-inset)",
              border: "1px solid var(--glass-border-subtle)",
            }}
          >
            <span
              className={cn(
                "w-2 h-2 rounded-full shrink-0",
                isHealthy ? "bg-emerald-400 animate-pulse-glow" : "bg-rose-400"
              )}
              title={isHealthy ? "API Connected" : "API Offline"}
            />
            <button
              onClick={() => (isHealthy ? reloadBackend() : fetchHealth())}
              disabled={isLoading}
              aria-label={isHealthy ? "Reload configuration" : "Retry connection"}
              className={cn(
                "p-1 rounded-lg transition-all duration-200",
                "text-[rgba(150,135,165,0.70)] hover:text-white",
                "hover:bg-[var(--glass-fill)]",
                "disabled:opacity-40 active:scale-90"
              )}
            >
              <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
            </button>
          </div>
        )}

        {/* User profile + theme toggle */}
        <div
          className={cn(
            "flex items-center justify-between pt-1",
            isCollapsed && "flex-col gap-2 pt-0"
          )}
        >
          {/* Avatar */}
          <div className="flex items-center gap-2.5">
            <div
              className={cn(
                "relative w-7 h-7 rounded-full flex items-center justify-center",
                "font-bold text-xs text-white shrink-0"
              )}
              title="Operator Profile"
              style={{
                background:
                  "linear-gradient(135deg, rgba(102,65,92,0.90), rgba(60,40,55,0.95))",
                border: "1px solid var(--glass-border)",
                boxShadow:
                  "0 2px 8px rgba(0,0,0,0.30), 0 1px 0 rgba(255,255,255,0.10) inset",
              }}
            >
              U
            </div>
            {!isCollapsed && (
              <span
                className="text-xs font-medium"
                style={{ color: "rgba(190,175,205,0.85)" }}
              >
                Operator
              </span>
            )}
          </div>

          {/* Theme toggle — glass icon button */}
          <button
            onClick={toggleTheme}
            aria-label={
              theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"
            }
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className={cn(
              "relative p-1.5 rounded-lg overflow-hidden",
              "border border-transparent",
              "text-[rgba(160,145,175,0.80)] hover:text-white",
              "transition-all duration-200",
              "hover:bg-[var(--glass-fill)] hover:border-[var(--glass-border)]",
              "hover:shadow-[var(--glass-shadow-sm)]",
              "active:scale-90",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(214,91,180,0.45)]"
            )}
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </aside>
    </div>
  );
}
