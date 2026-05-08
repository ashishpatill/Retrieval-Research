"use client";

import { useState } from "react";
import { Puzzle, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
      const endpoint = action === "chunk"
        ? `/api/documents/${documentId}/chunk`
        : `/api/documents/${documentId}/index`;
      const body = action === "chunk"
        ? { max_words: 220, overlap_words: 40 }
        : { mode: "all", visual_backend: "baseline" };
      const response = await fetch(`${apiBaseUrl()}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) {
        setStatus(payload?.detail || `${action} failed`);
      } else {
        setStatus(
          action === "chunk"
            ? `Created ${payload.chunk_count} chunks.`
            : `Saved ${payload.saved_paths.length} indexes.`,
        );
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : `${action} failed`);
    } finally {
      setBusyAction("");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Puzzle className="h-4 w-4" />
          Process document
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => runAction("chunk")}
            disabled={!!busyAction}
          >
            {busyAction === "chunk" ? "Chunking..." : "Build chunks"}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => runAction("index")}
            disabled={!!busyAction}
          >
            {busyAction === "index" ? "Indexing..." : "Build indexes"}
          </Button>
        </div>
        {status && <p className="text-xs text-muted-foreground">{status}</p>}
      </CardContent>
    </Card>
  );
}
