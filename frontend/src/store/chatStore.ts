import { create } from "zustand";
import { api } from "@/services/api";
import { ChatMessage, RoutingDecision, SourceCitation, MemoryRecord, AgentType, ChatSession } from "@/types";

// Module-level guard: tracks any active fake-typing interval so it can be
// cancelled before a new message or session switch begins.
let _typingIntervalId: ReturnType<typeof setInterval> | null = null;

function cancelTypingInterval() {
  if (_typingIntervalId !== null) {
    clearInterval(_typingIntervalId);
    _typingIntervalId = null;
  }
}

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: ChatMessage[];
  isGenerating: boolean;
  isStreaming: boolean;
  error: string | null;

  // Observability metadata for active query response
  currentDecision: RoutingDecision | null;
  currentTrace: string[];
  currentLatency: Record<string, number>;
  currentSources: SourceCitation[];
  currentMemories: MemoryRecord[];
  currentTokens: {
    prompt: number;
    completion: number;
    total: number;
    cost: number;
  } | null;

  // Actions
  fetchSessions: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  createNewSession: () => void;
  sendMessage: (query: string, useWebSearch: boolean, filterDocumentIds?: string[]) => Promise<void>;
  clearMetadata: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isGenerating: false,
  isStreaming: false,
  error: null,

  currentDecision: null,
  currentTrace: [],
  currentLatency: {},
  currentSources: [],
  currentMemories: [],
  currentTokens: null,

  fetchSessions: async () => {
    try {
      const sessions = await api.listSessions();
      set({ sessions });
    } catch (err: unknown) {
      console.error("Failed to load chat sessions:", err instanceof Error ? err.message : String(err));
    }
  },

  selectSession: async (sessionId) => {
    cancelTypingInterval();
    set({ activeSessionId: sessionId, isGenerating: true, error: null });
    get().clearMetadata();
    try {
      const res = await api.exportSession(sessionId, "json");
      const messages = (res.messages || []).map((msg: ChatMessage) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp || new Date().toISOString(),
        agent_type: msg.agent_type,
        metadata: msg.metadata || {},
      }));
      set({ messages, isGenerating: false });
    } catch (err: unknown) {
      set({
        error: err instanceof Error ? err.message : String(err),
        isGenerating: false,
      });
    }
  },

  deleteSession: async (sessionId) => {
    try {
      await api.deleteSession(sessionId);
      const isDeletingActive = get().activeSessionId === sessionId;
      await get().fetchSessions();
      if (isDeletingActive) {
        get().createNewSession();
      }
    } catch (err: unknown) {
      console.error("Failed to delete chat session:", err instanceof Error ? err.message : String(err));
    }
  },

  createNewSession: () => {
    cancelTypingInterval();
    set({
      activeSessionId: null,
      messages: [],
      error: null,
    });
    get().clearMetadata();
  },

  sendMessage: async (query, useWebSearch, filterDocumentIds) => {
    if (!query.trim()) return;
    cancelTypingInterval(); // cancel any stale typing animation before starting

    let sessionId = get().activeSessionId;
    const isNewSession = !sessionId;
    if (isNewSession) {
      sessionId = crypto.randomUUID().replace(/-/g, "");
      set({ activeSessionId: sessionId });
    }

    const userMessage: ChatMessage = {
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isGenerating: true,
      isStreaming: false,
      error: null,
    }));
    get().clearMetadata();

    // Placeholder assistant message shown while retrieval runs
    const placeholderMessage: ChatMessage = {
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    try {
      await new Promise<void>((resolve, reject) => {
        const abortController = api.chatStream(
          {
            query,
            session_id: sessionId!,
            use_web_search: useWebSearch,
            filter_document_ids: filterDocumentIds,
          },
          // onRouting — retrieval done, first token imminent
          (routingEvent) => {
            set((state) => ({
              messages: [...state.messages, { ...placeholderMessage }],
              isGenerating: false,
              isStreaming: true,
              currentDecision: routingEvent.routing_decision || null,
              currentTrace: routingEvent.trace || [],
            }));
          },
          // onToken — append each token to the last message
          (token) => {
            set((state) => {
              const msgs = [...state.messages];
              if (msgs.length > 0) {
                msgs[msgs.length - 1] = {
                  ...msgs[msgs.length - 1],
                  content: msgs[msgs.length - 1].content + token,
                };
              }
              return { messages: msgs };
            });
          },
          // onDone — apply full metadata, mark stream finished
          (meta) => {
            set((state) => {
              const msgs = [...state.messages];
              if (msgs.length > 0) {
                msgs[msgs.length - 1] = {
                  ...msgs[msgs.length - 1],
                  agent_type: (meta as any).agent_used,
                  isStreaming: false,
                };
              }
              return {
                messages: msgs,
                isStreaming: false,
                currentDecision: (meta as any).routing_decision || null,
                currentTrace: (meta as any).routing_trace || [],
                currentLatency: (meta as any).latency_ms || {},
                currentSources: (meta as any).sources || [],
                currentMemories: (meta as any).retrieved_memories || [],
                currentTokens: {
                  prompt: (meta as any).prompt_tokens ?? 0,
                  completion: (meta as any).completion_tokens ?? 0,
                  total: (meta as any).total_tokens ?? 0,
                  cost: (meta as any).cost_usd ?? 0,
                },
              };
            });
            get().fetchSessions();
            resolve();
          },
          // onError
          (errMsg) => {
            set({ error: errMsg, isGenerating: false, isStreaming: false });
            reject(new Error(errMsg));
          },
        );

        // Attach abort controller for cleanup (e.g., on session change)
        (get() as any)._streamAbort = abortController;
      });
    } catch (err: unknown) {
      if ((err as { name?: string })?.name !== "AbortError") {
        set({
          error: err instanceof Error ? err.message : String(err),
          isGenerating: false,
          isStreaming: false,
        });
      }
    }
  },

  clearMetadata: () => {
    set({
      currentDecision: null,
      currentTrace: [],
      currentLatency: {},
      currentSources: [],
      currentMemories: [],
      currentTokens: null,
    });
  },
}));
