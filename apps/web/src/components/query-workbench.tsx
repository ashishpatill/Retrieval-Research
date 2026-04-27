"use client";

import { useState } from "react";
import { apiBaseUrl } from "@/lib/api";

type ResultPayload = {
  run_id: string;
  result: {
    answer: string;
    knowledge_card?: { confidence?: number; answerable?: boolean; answerability_reason?: string } & Record<string, unknown>;
    evidence?: unknown[];
  };
  trace: unknown;
};

export function QueryWorkbench() {
  const [question, setQuestion] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [mode, setMode] = useState("planner");
  const [topK, setTopK] = useState(5);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState<ResultPayload | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");
    setPayload(null);
    try {
      const response = await fetch(`${apiBaseUrl()}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          document_id: documentId || null,
          mode,
          top_k: topK,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data?.detail || "Query failed.");
      } else {
        setPayload(data as ResultPayload);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-semibold text-zinc-100">Query workbench</h2>
        <textarea
          className="h-24 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3 text-sm text-zinc-100"
          placeholder="Ask a question..."
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          required
        />
        <div className="grid grid-cols-3 gap-2">
          <input
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
            placeholder="Document ID (optional)"
            value={documentId}
            onChange={(event) => setDocumentId(event.target.value)}
          />
          <select
            value={mode}
            onChange={(event) => setMode(event.target.value)}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          >
            <option value="planner">planner</option>
            <option value="hybrid">hybrid</option>
            <option value="bm25">bm25</option>
            <option value="dense">dense</option>
            <option value="visual">visual</option>
          </select>
          <input
            type="number"
            value={topK}
            min={1}
            max={20}
            onChange={(event) => setTopK(Number(event.target.value))}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          />
        </div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {isSubmitting ? "Running..." : "Run query"}
        </button>
      </form>

      {error ? <p className="rounded-md border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-200">{error}</p> : null}

      {payload ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <h3 className="text-sm font-semibold text-zinc-100">Answer</h3>
            <pre className="whitespace-pre-wrap text-xs text-zinc-200">{payload.result.answer}</pre>
            <p className="text-xs text-zinc-400">Run ID: {payload.run_id}</p>
          </section>
          <section className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <h3 className="text-sm font-semibold text-zinc-100">Knowledge card</h3>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2 text-xs text-zinc-300">
              <p>Answerable: {String(payload.result.knowledge_card?.answerable ?? false)}</p>
              <p>Confidence: {(payload.result.knowledge_card?.confidence ?? 0).toFixed(3)}</p>
              <p>{payload.result.knowledge_card?.answerability_reason ?? "No reason available."}</p>
            </div>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-zinc-200">
              {JSON.stringify(payload.result.knowledge_card ?? {}, null, 2)}
            </pre>
          </section>
          <section className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-900 p-4 lg:col-span-2">
            <h3 className="text-sm font-semibold text-zinc-100">Retrieval trace</h3>
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs text-zinc-200">
              {JSON.stringify(payload.trace, null, 2)}
            </pre>
          </section>
        </div>
      ) : null}
    </div>
  );
}
