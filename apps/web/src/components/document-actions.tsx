"use client";

import { useState } from "react";
import { apiBaseUrl } from "@/lib/api";

type Props = {
  documentId: string;
};

export function DocumentActions({ documentId }: Props) {
  const [status, setStatus] = useState<string>("");
  const [busyAction, setBusyAction] = useState<string>("");

  async function runAction(action: "chunk" | "index") {
    setStatus("");
    setBusyAction(action);
    try {
      const endpoint = action === "chunk" ? `/api/documents/${documentId}/chunk` : `/api/documents/${documentId}/index`;
      const body = action === "chunk" ? { max_words: 220, overlap_words: 40 } : { mode: "all", visual_backend: "baseline" };
      const response = await fetch(`${apiBaseUrl()}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) {
        setStatus(payload?.detail || `${action} failed`);
      } else {
        setStatus(action === "chunk" ? `Created ${payload.chunk_count} chunks.` : `Saved ${payload.saved_paths.length} indexes.`);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : `${action} failed`);
    } finally {
      setBusyAction("");
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h3 className="text-sm font-semibold text-zinc-100">Process document</h3>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => runAction("chunk")}
          disabled={!!busyAction}
          className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {busyAction === "chunk" ? "Chunking..." : "Build chunks"}
        </button>
        <button
          type="button"
          onClick={() => runAction("index")}
          disabled={!!busyAction}
          className="rounded-md bg-violet-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {busyAction === "index" ? "Indexing..." : "Build indexes"}
        </button>
      </div>
      {status ? <p className="text-xs text-zinc-300">{status}</p> : null}
    </div>
  );
}
