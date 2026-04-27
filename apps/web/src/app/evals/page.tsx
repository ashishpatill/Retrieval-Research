import { EvalRunner } from "@/components/eval-runner";
import { getRun, getRuns } from "@/lib/api";

export default async function EvalsPage() {
  const { runs } = await getRuns();
  const evalRun = runs.find((run) => run.files.includes("eval_report.json"));
  const latestEval = evalRun ? await getRun(evalRun.id) : null;
  const metrics = (latestEval?.files?.["eval_report.json"] as { metrics?: { modes?: Record<string, Record<string, number>> } })?.metrics
    ?.modes;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-zinc-100">Evals</h1>
      <div className="grid gap-4 lg:grid-cols-3">
        <EvalRunner />
        <section className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4 lg:col-span-2">
          <h2 className="text-sm font-semibold text-zinc-100">Latest eval metrics</h2>
          {metrics ? (
            <div className="space-y-2">
              {Object.entries(metrics).map(([mode, row]) => (
                <div key={mode} className="rounded-md border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-200">
                  <p className="font-semibold text-zinc-100">{mode}</p>
                  <p className="mt-1">
                    term_hit_rate={row.term_hit_rate?.toFixed?.(3) ?? row.term_hit_rate} page_hit_rate=
                    {row.page_hit_rate?.toFixed?.(3) ?? row.page_hit_rate} citation_support_rate=
                    {row.citation_support_rate?.toFixed?.(3) ?? row.citation_support_rate} mrr=
                    {row.mrr?.toFixed?.(3) ?? row.mrr}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-zinc-400">No eval report found yet.</p>
          )}
        </section>
      </div>
    </div>
  );
}
