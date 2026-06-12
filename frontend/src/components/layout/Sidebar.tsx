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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/store/settingsStore";

export default function Sidebar() {
  const pathname = usePathname();
  const { health, fetchHealth, reloadBackend, isLoading } = useSettingsStore();
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    // Initial fetch of health
    fetchHealth();
    
    // Check initial document body theme
    const isLight = document.documentElement.classList.contains("light");
    setTheme(isLight ? "light" : "dark");
  }, [fetchHealth]);

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
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "AI Chat", href: "/chat", icon: MessageSquare },
    { name: "Documents", href: "/documents", icon: Files },
    { name: "Resume Analyzer", href: "/resume", icon: FileUser },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Architecture", href: "/workflow", icon: Cpu },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  const isHealthy = health?.status === "healthy";

  return (
    <aside className="w-64 bg-zinc-950/80 border-r border-zinc-800/60 flex flex-col h-screen select-none relative backdrop-blur-md">
      {/* Header Logo */}
      <div className="p-6 border-b border-zinc-800/40 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center shadow-md shadow-violet-500/10">
          <span className="text-zinc-50 font-bold text-sm tracking-widest">AG</span>
        </div>
        <div className="flex flex-col">
          <span className="font-semibold text-zinc-100 text-sm leading-tight tracking-wide">Antigravity RAG</span>
          <span className="text-zinc-500 text-xs tracking-tight">Enterprise Agent</span>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 py-6 px-4 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm transition-all duration-200 group relative",
                isActive
                  ? "bg-primary text-primary-foreground font-medium shadow-sm shadow-primary/20"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/60"
              )}
            >
              <Icon className={cn("w-4.5 h-4.5 transition-transform", !isActive && "group-hover:scale-105")} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Bottom Observability & Settings */}
      <div className="p-4 border-t border-zinc-800/40 space-y-4 bg-zinc-950/40">
        {/* Connection status */}
        <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-900/40 border border-zinc-800/30">
          <div className="flex items-center gap-2">
            <span className={cn("w-2 h-2 rounded-full", isHealthy ? "bg-emerald-500 animate-pulse" : "bg-rose-500")} />
            <span className="text-[11px] text-zinc-400 font-medium">
              {isHealthy ? "API Connected" : "API Offline"}
            </span>
          </div>
          <button
            onClick={() => reloadBackend()}
            disabled={isLoading}
            className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-50"
            title="Reload Config & Services"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
          </button>
        </div>

        {/* Theme & User Profile Mock */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-zinc-800 flex items-center justify-center font-bold text-xs text-zinc-300 border border-zinc-700/50">
              U
            </div>
            <span className="text-xs font-medium text-zinc-300">Operator</span>
          </div>
          
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-zinc-100 transition-colors"
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </aside>
  );
}
