import { FlaskConical, TrendingUp } from "lucide-react";
import { EvalRunner } from "@/components/eval-runner";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getRun, getRuns } from "@/lib/api";

export default async function EvalsPage() {
  const { runs } = await getRuns();
  const evalRun = runs.find((run) => run.files.includes("eval_report.json"));
  const latestEval = evalRun ? await getRun(evalRun.id) : null;
  const metrics = (
    latestEval?.files?.["eval_report.json"] as {
      metrics?: { modes?: Record<string, Record<string, number>> };
    }
  )?.metrics?.modes;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Evals</h1>
        <p className="mt-1 text-muted-foreground">Run evaluations and inspect benchmark metrics.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <EvalRunner />

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Latest eval metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            {metrics ? (
              <div className="space-y-2">
                {Object.entries(metrics).map(([mode, row]) => (
                  <div key={mode} className="rounded-lg border bg-card p-4">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{mode}</Badge>
                    </div>
                    <div className="mt-2 grid gap-2 text-sm sm:grid-cols-4">
                      <div>
                        <span className="text-xs text-muted-foreground">term_hit_rate</span>
                        <p className="font-mono text-xs">{row.term_hit_rate?.toFixed?.(3) ?? row.term_hit_rate}</p>
                      </div>
                      <div>
                        <span className="text-xs text-muted-foreground">page_hit_rate</span>
                        <p className="font-mono text-xs">{row.page_hit_rate?.toFixed?.(3) ?? row.page_hit_rate}</p>
                      </div>
                      <div>
                        <span className="text-xs text-muted-foreground">citation_support</span>
                        <p className="font-mono text-xs">
                          {row.citation_support_rate?.toFixed?.(3) ?? row.citation_support_rate}
                        </p>
                      </div>
                      <div>
                        <span className="text-xs text-muted-foreground">MRR</span>
                        <p className="font-mono text-xs">{row.mrr?.toFixed?.(3) ?? row.mrr}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3 py-12">
                <FlaskConical className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No eval report found.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
