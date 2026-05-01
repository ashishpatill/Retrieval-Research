"use client";

import { useState } from "react";
import { apiBaseUrl } from "@/lib/api";

type ResultPayload = {
  run_id: string;
  result: {
    answer: string;
    knowledge_card?: {
      confidence?: number;
      answerable?: boolean;
      answerability_reason?: string;
      unresolved_ambiguity?: string[];
      follow_up_retrieval_suggestions?: string[];
    } & Record<string, unknown>;
    evidence?: EvidenceItem[];
  };
  trace: { steps?: TraceStep[] } & Record<string, unknown>;
};

type EvidenceItem = {
  chunk_id?: string;
  score?: number;
  metadata?: {
    graph_relations?: string[];
    graph_expanded_from?: string[];
  } & Record<string, unknown>;
};

type TraceStep = {
  path?: string;
  document_id?: string;
  document_ids?: string[];
  hits?: number;
  diagnostics?: {
    node_count?: number;
    edge_count?: number;
    seed_count?: number;
    expanded_count?: number;
    relation_counts?: Record<string, number>;
    expanded_relation_counts?: Record<string, number>;
    query_entities?: string[];
    query_references?: string[];
  };
  [key: string]: unknown;
};

function GraphDiagnostics({ payload }: { payload: ResultPayload }) {
  const [relationFilter, setRelationFilter] = useState("all");
  const graphSteps = (payload.trace.steps ?? []).filter(
    (step) => (step.path === "graph" || step.path === "graph_corpus") && step.diagnostics,
  );
  const graphEvidence = (payload.result.evidence ?? []).filter((item) => item.metadata?.graph_relations?.length);

  if (!graphSteps.length && !graphEvidence.length) {
    return null;
  }

  const relationCounts = graphSteps.reduce<Record<string, number>>((acc, step) => {
    const counts = step.diagnostics?.expanded_relation_counts ?? step.diagnostics?.relation_counts ?? {};
    for (const [relation, count] of Object.entries(counts)) {
      acc[relation] = (acc[relation] ?? 0) + count;
    }
    return acc;
  }, {});
  const relationRows = Object.entries(relationCounts).sort((left, right) => right[1] - left[1]);
  const filteredEvidence =
    relationFilter === "all"
      ? graphEvidence
      : graphEvidence.filter((item) => item.metadata?.graph_relations?.includes(relationFilter));

  return (
    <section className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4 lg:col-span-2">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-sm font-semibold text-zinc-100">Graph diagnostics</h3>
        {relationRows.length ? (
          <select
            value={relationFilter}
            onChange={(event) => setRelationFilter(event.target.value)}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          >
            <option value="all">All relations</option>
            {relationRows.map(([relation]) => (
              <option key={relation} value={relation}>
                {relation}
              </option>
            ))}
          </select>
        ) : null}
      </div>
      {graphSteps.map((step, index) => (
        <div
          key={`${step.document_id ?? step.document_ids?.join("-") ?? "doc"}-${index}`}
          className="grid gap-2 text-xs text-zinc-300 sm:grid-cols-4"
        >
          <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
            <p className="text-zinc-500">Nodes</p>
            <p className="text-zinc-100">{step.diagnostics?.node_count ?? 0}</p>
          </div>
          <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
            <p className="text-zinc-500">Edges</p>
            <p className="text-zinc-100">{step.diagnostics?.edge_count ?? 0}</p>
          </div>
          <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
            <p className="text-zinc-500">Seeds</p>
            <p className="text-zinc-100">{step.diagnostics?.seed_count ?? 0}</p>
          </div>
          <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
            <p className="text-zinc-500">Expanded</p>
            <p className="text-zinc-100">{step.diagnostics?.expanded_count ?? 0}</p>
          </div>
        </div>
      ))}
      {relationRows.length ? (
        <div className="flex flex-wrap gap-2">
          {relationRows
            .filter(([relation]) => relationFilter === "all" || relation === relationFilter)
            .map(([relation, count]) => (
              <span key={relation} className="rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-300">
                {relation}: {count}
              </span>
            ))}
        </div>
      ) : null}
      {filteredEvidence.length ? (
        <div className="space-y-2">
          {filteredEvidence.slice(0, 5).map((item) => (
            <div key={item.chunk_id} className="rounded-md border border-zinc-800 bg-zinc-950 p-2 text-xs text-zinc-300">
              <p className="text-zinc-100">{item.chunk_id}</p>
              <p>Relations: {item.metadata?.graph_relations?.join(", ")}</p>
            </div>
          ))}
        </div>
      ) : graphEvidence.length ? (
        <p className="text-xs text-zinc-500">No evidence matched the selected relation.</p>
      ) : null}
    </section>
  );
}

export function QueryWorkbench() {
  const [question, setQuestion] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [mode, setMode] = useState("planner");
  const [topK, setTopK] = useState(5);
  const [plannerMergeStrategy, setPlannerMergeStrategy] = useState("score_max");
  const [plannerRerank, setPlannerRerank] = useState(false);
  const [plannerRouteVoteBonus, setPlannerRouteVoteBonus] = useState(0.08);
  const [plannerRerankOverlapWeight, setPlannerRerankOverlapWeight] = useState(0.15);
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
          planner_merge_strategy: plannerMergeStrategy,
          planner_rerank: plannerRerank,
          planner_route_vote_bonus: plannerRouteVoteBonus,
          planner_rerank_overlap_weight: plannerRerankOverlapWeight,
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
            <option value="graph">graph</option>
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
        {mode === "planner" ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <select
              value={plannerMergeStrategy}
              onChange={(event) => setPlannerMergeStrategy(event.target.value)}
              className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
            >
              <option value="score_max">score_max merge</option>
              <option value="route_vote">route_vote merge</option>
            </select>
            <label className="flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-300">
              <input
                type="checkbox"
                checked={plannerRerank}
                onChange={(event) => setPlannerRerank(event.target.checked)}
              />
              Query-overlap rerank
            </label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={plannerRouteVoteBonus}
              onChange={(event) => setPlannerRouteVoteBonus(Number(event.target.value))}
              className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
              placeholder="Route vote bonus"
            />
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={plannerRerankOverlapWeight}
              onChange={(event) => setPlannerRerankOverlapWeight(Number(event.target.value))}
              className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
              placeholder="Rerank overlap weight"
            />
          </div>
        ) : null}
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
            {(payload.result.knowledge_card?.unresolved_ambiguity?.length ?? 0) > 0 ? (
              <div className="rounded-md border border-amber-900 bg-amber-950/30 p-2 text-xs text-amber-100">
                {payload.result.knowledge_card?.unresolved_ambiguity?.map((item) => <p key={item}>{item}</p>)}
              </div>
            ) : null}
            {(payload.result.knowledge_card?.follow_up_retrieval_suggestions?.length ?? 0) > 0 ? (
              <div className="rounded-md border border-sky-900 bg-sky-950/30 p-2 text-xs text-sky-100">
                {payload.result.knowledge_card?.follow_up_retrieval_suggestions?.map((item) => <p key={item}>{item}</p>)}
              </div>
            ) : null}
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-zinc-200">
              {JSON.stringify(payload.result.knowledge_card ?? {}, null, 2)}
            </pre>
          </section>
          <GraphDiagnostics payload={payload} />
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
