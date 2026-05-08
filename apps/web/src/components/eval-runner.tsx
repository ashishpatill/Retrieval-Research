"use client";

import { useState } from "react";
import {
  Beaker,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  Network,
  Settings2,
  Eye,
  BarChart3,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/input";
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
  const [showPlannerOptions, setShowPlannerOptions] = useState(false);
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
        .map((m) => m.trim())
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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Beaker className="h-4 w-4" />
          Run eval
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="manifest">Manifest (JSON)</Label>
            <Textarea
              id="manifest"
              className="min-h-[160px] font-mono text-xs"
              value={manifestText}
              onChange={(e) => setManifestText(e.target.value)}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="topK">Top-K</Label>
              <Input id="topK" type="number" value={topK} min={1} max={20} onChange={(e) => setTopK(Number(e.target.value))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="modes">Modes (comma separated)</Label>
              <Input
                id="modes"
                value={modesText}
                onChange={(e) => setModesText(e.target.value)}
                placeholder="bm25,dense,late,hybrid,visual,graph,planner"
              />
            </div>
          </div>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowPlannerOptions(!showPlannerOptions)}
            className="flex items-center gap-1 text-xs text-muted-foreground"
          >
            <Settings2 className="h-3.5 w-3.5" />
            Planner options
            {showPlannerOptions ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </Button>
          {showPlannerOptions && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label className="text-xs">Merge</Label>
                <Select value={plannerMergeStrategy} onValueChange={setPlannerMergeStrategy}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="score_max">score_max</SelectItem>
                    <SelectItem value="route_vote">route_vote</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end gap-2 pb-1">
                <Checkbox id="sweepRerank" checked={plannerRerank} onCheckedChange={(v) => setPlannerRerank(!!v)} />
                <Label htmlFor="sweepRerank" className="text-xs font-normal">Rerank</Label>
              </div>
              <div className="space-y-2">
                <Label className="text-xs">Vote bonus</Label>
                <Input
                  type="number"
                  min={0} max={1} step={0.01}
                  value={plannerRouteVoteBonus}
                  onChange={(e) => setPlannerRouteVoteBonus(Number(e.target.value))}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs">Overlap weight</Label>
                <Input
                  type="number"
                  min={0} max={1} step={0.01}
                  value={plannerRerankOverlapWeight}
                  onChange={(e) => setPlannerRerankOverlapWeight(Number(e.target.value))}
                  className="h-8 text-xs"
                />
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <Checkbox id="sweep" checked={plannerSweep} onCheckedChange={(v) => setPlannerSweep(!!v)} />
            <Label htmlFor="sweep" className="text-xs font-normal">Benchmark all planner variants</Label>
          </div>

          <Button type="submit" disabled={isSubmitting}>
            <FlaskConical className="h-4 w-4" />
            {isSubmitting ? "Running..." : "Run eval"}
          </Button>
        </form>
      </CardContent>

      {error && (
        <CardContent>
          <p className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive-foreground">
            {error}
          </p>
        </CardContent>
      )}

      {result && (
        <CardContent className="space-y-4 border-t pt-4">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{result.run_id}</Badge>
            <span className="text-xs text-muted-foreground">
              {result.report.planner?.merge_strategy} | rerank: {String(result.report.planner?.rerank ?? true)}
            </span>
          </div>

          {graphSummary?.available && (
            <div className="grid gap-2 sm:grid-cols-4">
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Graph steps</p>
                <p className="text-sm font-semibold">{graphSummary.step_count ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Avg seeds</p>
                <p className="text-sm font-semibold">{(graphSummary.avg_seed_count ?? 0).toFixed(2)}</p>
              </div>
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Avg expanded</p>
                <p className="text-sm font-semibold">{(graphSummary.avg_expanded_count ?? 0).toFixed(2)}</p>
              </div>
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Max docs</p>
                <p className="text-sm font-semibold">{graphSummary.max_document_count ?? 1}</p>
              </div>
            </div>
          )}

          {visualSummary?.available && (
            <div className="grid gap-2 sm:grid-cols-4">
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Visual steps</p>
                <p className="text-sm font-semibold">{visualSummary.visual_step_count ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Hits</p>
                <p className="text-sm font-semibold">{visualSummary.visual_hit_count ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Planner rows</p>
                <p className="text-sm font-semibold">{visualSummary.planner_query_count ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-card p-2">
                <p className="text-[10px] text-muted-foreground">Contribution</p>
                <p className="text-sm font-semibold">
                  {(visualSummary.planner_visual_contribution_rate ?? 0).toFixed(2)}
                </p>
              </div>
            </div>
          )}

          {plannerSweepSummary?.available && (
            <div className="rounded-lg border bg-card p-3">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold">
                <BarChart3 className="h-3.5 w-3.5" />
                Planner sweep
              </h4>
              <p className="mt-1 text-xs text-muted-foreground">
                Best MRR: <span className="font-medium text-foreground">{plannerSweepSummary.best_by_mrr}</span>
                {" | "}Best confidence: <span className="font-medium text-foreground">{plannerSweepSummary.best_by_confidence}</span>
              </p>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {(plannerSweepSummary.variants ?? []).map((variant) => (
                  <div key={variant.name} className="rounded border bg-card p-2 text-xs">
                    <p className="font-medium">{variant.name}</p>
                    <p className="mt-0.5 text-muted-foreground">
                      {variant.merge_strategy} | MRR {(variant.metrics?.mrr ?? 0).toFixed(3)} | conf{" "}
                      {(variant.metrics?.avg_confidence ?? 0).toFixed(3)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {graphRows.length > 0 && (
            <div className="rounded-lg border bg-card p-3">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold">
                <Network className="h-3.5 w-3.5" />
                Graph retrieval diagnostics
              </h4>
              {graphRows.map((row, idx) => (
                <p key={`${row.query}-${row.mode}-${idx}`} className="mt-1 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{row.mode}</span> {row.query}: seeds{" "}
                  {row.diagnostics?.seed_count ?? 0}, expanded {row.diagnostics?.expanded_count ?? 0}
                </p>
              ))}
            </div>
          )}

          {extractionSummary?.available && (
            <div className="rounded-lg border bg-card p-3">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold">
                <Eye className="h-3.5 w-3.5" />
                Graph extraction quality
              </h4>
              <div className="mt-2 grid gap-2 sm:grid-cols-4">
                <div className="rounded border bg-card p-2">
                  <p className="text-[10px] text-muted-foreground">Docs</p>
                  <p className="text-sm font-semibold">{extractionSummary.document_count ?? 0}</p>
                </div>
                <div className="rounded border bg-card p-2">
                  <p className="text-[10px] text-muted-foreground">Sections</p>
                  <p className="text-sm font-semibold">{extractionSummary.totals?.section_count ?? 0}</p>
                </div>
                <div className="rounded border bg-card p-2">
                  <p className="text-[10px] text-muted-foreground">Entities</p>
                  <p className="text-sm font-semibold">{extractionSummary.totals?.entity_count ?? 0}</p>
                </div>
                <div className="rounded border bg-card p-2">
                  <p className="text-[10px] text-muted-foreground">References</p>
                  <p className="text-sm font-semibold">{extractionSummary.totals?.reference_count ?? 0}</p>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {Object.entries(extractionSummary.expected_recall ?? {})
                  .filter(([, r]) => r.available)
                  .map(([label, r]) => (
                    <Badge key={label} variant="outline" className="text-[10px]">
                      {label}: {r.hit_count ?? 0}/{r.expected_count ?? 0} ({(r.recall ?? 0) * 100}%)
                    </Badge>
                  ))}
              </div>
            </div>
          )}

          <div className="rounded-lg border bg-card p-3">
            <details>
              <summary className="cursor-pointer text-xs font-semibold text-muted-foreground hover:text-foreground">
                Raw report JSON
              </summary>
              <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">
                {JSON.stringify(result.report, null, 2)}
              </pre>
            </details>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
