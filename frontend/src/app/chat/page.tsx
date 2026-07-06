"use client";

import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import Markdown from "@/components/chat/Markdown";
import ObservabilityPanel from "@/components/chat/ObservabilityPanel";
import SourceCards from "@/components/chat/SourceCards";
import {
  Plus,
  Trash2,
  Send,
  Sparkles,
  Bot,
  User,
  Copy,
  Check,
  RotateCcw,
  MessageSquare,
  AlertCircle,
  Cpu,
  Globe,
  Settings as SettingsIcon,
  HelpCircle,
  Activity,
  History,
  Coins,
  Files,
  ChevronLeft,
  ChevronRight,
  Search,
  X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn, formatDateTime } from "@/lib/utils";
import Link from "next/link";

export default function ChatPage() {
  const {
    sessions,
    activeSessionId,
    messages,
    isGenerating,
    isStreaming,
    error,
    currentLatency,
    currentTokens,
    currentDecision,
    currentSources,
    fetchSessions,
    selectSession,
    deleteSession,
    createNewSession,
    sendMessage,
  } = useChatStore();

  const { useWebSearch, setUseWebSearch, health, fetchHealth } = useSettingsStore();

  // Fetch Documents list to determine status
  const { data: documentsData } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(),
    refetchInterval: 8000, // Sync every 8s
  });

  const documents = documentsData?.documents || [];
  const indexedDocumentsCount = documents.filter((doc) => doc.status === "indexed").length;

  const [input, setInput] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  
  // Document selection states
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [isDocDropdownOpen, setIsDocDropdownOpen] = useState(false);
  const [docSearchQuery, setDocSearchQuery] = useState("");

  // Collapsible Session sidebar state
  const [isSessionSidebarCollapsed, setIsSessionSidebarCollapsed] = useState(false);

  // Observability Panel toggle state
  const [showObservability, setShowObservability] = useState(true);

  const toggleDocSelection = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const clearDocSelection = () => setSelectedDocIds([]);

  const examplePrompts = [
    "Summarize Resume.pdf",
    "Compare Resume.pdf with JD.pdf",
    "Extract key skills from uploaded documents",
    "What requirements are mentioned in the JD?",
    "Review my resume against the uploaded job description",
  ];

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchSessions();
    fetchHealth();
  }, [fetchSessions, fetchHealth]);

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [messages, isGenerating]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating || isStreaming) return;

    const query = input;
    setInput("");
    await sendMessage(query, useWebSearch, selectedDocIds.length > 0 ? selectedDocIds : undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  const handleCopy = async (text: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(idx);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error("Failed to copy message text:", err);
    }
  };

  const handleRegenerate = async (index: number) => {
    if (isGenerating || isStreaming) return;

    let lastUserQuery = "";
    for (let i = index; i >= 0; i--) {
      if (messages[i].role === "user") {
        lastUserQuery = messages[i].content;
        break;
      }
    }

    if (lastUserQuery) {
      useChatStore.setState({
        messages: messages.slice(0, index),
      });
      await sendMessage(lastUserQuery, useWebSearch, selectedDocIds.length > 0 ? selectedDocIds : undefined);
    }
  };

  // Determine active provider details
  const activeProvider = health?.llm_provider?.toLowerCase() || "ollama";
  const activeModel = health?.llm_model || "llama3.2";
  const lastLatency = currentLatency.total || currentLatency.total_latency_ms || null;
  const lastTokens = currentTokens?.total || null;

  return (
    <div className="flex-1 flex h-full overflow-hidden">
      {/* 1. Chat Sessions Sidebar */}
      <div className={cn(
        "bg-zinc-950/40 border-r border-zinc-800/40 flex flex-col shrink-0 h-full backdrop-blur-sm transition-all duration-300 ease-in-out relative",
        isSessionSidebarCollapsed ? "w-12" : "w-64"
      )}>
        {isSessionSidebarCollapsed ? (
          <div className="p-2 border-b border-zinc-800/20 flex flex-col items-center gap-3">
            <button
              onClick={() => setIsSessionSidebarCollapsed(false)}
              className="p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-zinc-150 transition-colors"
              title="Expand Sessions"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              onClick={createNewSession}
              className="w-8 h-8 rounded-lg border border-zinc-800/60 flex items-center justify-center hover:border-primary/40 hover:bg-zinc-900/60 transition-all"
              title="New Chat"
            >
              <Plus className="w-4 h-4 text-primary" />
            </button>
          </div>
        ) : (
          <div className="p-4 border-b border-zinc-800/20 flex items-center justify-between gap-2">
            <Button
              onClick={createNewSession}
              variant="outline"
              className="flex-1 flex items-center justify-center gap-1.5 font-semibold hover:border-primary/40 hover:bg-zinc-900/60 text-xs py-1.5 h-9"
            >
              <Plus className="w-4 h-4 text-primary" />
              New Chat
            </Button>
            <button
              onClick={() => setIsSessionSidebarCollapsed(true)}
              className="p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-zinc-100 transition-colors"
              title="Collapse Sessions"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Sessions list */}
        {!isSessionSidebarCollapsed && (
          <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
            {sessions.length === 0 ? (
              <div className="text-center py-8 text-zinc-650 text-xs font-medium">
                No sessions found
              </div>
            ) : (
              sessions.map((s) => {
                const isActive = activeSessionId === s.session_id;
                return (
                  <div
                    key={s.session_id}
                    className={cn(
                      "flex items-center justify-between group rounded-lg p-2.5 text-xs transition-all duration-150 cursor-pointer border",
                      isActive
                        ? "bg-zinc-900/80 border-zinc-800/80 text-zinc-200"
                        : "border-transparent text-zinc-450 hover:text-zinc-250 hover:bg-zinc-900/20"
                    )}
                    onClick={() => selectSession(s.session_id)}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <MessageSquare className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-350" />
                      <span className="truncate font-medium">
                        {s.title || `Chat Session ${s.session_id.substring(0, 6)}`}
                      </span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(s.session_id);
                      }}
                      className="opacity-0 group-hover:opacity-100 hover:text-rose-400 p-0.5 rounded transition-opacity"
                      title="Delete Session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* 2. Main Chat viewport */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-zinc-900/10 min-w-0 relative">
        {/* Top Provider Control Center Header */}
        <header className="h-16 border-b border-zinc-800/40 flex items-center justify-between px-6 shrink-0 bg-zinc-950/20 backdrop-blur-md z-20">
          <div className="flex items-center gap-4">
            {/* Active Provider Badge Switcher */}
            <div className="flex items-center gap-2 p-1.5 rounded-lg bg-zinc-900/40 border border-zinc-850/40 text-xs">
              <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-950/40 border border-zinc-850/40">
                <span
                  className={cn("w-2 h-2 rounded-full", {
                    "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)] animate-pulse":
                      activeProvider === "ollama",
                    "bg-violet-500 shadow-[0_0_8px_rgba(139,92,246,0.4)] animate-pulse":
                      activeProvider === "gemini",
                    "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.4)] animate-pulse":
                      activeProvider === "groq",
                  })}
                />
                <span className="font-bold text-zinc-300 uppercase tracking-wide">
                  {activeProvider}
                </span>
              </div>
              <span className="text-[10px] text-zinc-500 font-mono tracking-tight hidden md:inline truncate max-w-[100px]">
                {activeModel.split("/").pop()}
              </span>
            </div>

            {/* Quick Metrics display */}
            {lastLatency !== null && (
              <div className="hidden sm:flex items-center gap-4 text-[10px] text-zinc-500 font-mono">
                <div className="flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5 text-zinc-650" />
                  <span>Latency: {lastLatency.toFixed(0)}ms</span>
                </div>
                <div className="flex items-center gap-1">
                  <Coins className="w-3.5 h-3.5 text-zinc-650" />
                  <span>Tokens: {lastTokens}</span>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* Document Status Indicator */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-zinc-900/40 border border-zinc-850/40 text-xs">
              <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", indexedDocumentsCount > 0 ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)] animate-pulse" : "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]")} />
              <span className="font-mono text-[10px] text-zinc-400 uppercase tracking-wider">
                Indexed Documents: <span className="font-bold text-zinc-250 font-sans normal-case text-xs">{indexedDocumentsCount}</span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Document Filter Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsDocDropdownOpen(!isDocDropdownOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zinc-900/40 border border-zinc-850/40 text-xs text-zinc-350 hover:text-zinc-200 hover:bg-zinc-850/30 transition-all font-medium select-none"
              >
                <Files className="w-3.5 h-3.5 text-primary" />
                <span>
                  {selectedDocIds.length === 0
                    ? "All Documents"
                    : `${selectedDocIds.length} Document${selectedDocIds.length > 1 ? "s" : ""}`}
                </span>
              </button>

              <AnimatePresence>
                {isDocDropdownOpen && (
                  <>
                    {/* Backdrop to close */}
                    <div
                      className="fixed inset-0 z-30"
                      onClick={() => {
                        setIsDocDropdownOpen(false);
                        setDocSearchQuery("");
                      }}
                    />
                    <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 mt-2 w-72 bg-zinc-950 border border-zinc-800 rounded-xl shadow-2xl p-3 z-40 space-y-2.5 glass-panel"
                    >
                      <div className="flex items-center justify-between border-b border-zinc-800/60 pb-2">
                        <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider select-none">
                          Filter Knowledge Base
                        </span>
                        {selectedDocIds.length > 0 && (
                          <button
                            type="button"
                            onClick={() => {
                              clearDocSelection();
                              setDocSearchQuery("");
                            }}
                            className="text-[10px] text-primary hover:underline font-semibold"
                          >
                            Reset to All
                          </button>
                        )}
                      </div>

                      {/* Search Bar */}
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
                        <input
                          type="text"
                          placeholder="Search files..."
                          value={docSearchQuery}
                          onChange={(e) => setDocSearchQuery(e.target.value)}
                          className="w-full bg-zinc-900 border border-zinc-850 rounded-lg pl-8 pr-7 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-primary/50 transition-colors"
                        />
                        {docSearchQuery && (
                          <button
                            type="button"
                            onClick={() => setDocSearchQuery("")}
                            className="absolute right-2 top-2 p-0.5 hover:bg-zinc-850 rounded text-zinc-500 hover:text-zinc-300 transition-colors animate-fade-in"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1 custom-scrollbar">
                        {(() => {
                          const indexedDocs = documents.filter((doc) => doc.status === "indexed");
                          
                          if (indexedDocs.length === 0) {
                            return (
                              <div className="text-center py-6 text-zinc-500 text-xs">
                                No indexed documents available
                              </div>
                            );
                          }

                          const filteredDocs = indexedDocs.filter((doc) =>
                            doc.filename.toLowerCase().includes(docSearchQuery.toLowerCase())
                          );

                          if (filteredDocs.length === 0) {
                            return (
                              <div className="text-center py-6 text-zinc-500 text-xs">
                                No matching documents found
                              </div>
                            );
                          }

                          return filteredDocs.map((doc) => {
                            const isSelected = selectedDocIds.includes(doc.document_id);
                            const displayFilename = doc.filename.replace(/^[a-fA-F0-9]{32}_/i, "");
                            
                            return (
                              <label
                                key={doc.document_id}
                                className={cn(
                                  "flex items-start gap-2.5 p-2 rounded-lg cursor-pointer transition-colors text-xs border border-transparent",
                                  isSelected
                                    ? "bg-primary/5 border-primary/20 text-zinc-200"
                                    : "hover:bg-zinc-900/60 text-zinc-400 hover:text-zinc-300"
                                )}
                              >
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleDocSelection(doc.document_id)}
                                  className="rounded border-zinc-700 bg-zinc-900 text-primary focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5 mt-0.5"
                                />
                                <div className="flex-1 min-w-0">
                                  <p className="font-semibold truncate" title={doc.filename}>
                                    {displayFilename}
                                  </p>
                                  <p className="text-[9px] text-zinc-550 font-mono mt-0.5">
                                    {doc.num_chunks} chunks
                                  </p>
                                </div>
                              </label>
                            );
                          });
                        })()}
                      </div>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>

            {/* Use Web search check */}
            <label className="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={useWebSearch}
                onChange={(e) => setUseWebSearch(e.target.checked)}
                className="rounded border-zinc-750 bg-zinc-950 text-primary focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5"
              />
              <span className="font-medium text-zinc-350 hover:text-zinc-200 transition-colors">Web Search</span>
            </label>

            {/* Toggle Observability Center */}
            <button
              type="button"
              onClick={() => setShowObservability(!showObservability)}
              className={cn(
                "p-1.5 rounded-lg border text-[11px] font-semibold flex items-center gap-1.5 transition-all select-none h-8",
                showObservability
                  ? "bg-primary/10 border-primary/20 text-primary shadow-[0_0_8px_rgba(214,91,180,0.15)]"
                  : "bg-zinc-900/40 border-zinc-850/40 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/30"
              )}
              title={showObservability ? "Hide Observability Center" : "Show Observability Center"}
            >
              <Activity className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">Observability</span>
            </button>

            <Link href="/settings">
              <Button variant="ghost" size="icon" className="w-8 h-8 rounded-lg" title="Provider Settings">
                <SettingsIcon className="w-4 h-4 text-zinc-400" />
              </Button>
            </Link>
          </div>
        </header>

        {/* Warning Banner when no documents are indexed */}
        {indexedDocumentsCount === 0 && (
          <div className="bg-rose-500/5 border-b border-rose-500/15 px-6 py-2.5 flex items-center gap-2.5 text-xs text-rose-450 shrink-0 z-10 select-none">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>
              No indexed documents found. Upload files in the{" "}
              <Link href="/documents" className="underline font-bold hover:text-rose-400 transition-colors">
                Documents
              </Link>{" "}
              section to enable document-based answers.
            </span>
          </div>
        )}

        {/* Message bubble stream */}
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto w-full min-h-full flex flex-col justify-between">
            {messages.length === 0 && !isGenerating ? (
              <div className="flex-1 flex flex-col justify-center items-center text-center relative py-12">
                {/* Glow background */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-violet-600/5 rounded-full blur-3xl pointer-events-none" />
                
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4 }}
                  className="flex flex-col items-center w-full"
                >
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-violet-500/15 mb-4 animate-float">
                  <Sparkles className="w-6 h-6 text-zinc-100" />
                </div>
                <h2 className="text-lg font-bold text-zinc-200">How can I assist you today?</h2>
                <p className="text-zinc-500 text-xs mt-2 max-w-sm leading-relaxed">
                  Scan indexed PDF/Word documents, query local databases, or activate the Web Agent to perform search diagnostics.
                </p>

                {/* Quick Start Guide Onboarding */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15, duration: 0.4 }}
                  className="w-full mt-8 p-5 rounded-2xl border border-zinc-850/65 bg-zinc-950/20 backdrop-blur-md text-left space-y-4"
                >
                  <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2 select-none">
                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                    Quick Start Guide
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div className="space-y-2.5 p-4 rounded-xl bg-zinc-900/35 border border-zinc-900/60 flex flex-col justify-between backdrop-blur-sm">
                      <div>
                        <div className="text-[10px] font-bold text-primary uppercase tracking-wider mb-1">Step 1</div>
                        <p className="text-zinc-250 font-semibold mb-1">Upload Files</p>
                        <p className="text-zinc-500 text-[11px] leading-relaxed">
                          Go to the registry and upload your PDF, DOCX, or TXT credentials.
                        </p>
                      </div>
                      <Link href="/documents" className="mt-3 block">
                        <Button variant="outline" className="w-full text-[10px] py-1 h-7.5 rounded-lg border-zinc-800 hover:bg-zinc-800 text-zinc-350 transition-colors">
                          Go to Upload
                        </Button>
                      </Link>
                    </div>
                    
                    <div className="space-y-2.5 p-4 rounded-xl bg-zinc-900/35 border border-zinc-900/60 flex flex-col justify-between backdrop-blur-sm">
                      <div>
                        <div className="text-[10px] font-bold text-primary uppercase tracking-wider mb-1">Step 2</div>
                        <p className="text-zinc-250 font-semibold mb-1">Index Document</p>
                        <p className="text-zinc-500 text-[11px] leading-relaxed">
                          Click **Index Document** to trigger the AI semantic chunking and vector parsing pipeline.
                        </p>
                      </div>
                      <Link href="/documents" className="mt-3 block">
                        <Button variant="outline" className="w-full text-[10px] py-1 h-7.5 rounded-lg border-zinc-800 hover:bg-zinc-800 text-zinc-350 transition-colors">
                          Go to Index
                        </Button>
                      </Link>
                    </div>
                    
                    <div className="space-y-2.5 p-4 rounded-xl bg-zinc-900/35 border border-zinc-900/60 flex flex-col justify-between backdrop-blur-sm">
                      <div>
                        <div className="text-[10px] font-bold text-primary uppercase tracking-wider mb-1">Step 3</div>
                        <p className="text-zinc-250 font-semibold mb-1">Query Database</p>
                        <p className="text-zinc-500 text-[11px] leading-relaxed">
                          Return to the chat interface and run search diagnostics or fit check questions.
                        </p>
                      </div>
                      <div className="mt-3">
                        <Button 
                          onClick={() => inputRef.current?.focus()} 
                          variant="outline" 
                          className="w-full text-[10px] py-1 h-7.5 rounded-lg border-zinc-800 hover:bg-zinc-800 text-zinc-350 transition-colors"
                        >
                          Focus Chat Input
                        </Button>
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Example Prompts */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.4 }}
                  className="w-full mt-6 text-left"
                >
                  <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 select-none">
                    Suggested Prompts
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 select-none">
                    {examplePrompts.map((prompt, i) => (
                      <motion.button
                        key={i}
                        whileHover={{ scale: 1.005, translateY: -1.5 }}
                        whileTap={{ scale: 0.995 }}
                        onClick={() => {
                          setInput(prompt);
                          inputRef.current?.focus();
                        }}
                        className="p-3.5 rounded-xl border border-zinc-850/60 bg-zinc-950/20 hover:bg-zinc-900/40 hover:border-zinc-800 transition-all text-left flex items-start gap-2.5 text-xs text-zinc-450 hover:text-zinc-250 group glass-panel"
                      >
                        <MessageSquare className="w-3.5 h-3.5 text-zinc-650 group-hover:text-primary transition-colors mt-0.5 shrink-0" />
                        <span className="leading-relaxed">{prompt}</span>
                      </motion.button>
                    ))}
                  </div>
                </motion.div>
              </motion.div>
            </div>
          ) : (
            <div className="space-y-6 w-full pb-6">
              <AnimatePresence initial={false}>
                {messages.map((msg, idx) => {
                  const isUser = msg.role === "user";
                  return (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={cn("flex gap-4", isUser ? "justify-end" : "justify-start")}
                    >
                      {!isUser && (
                        <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0 shadow-sm">
                          <Bot className="w-4 h-4 text-violet-400" />
                        </div>
                      )}

                      <Card
                        className={cn(
                          "max-w-[85%] px-4 py-3 border-zinc-850/40 relative group shadow-sm",
                          isUser
                            ? "bg-zinc-800/70 text-zinc-100 border-zinc-750 rounded-br-none"
                            : "bg-zinc-900/50 text-zinc-350 rounded-bl-none glass-panel"
                        )}
                        glass={!isUser}
                      >
                        <div className="select-text">
                          {isUser ? (
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                          ) : (
                            <div className="space-y-4">
                              <Markdown content={msg.content} />
                              {(() => {
                                const isLastMessage = idx === messages.length - 1;
                                const sources = isLastMessage && (isGenerating || isStreaming)
                                  ? currentSources
                                  : msg.metadata?.sources || [];
                                
                                if (sources && sources.length > 0) {
                                  return <SourceCards sources={sources} />;
                                }
                                return null;
                              })()}
                            </div>
                          )}
                        </div>

                        {/* Copy / Regenerate controls */}
                        {!isUser && !msg.isStreaming && (
                          <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1.5 absolute -bottom-7 right-2 transition-opacity duration-200 bg-zinc-950/80 border border-zinc-850/60 px-2 py-0.5 rounded-full shadow backdrop-blur-sm z-10">
                            <button
                              onClick={() => handleCopy(msg.content, idx)}
                              className="p-1 hover:text-zinc-100 text-zinc-550 transition-colors rounded"
                              title="Copy Response"
                            >
                              {copiedIndex === idx ? (
                                <Check className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                            <button
                              onClick={() => handleRegenerate(idx)}
                              className="p-1 hover:text-zinc-100 text-zinc-550 transition-colors rounded"
                              title="Regenerate Response"
                            >
                              <RotateCcw className="w-3 h-3" />
                            </button>
                          </div>
                        )}
                      </Card>

                      {isUser && (
                        <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700/40 flex items-center justify-center shrink-0">
                          <User className="w-4 h-4 text-zinc-300" />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>

              {/* Loader */}
              {isGenerating && (
                <div className="flex gap-4 justify-start">
                  <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0 shadow-sm animate-pulse">
                    <Bot className="w-4 h-4 text-violet-400" />
                  </div>
                  <Card className="glass-panel border-zinc-850/40 max-w-[85%] px-5 py-4 rounded-bl-none">
                    <div className="flex items-center gap-3">
                      <div className="dot-flashing" />
                      <span className="text-xs text-zinc-500 select-none">Agent execution path running...</span>
                    </div>
                  </Card>
                </div>
              )}

              {/* Error messages */}
              {error && (
                <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 max-w-3xl mx-auto flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <h5 className="text-sm font-semibold text-rose-450">API Execution Interrupted</h5>
                    <p className="text-xs text-zinc-400 leading-relaxed select-text">{error}</p>
                  </div>
                </div>
              )}
            </div>
          )}
          </div>
        </div>

        {/* Floating Pill Input Bar — macOS Music player bar style */}
        <footer className="px-6 pb-6 pt-2 shrink-0">
          <form
            onSubmit={handleSend}
            className="glass-pill w-full max-w-3xl mx-auto flex items-center gap-2 px-4 py-2"
          >
            {/* Attach / upload icon button */}
            <Link href="/documents" className="shrink-0">
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="w-8 h-8 rounded-full border-transparent bg-transparent hover:bg-white/5 hover:border-white/10 text-zinc-400 hover:text-primary transition-all duration-200 shrink-0"
                title="Upload and Index Documents"
              >
                <Plus className="w-4 h-4" />
              </Button>
            </Link>

            {/* Pill divider */}
            <div className="w-px h-5 bg-white/10 shrink-0" />

            {/* Textarea — transparent, fills the pill */}
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Query documents database or ask follow-up questions..."
              disabled={isGenerating || isStreaming}
              className="flex-1 bg-transparent border-0 outline-none resize-none overflow-hidden max-h-32 text-sm text-zinc-200 placeholder-zinc-550 py-1.5 focus:ring-0"
              style={{ height: "36px" }}
            />

            {/* Send button */}
            <Button
              type="submit"
              variant="primary"
              size="icon"
              disabled={!input.trim() || isGenerating || isStreaming}
              className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center transition-all duration-200"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>
          <div className="text-center text-[10px] text-zinc-650 mt-2 select-none font-medium">
            RAG Orchestrator coordinates Router, Memory and Retrieval sub-agents.
          </div>
        </footer>
      </div>

      {/* 3. Observability Panel (Workflow, Citations, Metrics tabs) */}
      {showObservability && <ObservabilityPanel />}
    </div>
  );
}
