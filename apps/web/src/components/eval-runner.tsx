"use client";

import { useState } from "react";
import { apiBaseUrl } from "@/lib/api";

type EvalResponse = {
  run_id: string;
  report: {
    metrics?: {
      graph_diagnostics?: {
        available?: boolean;
        step_count?: number;
        avg_seed_count?: number;
        avg_expanded_count?: number;
        max_document_count?: number;
        relation_counts?: Record<string, number>;
      };
    };
    results?: Array<{
      query?: string;
      mode?: string;
      steps?: Array<{
        path?: string;
        diagnostics?: {
          seed_count?: number;
          expanded_count?: number;
          expanded_relation_counts?: Record<string, number>;
        };
      }>;
    }>;
  } & Record<string, unknown>;
};

const DEFAULT_MANIFEST = {
  queries: [{ query: "keyword retrieval", expected_terms: ["keyword"], expected_pages: [1] }],
};

export function EvalRunner() {
  const [manifestText, setManifestText] = useState(JSON.stringify(DEFAULT_MANIFEST, null, 2));
  const [topK, setTopK] = useState(5);
  const [modesText, setModesText] = useState("bm25,dense,hybrid,planner");
  const [result, setResult] = useState<EvalResponse | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    setIsSubmitting(true);
    try {
      const manifest = JSON.parse(manifestText);
      const modes = modesText
        .split(",")
        .map((mode) => mode.trim())
        .filter(Boolean);

      const response = await fetch(`${apiBaseUrl()}/api/eval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manifest, top_k: topK, modes }),
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(payload?.detail || "Eval failed.");
      } else {
        setResult(payload as EvalResponse);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const graphRows =
    result?.report.results
      ?.flatMap((row) =>
        (row.steps ?? [])
          .filter((step) => step.path === "graph" && step.diagnostics)
          .map((step) => ({ query: row.query, mode: row.mode, diagnostics: step.diagnostics })),
      )
      .slice(0, 8) ?? [];
  const graphSummary = result?.report.metrics?.graph_diagnostics;

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-semibold text-zinc-100">Run eval</h2>
        <textarea
          className="h-48 w-full rounded-md border border-zinc-700 bg-zinc-950 p-3 font-mono text-xs text-zinc-100"
          value={manifestText}
          onChange={(event) => setManifestText(event.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            value={topK}
            min={1}
            max={20}
            onChange={(event) => setTopK(Number(event.target.value))}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          />
          <input
            value={modesText}
            onChange={(event) => setModesText(event.target.value)}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
            placeholder="bm25,dense,hybrid,planner"
          />
        </div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {isSubmitting ? "Running..." : "Run eval"}
        </button>
      </form>

      {error ? <p className="rounded-md border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-200">{error}</p> : null}

      {result ? (
        <section className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h3 className="text-sm font-semibold text-zinc-100">Latest report</h3>
          <p className="text-xs text-zinc-400">Run ID: {result.run_id}</p>
          {graphSummary?.available ? (
            <div className="grid gap-2 text-xs text-zinc-300 sm:grid-cols-4">
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Graph steps</p>
                <p className="text-zinc-100">{graphSummary.step_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Avg seeds</p>
                <p className="text-zinc-100">{(graphSummary.avg_seed_count ?? 0).toFixed(2)}</p>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Avg expanded</p>
                <p className="text-zinc-100">{(graphSummary.avg_expanded_count ?? 0).toFixed(2)}</p>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Max docs</p>
                <p className="text-zinc-100">{graphSummary.max_document_count ?? 1}</p>
              </div>
            </div>
          ) : null}
          {graphRows.length ? (
            <div className="space-y-2 rounded-md border border-zinc-800 bg-zinc-950 p-3">
              <h4 className="text-xs font-semibold text-zinc-200">Graph retrieval diagnostics</h4>
              {graphRows.map((row, index) => (
                <div key={`${row.query}-${row.mode}-${index}`} className="text-xs text-zinc-300">
                  <span className="text-zinc-100">{row.mode}</span> {row.query}: seeds{" "}
                  {row.diagnostics?.seed_count ?? 0}, expanded {row.diagnostics?.expanded_count ?? 0}
                </div>
              ))}
            </div>
          ) : null}
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-zinc-200">
            {JSON.stringify(result.report, null, 2)}
          </pre>
        </section>
      ) : null}
    </div>
  );
}
