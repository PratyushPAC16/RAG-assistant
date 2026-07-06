// ── Enumerations ──────────────────────────────────────────────────────────────

export type AgentType = "rag" | "web" | "memory" | "hybrid";

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed";

export type FileType = "pdf" | "docx" | "txt";

// ── Document Metadata ─────────────────────────────────────────────────────────

export interface ChunkMetadata {
  source: string;
  document_name: string;
  page?: number;
  file_type: string;
  chunk_id: string;
  document_id: string;
  char_start?: number;
  char_end?: number;
  total_chunks?: number;
}

export interface DocumentRecord {
  document_id: string;
  filename: string;
  file_type: FileType;
  status: DocumentStatus;
  num_chunks: number;
  num_pages?: number;
  file_size_bytes: number;
  created_at: string;
  indexed_at?: string;
  error_message?: string;
}

// ── Retrieval & Reranking ─────────────────────────────────────────────────────

export interface RetrievedChunk {
  chunk_id: string;
  content: string;
  metadata: ChunkMetadata;
  semantic_score?: number;
  bm25_score?: number;
  rerank_score?: number;
  final_rank?: number;
}

export interface SourceCitation {
  document?: string;   // optional — backend may omit for preview sources
  page?: number;
  chunk_id?: string;
  relevance_score?: number;
  text?: string;
  // aliases used by some endpoints
  name?: string;
  score?: number;
  confidence?: number;
}

// ── Chat & Memory ─────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  role: MessageRole;
  content: string;
  timestamp: string;
  agent_type?: AgentType;
  metadata?: Record<string, any>;
  // UI-only states
  isStreaming?: boolean;
}

export interface ConversationMemory {
  session_id: string;
  messages: ChatMessage[];
  max_turns: number;
}

// ── Long-Term Memory ──────────────────────────────────────────────────────────

export interface MemoryRecord {
  memory_id: string;
  content: string;
  memory_type: string; // "fact" | "preference" | "summary"
  session_id: string;
  score?: number;
  timestamp: string;
}

// ── Routing Decision ─────────────────────────────────────────────────────────

export interface RoutingDecision {
  agent: AgentType;
  reasoning: string;
  confidence: number;
  fallback_used: boolean;
  num_docs_available: number;
  timestamp: string;
}

// ── Agent State (LangGraph) ───────────────────────────────────────────────────

export interface AgentState {
  query: string;
  session_id: string;
  agent_type?: AgentType;
  retrieved_chunks: RetrievedChunk[];
  reranked_chunks: RetrievedChunk[];
  web_results: Record<string, any>[];
  context: string;
  answer: string;
  sources: SourceCitation[];
  conversation_history: ChatMessage[];
  error?: string;
  latency_ms: Record<string, number>;
  routing_decision?: RoutingDecision;
  routing_trace: string[];
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  filter_document_ids?: string[];
  retrieved_memories: MemoryRecord[];
}

// ── API Request / Response Shapes ────────────────────────────────────────────

export interface UploadResponse {
  document_id: string;
  filename: string;
  num_chunks: number;
  num_pages?: number;
  status: DocumentStatus;
  message: string;
}

export interface ChatRequest {
  query: string;
  session_id?: string;
  use_web_search: boolean;
  filter_document_ids?: string[];
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  agent_used: AgentType;
  session_id: string;
  latency_ms: Record<string, number>;
  routing_decision?: RoutingDecision;
  routing_trace: string[];
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  retrieved_memories: MemoryRecord[];
}

export interface DocumentListResponse {
  documents: DocumentRecord[];
  total: number;
}

export interface DeleteDocumentResponse {
  document_id: string;
  message: string;
  chunks_deleted: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  vector_store: string;
  embedding_model: string;
  llm_model: string;
  llm_provider: string;
  documents_indexed: number;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface ScoreDistribution {
  min_score?: number;
  max_score?: number;
  mean_score?: number;
  p50_score?: number;
  p90_score?: number;
}

export interface RetrievalMetric {
  query: string;
  query_length: number;
  agent_type: AgentType;
  session_id?: string;
  timestamp: string;
  num_vector_results: number;
  num_bm25_results: number;
  num_retrieved: number;
  num_reranked: number;
  vector_search_latency_ms: number;
  bm25_search_latency_ms: number;
  rrf_fusion_latency_ms: number;
  retrieval_latency_ms: number;
  reranking_latency_ms?: number;
  llm_latency_ms?: number;
  total_latency_ms: number;
  vector_score_distribution: ScoreDistribution;
  bm25_score_distribution: ScoreDistribution;
  rerank_score_distribution: ScoreDistribution;
  rrf_score_distribution: ScoreDistribution;
  sources_used: string[];
  top_reranked_sources: string[];
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

// ── LLM Benchmark ─────────────────────────────────────────────────────────────

export interface BenchmarkProviderResult {
  provider: string;
  model: string;
  response: string;
  latency_s: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  response_length_chars: number;
  response_length_words: number;
  retrieval_accuracy: number;
  evaluation_reasoning: string;
  citations: string[];
  error?: string;
  composite_score: number;
}

export interface BenchmarkRun {
  run_id: string;
  timestamp: string;
  query: string;
  context_retrieved: string;
  use_rag: boolean;
  results: Record<string, BenchmarkProviderResult>;
}

// ── Visual Workflow Builder Schemas ───────────────────────────────────────────

export type WorkflowNodeType = "router" | "rag" | "memory" | "web_search" | "llm" | "evaluator";

export interface WorkflowNodeDef {
  id: string;
  type: WorkflowNodeType;
  label: string;
  position: { x: number; y: number };
  config: Record<string, any>;
}

export interface WorkflowEdgeDef {
  id: string;
  source: string;
  source_handle?: string;
  target: string;
  target_handle?: string;
  animated: boolean;
}

export interface WorkflowDefinition {
  workflow_id: string;
  name: string;
  description: string;
  nodes: WorkflowNodeDef[];
  edges: WorkflowEdgeDef[];
  created_at: string;
  updated_at: string;
  tags: string[];
}

export interface WorkflowExecutionStep {
  node_id: string;
  node_type: string;
  node_label: string;
  status: "idle" | "running" | "done" | "error";
  output: Record<string, any>;
  error?: string;
  duration_ms: number;
  started_at: string;
}

export interface WorkflowExecutionResult {
  execution_id: string;
  workflow_id: string;
  workflow_name: string;
  query: string;
  status: "pending" | "running" | "done" | "error";
  steps: WorkflowExecutionStep[];
  final_output: Record<string, any>;
  total_duration_ms: number;
  started_at: string;
  completed_at?: string;
}
// ── Chat Session ─────────────────────────────────────────────────────────────

export interface ChatSession {
  session_id: string;
  title?: string;
  message_count?: number;
  last_updated?: string;
}

// ── Analytics Response Shapes ─────────────────────────────────────────────────

/** Shape returned by GET /analytics */
export interface AnalyticsResponse {
  total_queries: number;
  queries_today: number;
  avg_total_latency_ms: number;
  avg_retrieval_latency_ms: number;
  avg_vector_search_ms: number;
  avg_bm25_search_ms: number;
  avg_rrf_fusion_ms: number;
  avg_reranking_ms: number;
  avg_llm_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_prompt_tokens: number;
  avg_completion_tokens: number;
  avg_total_tokens: number;
  avg_cost_usd: number;
  avg_vector_hits: number;
  avg_bm25_hits: number;
  avg_retrieved: number;
  avg_reranked: number;
  agent_distribution: Record<string, number>;
  top_sources: [string, number][];
  document_chunk_distribution: Record<string, number>;
  recent_metrics: RetrievalMetric[];
  daily_trend: { date: string; queries: number; cost: number }[];
  // optional provider field
  llm_provider?: string;
}

/** Shape returned by GET /analytics/extended */
export interface ExtendedAnalyticsResponse extends AnalyticsResponse {
  provider_usage: Record<string, number>;
  most_used_agent: string;
  avg_retrieval_ms: number;
  p95_total_latency_ms: number;
  retrieval_success_rate: number;
  avg_chunks_retrieved: number;
  avg_chunks_reranked: number;
  avg_query_length: number;
  max_query_length: number;
  min_query_length: number;
  query_length_distribution: Record<string, number>;
  hourly_query_counts: { hour: number; count: number }[];
  memory_metrics?: Record<string, unknown>;
  document_metrics?: {
    total_documents: number;
    total_chunks_indexed: number;
    file_type_distribution: Record<string, number>;
  };
}

/** Shape returned by POST /analyze-resume */
export interface ResumeAnalysisResponse {
  overall_match_score: number;
  ats_score: number;
  skills_match: { matched: string[]; missing: string[]; score: number };
  experience_match: { score: number; summary: string };
  education_match: { score: number; summary: string };
  projects_match: { score: number; summary: string };
  interview_readiness: number;
  strengths: string[];
  improvement_areas: string[];
  roadmap: string[];
  keyword_density: Record<string, number>;
  [key: string]: unknown;  // backend may add extra fields
}
