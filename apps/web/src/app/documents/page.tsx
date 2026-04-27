import Link from "next/link";
import { IngestForm } from "@/components/ingest-form";
import { getDocuments } from "@/lib/api";

export default async function DocumentsPage() {
  const { documents } = await getDocuments();
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-100">Documents</h1>
        <span className="rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-300">
          {documents.length} total
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-2 lg:col-span-2">
          {documents.map((document) => (
            <Link
              key={document.id}
              href={`/documents/${document.id}`}
              className="block rounded-lg border border-zinc-800 bg-zinc-900 p-4 hover:bg-zinc-800/60"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="truncate text-sm font-semibold text-zinc-100">{document.title}</p>
                <p className="font-mono text-[11px] text-zinc-400">{document.id}</p>
              </div>
              <p className="mt-2 text-xs text-zinc-300">{document.source_path}</p>
              <p className="mt-1 text-xs text-zinc-500">
                {document.page_count} pages | {document.source_type ?? "unknown source"}
              </p>
            </Link>
          ))}
          {documents.length === 0 ? (
            <p className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-400">No documents found.</p>
          ) : null}
        </div>
        <IngestForm />
      </div>
    </div>
  );
}
