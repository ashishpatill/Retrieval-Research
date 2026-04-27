import Link from "next/link";
import { IngestForm } from "@/components/ingest-form";
import { getDocuments, getRuns } from "@/lib/api";

export default async function Home() {
  const [documentsData, runsData] = await Promise.all([getDocuments(), getRuns()]);
  const documents = documentsData.documents;
  const runs = runsData.runs;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Documents</p>
          <p className="mt-2 text-2xl font-semibold text-zinc-100">{documents.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Runs</p>
          <p className="mt-2 text-2xl font-semibold text-zinc-100">{runs.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Latest document</p>
          <p className="mt-2 truncate text-sm text-zinc-200">{documents[0]?.title ?? "None"}</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-400">Latest run</p>
          <p className="mt-2 truncate font-mono text-xs text-zinc-200">{runs[0]?.id ?? "None"}</p>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-semibold text-zinc-100">Recent documents</h2>
          <div className="space-y-2">
            {documents.slice(0, 8).map((document) => (
              <Link
                key={document.id}
                href={`/documents/${document.id}`}
                className="flex items-center justify-between rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-900"
              >
                <span className="truncate">{document.title}</span>
                <span className="ml-3 font-mono text-[11px] text-zinc-400">{document.id}</span>
              </Link>
            ))}
            {documents.length === 0 ? <p className="text-xs text-zinc-400">No documents yet.</p> : null}
          </div>
        </div>
        <IngestForm />
      </section>
    </div>
  );
}
