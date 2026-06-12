import {
  HealthResponse,
  ChatRequest,
  ChatResponse,
  DocumentListResponse,
  UploadResponse,
  DeleteDocumentResponse,
  MemoryRecord,
  RetrievalMetric,
  BenchmarkRun,
  WorkflowDefinition,
  WorkflowExecutionResult,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorMessage;
      } catch {
        if (errorText) errorMessage = errorText;
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<T>;
  }

  // ── System / Health ──────────────────────────────────────────────────────────
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async getGraph(): Promise<{ mermaid: string }> {
    return this.request<{ mermaid: string }>("/graph");
  }

  async reloadConfig(): Promise<{ status: string; gemini_model: string; embedding_model: string }> {
    return this.request<{ status: string; gemini_model: string; embedding_model: string }>("/reload", {
      method: "POST",
    });
  }

  // ── Chat ─────────────────────────────────────────────────────────────────────
  async chat(req: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }

  async listSessions(): Promise<any[]> {
    return this.request<any[]>("/chat/sessions");
  }

  async deleteSession(sessionId: string): Promise<{ session_id: string; message: string }> {
    return this.request<{ session_id: string; message: string }>(`/chat/session/${sessionId}`, {
      method: "DELETE",
    });
  }

  async exportSession(sessionId: string, format = "json"): Promise<{ session_id: string; format: string; content?: string; messages?: any[] }> {
    return this.request<{ session_id: string; format: string; content?: string; messages?: any[] }>(
      `/chat/session/${sessionId}/export?format=${format}`
    );
  }

  // ── Documents ────────────────────────────────────────────────────────────────
  async listDocuments(): Promise<DocumentListResponse> {
    return this.request<DocumentListResponse>("/documents");
  }

  async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${API_BASE_URL}/upload`;
    const response = await fetch(url, {
      method: "POST",
      body: formData,
      // Note: We do NOT set Content-Type header here, so browser automatically sets multipart/form-data boundary
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorMessage;
      } catch {
        if (errorText) errorMessage = errorText;
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<UploadResponse>;
  }

  async deleteDocument(documentId: string): Promise<DeleteDocumentResponse> {
    return this.request<DeleteDocumentResponse>(`/documents/${documentId}`, {
      method: "DELETE",
    });
  }

  async reindexDocument(documentId: string): Promise<UploadResponse> {
    return this.request<UploadResponse>(`/documents/${documentId}/reindex`, {
      method: "POST",
    });
  }

  // ── Long-Term Memory ──────────────────────────────────────────────────────────
  async listMemories(): Promise<MemoryRecord[]> {
    return this.request<MemoryRecord[]>("/memories");
  }

  async searchMemories(query: string, topK = 5): Promise<MemoryRecord[]> {
    return this.request<MemoryRecord[]>(`/memories/search?query=${encodeURIComponent(query)}&top_k=${topK}`);
  }

  async deleteMemory(memoryId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/memories/${memoryId}`, {
      method: "DELETE",
    });
  }

  async clearMemories(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>("/memories", {
      method: "DELETE",
    });
  }

  // ── Resume Analyzer ──────────────────────────────────────────────────────────
  async analyzeResume(resume: File, jd: File): Promise<Record<string, any>> {
    const formData = new FormData();
    formData.append("resume", resume);
    formData.append("jd", jd);

    const url = `${API_BASE_URL}/analyze-resume`;
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorMessage;
      } catch {
        if (errorText) errorMessage = errorText;
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<Record<string, any>>;
  }

  // ── Analytics ────────────────────────────────────────────────────────────────
  async getAnalytics(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>("/analytics");
  }

  async getExtendedAnalytics(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>("/analytics/extended");
  }

  async getRetrievalMetrics(limit = 50): Promise<{ total_logged: number; returned: number; metrics: RetrievalMetric[] }> {
    return this.request<{ total_logged: number; returned: number; metrics: RetrievalMetric[] }>(
      `/retrieval-metrics?limit=${limit}`
    );
  }

  // ── Benchmarks ───────────────────────────────────────────────────────────────
  async runBenchmark(query: string, useRag = false, temperature = 0.1): Promise<BenchmarkRun> {
    return this.request<BenchmarkRun>(
      `/benchmark?query=${encodeURIComponent(query)}&use_rag=${useRag}&temperature=${temperature}`,
      {
        method: "POST",
      }
    );
  }

  async getBenchmarkHistory(limit = 50): Promise<{ total: number; runs: BenchmarkRun[] }> {
    return this.request<{ total: number; runs: BenchmarkRun[] }>(`/benchmark/history?limit=${limit}`);
  }

  async clearBenchmarkHistory(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>("/benchmark/history", {
      method: "DELETE",
    });
  }

  // ── Visual Workflow Builder ───────────────────────────────────────────────────
  async listWorkflows(): Promise<WorkflowDefinition[]> {
    return this.request<WorkflowDefinition[]>("/workflows");
  }

  async saveWorkflow(workflow: WorkflowDefinition): Promise<{ status: string; workflow_id: string }> {
    return this.request<{ status: string; workflow_id: string }>("/workflows", {
      method: "POST",
      body: JSON.stringify(workflow),
    });
  }

  async getWorkflow(workflowId: string): Promise<WorkflowDefinition> {
    return this.request<WorkflowDefinition>(`/workflows/${workflowId}`);
  }

  async deleteWorkflow(workflowId: string): Promise<{ status: string; workflow_id: string }> {
    return this.request<{ status: string; workflow_id: string }>(`/workflows/${workflowId}`, {
      method: "DELETE",
    });
  }

  async executeWorkflow(workflowId: string, query: string): Promise<WorkflowExecutionResult> {
    return this.request<WorkflowExecutionResult>(
      `/workflows/${workflowId}/execute?query=${encodeURIComponent(query)}`,
      {
        method: "POST",
      }
    );
  }

  async getWorkflowExecutions(workflowId: string, limit = 50): Promise<{ workflow_id: string; total: number; executions: WorkflowExecutionResult[] }> {
    return this.request<{ workflow_id: string; total: number; executions: WorkflowExecutionResult[] }>(
      `/workflows/${workflowId}/executions?limit=${limit}`
    );
  }
}

export const api = new ApiService();
