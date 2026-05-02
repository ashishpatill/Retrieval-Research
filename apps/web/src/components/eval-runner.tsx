"use client";

import { useState } from "react";
import { apiBaseUrl } from "@/lib/api";

type EvalResponse = {
  run_id: string;
  report: {
    planner?: {
      merge_strategy?: string;
      rerank?: boolean;
      route_vote_bonus?: number;
      rerank_overlap_weight?: number;
      merge_strategies?: string[];
    };
    metrics?: {
      planner_sweep?: {
        available?: boolean;
        best_by_mrr?: string;
        best_by_confidence?: string;
        variants?: Array<{
          name?: string;
          merge_strategy?: string;
          rerank?: boolean;
          route_vote_bonus?: number;
          rerank_overlap_weight?: number;
          metrics?: {
            mrr?: number;
            avg_confidence?: number;
            term_hit_rate?: number;
            page_hit_rate?: number;
          };
        }>;
      };
      graph_diagnostics?: {
        available?: boolean;
        step_count?: number;
        avg_seed_count?: number;
        avg_expanded_count?: number;
        max_document_count?: number;
        relation_counts?: Record<string, number>;
      };
      visual_diagnostics?: {
        available?: boolean;
        visual_step_count?: number;
        visual_hit_count?: number;
        planner_query_count?: number;
        planner_visual_contribution_count?: number;
        planner_visual_contribution_rate?: number;
      };
      graph_extraction?: {
        available?: boolean;
        document_count?: number;
        totals?: {
          section_count?: number;
          entity_count?: number;
          reference_count?: number;
          edge_count?: number;
        };
        expected_recall?: Record<
          string,
          {
            available?: boolean;
            expected_count?: number;
            hit_count?: number;
            recall?: number;
          }
        >;
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
  const [modesText, setModesText] = useState("bm25,dense,late,hybrid,visual,graph,planner");
  const [plannerMergeStrategy, setPlannerMergeStrategy] = useState("score_max");
  const [plannerRerank, setPlannerRerank] = useState(true);
  const [plannerRouteVoteBonus, setPlannerRouteVoteBonus] = useState(0.08);
  const [plannerRerankOverlapWeight, setPlannerRerankOverlapWeight] = useState(0.1);
  const [plannerSweep, setPlannerSweep] = useState(false);
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
        body: JSON.stringify({
          manifest,
          top_k: topK,
          modes,
          planner_merge_strategy: plannerMergeStrategy,
          planner_rerank: plannerRerank,
          planner_route_vote_bonus: plannerRouteVoteBonus,
          planner_rerank_overlap_weight: plannerRerankOverlapWeight,
          planner_sweep: plannerSweep,
        }),
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
          .filter((step) => (step.path === "graph" || step.path === "graph_corpus") && step.diagnostics)
          .map((step) => ({ query: row.query, mode: row.mode, diagnostics: step.diagnostics })),
      )
      .slice(0, 8) ?? [];
  const graphSummary = result?.report.metrics?.graph_diagnostics;
  const visualSummary = result?.report.metrics?.visual_diagnostics;
  const extractionSummary = result?.report.metrics?.graph_extraction;
  const plannerSweepSummary = result?.report.metrics?.planner_sweep;

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
            placeholder="bm25,dense,late,hybrid,visual,graph,planner"
          />
        </div>
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
        <label className="flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-300">
          <input
            type="checkbox"
            checked={plannerSweep}
            onChange={(event) => setPlannerSweep(event.target.checked)}
          />
          Benchmark all planner merge/rerank variants
        </label>
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
          <p className="text-xs text-zinc-400">
            Planner merge: {result.report.planner?.merge_strategy ?? "score_max"} | rerank:{" "}
            {String(result.report.planner?.rerank ?? true)}
          </p>
          <p className="text-xs text-zinc-400">
            Vote bonus: {(result.report.planner?.route_vote_bonus ?? 0.08).toFixed(2)} | Overlap weight:{" "}
            {(result.report.planner?.rerank_overlap_weight ?? 0.1).toFixed(2)}
          </p>
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
          {visualSummary?.available ? (
            <div className="grid gap-2 text-xs text-zinc-300 sm:grid-cols-4">
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Visual steps</p>
                <p className="text-zinc-100">{visualSummary.visual_step_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Visual hits</p>
                <p className="text-zinc-100">{visualSummary.visual_hit_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Planner rows</p>
                <p className="text-zinc-100">{visualSummary.planner_query_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                <p className="text-zinc-500">Planner visual contribution</p>
                <p className="text-zinc-100">
                  {(visualSummary.planner_visual_contribution_rate ?? 0).toFixed(2)} (
                  {visualSummary.planner_visual_contribution_count ?? 0})
                </p>
              </div>
            </div>
          ) : null}
          {plannerSweepSummary?.available ? (
            <div className="space-y-2 rounded-md border border-zinc-800 bg-zinc-950 p-3">
              <h4 className="text-xs font-semibold text-zinc-200">Planner sweep</h4>
              <p className="text-xs text-zinc-400">
                Best MRR: {plannerSweepSummary.best_by_mrr} | Best confidence:{" "}
                {plannerSweepSummary.best_by_confidence}
              </p>
              <div className="grid gap-2 md:grid-cols-2">
                {(plannerSweepSummary.variants ?? []).map((variant) => (
                  <div key={variant.name} className="rounded border border-zinc-800 bg-zinc-900 p-2 text-xs text-zinc-300">
                    <p className="font-medium text-zinc-100">{variant.name}</p>
                    <p>
                      {variant.merge_strategy} | rerank {String(variant.rerank)} | MRR{" "}
                      {(variant.metrics?.mrr ?? 0).toFixed(3)} | confidence{" "}
                      {(variant.metrics?.avg_confidence ?? 0).toFixed(3)}
                    </p>
                    <p>
                      vote bonus {(variant.route_vote_bonus ?? 0.08).toFixed(2)} | overlap weight{" "}
                      {(variant.rerank_overlap_weight ?? 0.1).toFixed(2)}
                    </p>
                  </div>
                ))}
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
          {extractionSummary?.available ? (
            <div className="space-y-2 rounded-md border border-zinc-800 bg-zinc-950 p-3">
              <h4 className="text-xs font-semibold text-zinc-200">Graph extraction quality</h4>
              <div className="grid gap-2 text-xs text-zinc-300 sm:grid-cols-4">
                <div className="rounded border border-zinc-800 bg-zinc-900 p-2">
                  <p className="text-zinc-500">Graph docs</p>
                  <p className="text-zinc-100">{extractionSummary.document_count ?? 0}</p>
                </div>
                <div className="rounded border border-zinc-800 bg-zinc-900 p-2">
                  <p className="text-zinc-500">Sections</p>
                  <p className="text-zinc-100">{extractionSummary.totals?.section_count ?? 0}</p>
                </div>
                <div className="rounded border border-zinc-800 bg-zinc-900 p-2">
                  <p className="text-zinc-500">Entities</p>
                  <p className="text-zinc-100">{extractionSummary.totals?.entity_count ?? 0}</p>
                </div>
                <div className="rounded border border-zinc-800 bg-zinc-900 p-2">
                  <p className="text-zinc-500">References</p>
                  <p className="text-zinc-100">{extractionSummary.totals?.reference_count ?? 0}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(extractionSummary.expected_recall ?? {})
                  .filter(([, recall]) => recall.available)
                  .map(([label, recall]) => (
                    <span key={label} className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300">
                      {label}: {recall.hit_count ?? 0}/{recall.expected_count ?? 0} (
                      {((recall.recall ?? 0) * 100).toFixed(0)}%)
                    </span>
                  ))}
              </div>
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
