import { notFound } from "next/navigation";
import { DocumentActions } from "@/components/document-actions";
import { getDocument } from "@/lib/api";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function DocumentDetailPage({ params }: Props) {
  const { id } = await params;
  let payload;
  try {
    payload = await getDocument(id);
  } catch {
    notFound();
  }

  const document = payload.document;
  const profile = payload.profile;
  const graphStats = payload.stats.knowledge_graph;
  const relationCounts = Object.entries(graphStats?.relation_counts ?? {}).sort((left, right) => right[1] - left[1]);
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h1 className="text-lg font-semibold text-zinc-100">{document.title}</h1>
        <p className="mt-1 font-mono text-xs text-zinc-400">{document.id}</p>
        <p className="mt-2 text-sm text-zinc-300">{document.source_path}</p>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Pages</p>
          <p className="mt-2 text-2xl font-semibold text-zinc-100">{document.pages.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Chunks</p>
          <p className="mt-2 text-2xl font-semibold text-zinc-100">{payload.stats.chunk_count}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Indexes</p>
          <p className="mt-2 text-xs text-zinc-200">
            bm25:{String(payload.stats.indexes.bm25)} dense:{String(payload.stats.indexes.dense)} visual:
            {String(payload.stats.indexes.visual)} graph:{String(payload.stats.indexes.graph ?? false)}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Source type</p>
          <p className="mt-2 text-sm text-zinc-200">{String(document.metadata?.source_type ?? "unknown")}</p>
        </div>
      </section>

      {graphStats ? (
        <section className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-semibold text-zinc-100">Knowledge graph</h2>
          <div className="grid gap-2 text-xs text-zinc-300 sm:grid-cols-5">
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
              <p className="text-zinc-500">Nodes</p>
              <p className="text-zinc-100">{graphStats.node_count ?? 0}</p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
              <p className="text-zinc-500">Edges</p>
              <p className="text-zinc-100">{graphStats.edge_count ?? 0}</p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
              <p className="text-zinc-500">Sections</p>
              <p className="text-zinc-100">{graphStats.section_count ?? 0}</p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
              <p className="text-zinc-500">Entities</p>
              <p className="text-zinc-100">{graphStats.entity_count ?? 0}</p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
              <p className="text-zinc-500">References</p>
              <p className="text-zinc-100">{graphStats.reference_count ?? 0}</p>
            </div>
          </div>
          {relationCounts.length ? (
            <div className="flex flex-wrap gap-2">
              {relationCounts.map(([relation, count]) => (
                <span key={relation} className="rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-300">
                  {relation}: {count}
                </span>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <DocumentActions documentId={document.id} />
        <section className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-900 p-4 lg:col-span-2">
          <h2 className="text-sm font-semibold text-zinc-100">Document profile</h2>
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs text-zinc-200">
            {JSON.stringify(profile ?? {}, null, 2)}
          </pre>
        </section>
      </div>

      <section className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-semibold text-zinc-100">Page previews</h2>
        <div className="space-y-3">
          {document.pages.slice(0, 8).map((page) => (
            <div key={page.id} className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
              <p className="text-xs font-semibold text-zinc-300">Page {page.number}</p>
              <p className="mt-2 line-clamp-4 text-xs text-zinc-400">{page.text || "(empty text)"}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
