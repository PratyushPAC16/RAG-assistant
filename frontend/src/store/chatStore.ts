import { create } from "zustand";
import { api } from "@/services/api";
import { ChatMessage, RoutingDecision, SourceCitation, MemoryRecord, AgentType } from "@/types";

interface ChatSession {
  session_id: string;
  title?: string;
  message_count?: number;
  last_updated?: string;
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
    } catch (err: any) {
      console.error("Failed to load chat sessions:", err);
    }
  },

  selectSession: async (sessionId) => {
    set({ activeSessionId: sessionId, isGenerating: true, error: null });
    get().clearMetadata();
    try {
      const res = await api.exportSession(sessionId, "json");
      const messages = (res.messages || []).map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp || new Date().toISOString(),
        agent_type: msg.agent_type,
        metadata: msg.metadata || {},
      }));
      set({ messages, isGenerating: false });
    } catch (err: any) {
      set({ error: err.message, isGenerating: false });
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
    } catch (err: any) {
      console.error("Failed to delete chat session:", err);
    }
  },

  createNewSession: () => {
    set({
      activeSessionId: null,
      messages: [],
      error: null,
    });
    get().clearMetadata();
  },

  sendMessage: async (query, useWebSearch, filterDocumentIds) => {
    if (!query.trim()) return;

    let sessionId = get().activeSessionId;
    // Generate a temp session ID if none active
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
      error: null,
    }));
    get().clearMetadata();

    try {
      const res = await api.chat({
        query,
        session_id: sessionId!,
        use_web_search: useWebSearch,
        filter_document_ids: filterDocumentIds,
      });

      // Save metadata
      set({
        currentDecision: res.routing_decision || null,
        currentTrace: res.routing_trace || [],
        currentLatency: res.latency_ms || {},
        currentSources: res.sources || [],
        currentMemories: res.retrieved_memories || [],
        currentTokens: {
          prompt: res.prompt_tokens,
          completion: res.completion_tokens,
          total: res.total_tokens,
          cost: res.cost_usd,
        },
      });

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        agent_type: res.agent_used,
        isStreaming: true,
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isGenerating: false,
        isStreaming: true,
      }));

      // Emulate typing animation for a premium SaaS experience
      const fullContent = res.answer;
      const words = fullContent.split(/(\s+)/);
      let index = 0;
      let displayedText = "";

      const interval = setInterval(() => {
        if (index < words.length) {
          displayedText += words[index];
          index++;
          set((state) => {
            const updatedMessages = [...state.messages];
            if (updatedMessages.length > 0) {
              updatedMessages[updatedMessages.length - 1] = {
                ...updatedMessages[updatedMessages.length - 1],
                content: displayedText,
              };
            }
            return { messages: updatedMessages };
          });
        } else {
          clearInterval(interval);
          set((state) => {
            const updatedMessages = [...state.messages];
            if (updatedMessages.length > 0) {
              updatedMessages[updatedMessages.length - 1] = {
                ...updatedMessages[updatedMessages.length - 1],
                isStreaming: false,
              };
            }
            return { isStreaming: false };
          });
          get().fetchSessions();
        }
      }, 15); // Adjust typing speed here
    } catch (err: any) {
      set({ error: err.message, isGenerating: false });
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
