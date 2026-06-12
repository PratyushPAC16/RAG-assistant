"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Files,
  Upload,
  Search,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileText,
  FileCode,
  HardDrive,
} from "lucide-react";
import { cn, formatBytes, formatDateTime } from "@/lib/utils";

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Fetch Documents list
  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(),
    refetchInterval: 10000, // Eager reload every 10s to capture background processing
  });

  // Reindex Mutation
  const reindexMutation = useMutation({
    mutationFn: (id: string) => api.reindexDocument(id),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setSuccessMsg(`Reindexed document "${res.filename}"!`);
      setTimeout(() => setSuccessMsg(null), 4000);
    },
    onError: (err: any) => {
      setErrorMsg(`Reindexing failed: ${err.message}`);
      setTimeout(() => setErrorMsg(null), 5000);
    },
  });

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["health"] });
      setSuccessMsg("Document deleted successfully!");
      setTimeout(() => setSuccessMsg(null), 4000);
    },
    onError: (err: any) => {
      setErrorMsg(`Deletion failed: ${err.message}`);
      setTimeout(() => setErrorMsg(null), 5000);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setIsUploading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.uploadDocument(uploadFile);
      setSuccessMsg(`Successfully uploaded and indexed "${uploadFile.name}"!`);
      setUploadFile(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["health"] });
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to upload document.");
    } finally {
      setIsUploading(false);
    }
  };

  const documents = data?.documents || [];
  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8">
      {/* Title Header */}
      <div className="border-b border-zinc-800/40 pb-5">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <Files className="w-8 h-8 text-primary" />
          Document Registry
        </h1>
        <p className="text-zinc-400 text-sm mt-1">
          Upload and manage files. Uploaded documents are automatically parsed, vectorized, and stored.
        </p>
      </div>

      {/* Upload Zone & Messages */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <Card className="glass-panel border-zinc-800/40 sticky top-8">
            <CardHeader>
              <CardTitle className="text-md font-semibold text-zinc-100">Upload New File</CardTitle>
              <CardDescription className="text-zinc-500 text-xs">
                Supports PDF, DOCX, and TXT files up to 25MB.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleUpload} className="space-y-4">
                <div className="border-2 border-dashed border-zinc-800 hover:border-primary/40 rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-zinc-950/20 relative group">
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Upload className="w-8 h-8 text-zinc-500 group-hover:text-primary transition-colors mb-3" />
                  
                  {uploadFile ? (
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-zinc-200 truncate max-w-[180px]">
                        {uploadFile.name}
                      </p>
                      <p className="text-[10px] text-zinc-500">{formatBytes(uploadFile.size)}</p>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <p className="text-xs text-zinc-300 font-medium">Click or drag file to upload</p>
                      <p className="text-[10px] text-zinc-500">PDF, DOCX, or TXT formats</p>
                    </div>
                  )}
                </div>

                {errorMsg && (
                  <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-400 flex items-start gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                {successMsg && (
                  <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-400 flex items-start gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>{successMsg}</span>
                  </div>
                )}

                <Button
                  type="submit"
                  variant="primary"
                  className="w-full font-medium"
                  disabled={!uploadFile || isUploading}
                  loading={isUploading}
                >
                  Index Document
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Documents Table List - 2 columns wide */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-2.5" />
              <Input
                type="text"
                placeholder="Search documents by name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-zinc-950/40 border-zinc-800/60 focus:border-primary/60 text-xs h-9 text-zinc-200"
              />
            </div>
            
            <div className="flex items-center gap-1.5 bg-zinc-900/40 border border-zinc-800/30 px-3 py-1.5 rounded-lg text-[10px] text-zinc-400 font-medium font-mono shrink-0">
              <HardDrive className="w-3.5 h-3.5" />
              Total: {documents.length} docs
            </div>
          </div>

          <Card className="glass-panel border-zinc-800/40 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs select-none">
                <thead>
                  <tr className="border-b border-zinc-800/50 bg-zinc-950/20 text-zinc-400 font-medium">
                    <th className="p-4">Filename</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Chunks</th>
                    <th className="p-4">Size</th>
                    <th className="p-4">Indexed At</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/30">
                  {isLoading ? (
                    [1, 2, 3].map((n) => (
                      <tr key={n}>
                        <td colSpan={6} className="p-6 text-center">
                          <div className="h-4 bg-zinc-900/60 animate-pulse rounded w-3/4 mx-auto" />
                        </td>
                      </tr>
                    ))
                  ) : filteredDocs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-zinc-500 font-medium">
                        No documents indexed. Upload files on the left to start.
                      </td>
                    </tr>
                  ) : (
                    filteredDocs.map((doc) => {
                      let fileColor = "text-zinc-400";
                      if (doc.file_type === "pdf") fileColor = "text-rose-400";
                      if (doc.file_type === "docx") fileColor = "text-blue-400";
                      
                      const isProcessing = doc.status === "processing";
                      const isFailed = doc.status === "failed";
                      const isIndexed = doc.status === "indexed";

                      return (
                        <tr key={doc.document_id} className="hover:bg-zinc-800/10 transition-colors">
                          <td className="p-4 font-medium text-zinc-200">
                            <div className="flex items-center gap-2 max-w-[200px] md:max-w-xs">
                              {doc.file_type === "txt" ? (
                                <FileCode className={`w-4 h-4 shrink-0 ${fileColor}`} />
                              ) : (
                                <FileText className={`w-4 h-4 shrink-0 ${fileColor}`} />
                              )}
                              <span className="truncate" title={doc.filename}>{doc.filename}</span>
                            </div>
                          </td>
                          <td className="p-4">
                            {isIndexed ? (
                              <span className="inline-flex items-center gap-1 text-[9px] font-semibold px-2 py-0.5 rounded-full border bg-emerald-500/10 border-emerald-500/20 text-emerald-400 uppercase tracking-wider">
                                Indexed
                              </span>
                            ) : isProcessing ? (
                              <span className="inline-flex items-center gap-1 text-[9px] font-semibold px-2 py-0.5 rounded-full border bg-amber-500/10 border-amber-500/20 text-amber-400 uppercase tracking-wider animate-pulse">
                                Processing
                              </span>
                            ) : isFailed ? (
                              <span
                                className="inline-flex items-center gap-1 text-[9px] font-semibold px-2 py-0.5 rounded-full border bg-rose-500/10 border-rose-500/20 text-rose-400 uppercase tracking-wider"
                                title={doc.error_message}
                              >
                                Failed
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[9px] font-semibold px-2 py-0.5 rounded-full border bg-zinc-900 border-zinc-800 text-zinc-500 uppercase tracking-wider">
                                {doc.status}
                              </span>
                            )}
                          </td>
                          <td className="p-4 text-zinc-300 font-mono">{doc.num_chunks}</td>
                          <td className="p-4 text-zinc-400 font-mono">{formatBytes(doc.file_size_bytes)}</td>
                          <td className="p-4 text-zinc-500">
                            {doc.indexed_at ? formatDateTime(doc.indexed_at) : formatDateTime(doc.created_at)}
                          </td>
                          <td className="p-4 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => reindexMutation.mutate(doc.document_id)}
                                disabled={reindexMutation.isPending || deleteMutation.isPending || isProcessing}
                                className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-zinc-200 transition-colors disabled:opacity-30"
                                title="Reindex File"
                              >
                                <RefreshCw className={cn("w-3.5 h-3.5", reindexMutation.isPending && "animate-spin")} />
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm(`Are you sure you want to delete and wipe "${doc.filename}"?`)) {
                                    deleteMutation.mutate(doc.document_id);
                                  }
                                }}
                                disabled={reindexMutation.isPending || deleteMutation.isPending || isProcessing}
                                className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-rose-400 transition-colors disabled:opacity-30"
                                title="Delete File"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
