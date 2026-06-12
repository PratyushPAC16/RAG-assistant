import { create } from "zustand";
import { api } from "@/services/api";
import { HealthResponse } from "@/types";

interface SettingsState {
  // Provider Configs
  activeProvider: string;
  geminiModel: string;
  groqModel: string;
  ollamaModel: string;
  googleApiKey: string;
  groqApiKey: string;
  ollamaBaseUrl: string;
  useWebSearch: boolean;
  
  // Connection state
  health: HealthResponse | null;
  connectionStatus: "idle" | "testing" | "success" | "failed";
  error: string | null;
  isLoading: boolean;

  // Actions
  setProvider: (provider: string) => void;
  setUseWebSearch: (val: boolean) => void;
  updateKeys: (updates: Partial<Pick<SettingsState, "googleApiKey" | "groqApiKey" | "ollamaBaseUrl" | "geminiModel" | "groqModel" | "ollamaModel">>) => void;
  fetchHealth: () => Promise<void>;
  testConnection: () => Promise<boolean>;
  reloadBackend: () => Promise<boolean>;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  activeProvider: "ollama",
  geminiModel: "gemini-2.0-flash",
  groqModel: "llama-3.1-8b-instant",
  ollamaModel: "llama3.2",
  googleApiKey: "",
  groqApiKey: "",
  ollamaBaseUrl: "http://localhost:11434",
  useWebSearch: true,
  
  health: null,
  connectionStatus: "idle",
  error: null,
  isLoading: false,

  setProvider: (provider) => set({ activeProvider: provider }),
  setUseWebSearch: (val) => set({ useWebSearch: val }),
  updateKeys: (updates) => set(updates),

  fetchHealth: async () => {
    set({ isLoading: true, error: null });
    try {
      const health = await api.getHealth();
      set({ 
        health, 
        activeProvider: health.llm_provider.toLowerCase(),
        isLoading: false 
      });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  testConnection: async () => {
    set({ connectionStatus: "testing", error: null });
    try {
      const health = await api.getHealth();
      set({ health, connectionStatus: "success" });
      return true;
    } catch (err: any) {
      set({ connectionStatus: "failed", error: err.message });
      return false;
    }
  },

  reloadBackend: async () => {
    set({ isLoading: true });
    try {
      await api.reloadConfig();
      const health = await api.getHealth();
      set({ health, isLoading: false, connectionStatus: "success" });
      return true;
    } catch (err: any) {
      set({ error: err.message, isLoading: false, connectionStatus: "failed" });
      return false;
    }
  }
}));
