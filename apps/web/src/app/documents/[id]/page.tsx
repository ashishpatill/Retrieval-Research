import { FileText, Layers, BookOpen, Archive } from "lucide-react";
import { notFound } from "next/navigation";
import { DocumentActions } from "@/components/document-actions";
import { DocumentProfilePanel } from "@/components/document-profile-panel";
import { KnowledgeGraphInspector } from "@/components/knowledge-graph-inspector";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

  const doc = payload.document;
  const profile = payload.profile;
  const indexes = payload.stats.indexes;
  const indexList = Object.entries(indexes)
    .filter(([, v]) => v)
    .map(([k]) => k);

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{doc.title}</h1>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{doc.id}</p>
          </div>
          <div className="flex gap-2">
            {indexList.map((name) => (
              <Badge key={name} variant="secondary" className="text-[10px]">{name}</Badge>
            ))}
          </div>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">{doc.source_path}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Pages</CardTitle>
            <BookOpen className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{doc.pages.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Chunks</CardTitle>
            <Layers className="h-4 w-4 text-violet-400" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{payload.stats.chunk_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Indexes</CardTitle>
            <Archive className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <p className="text-lg font-bold">{indexList.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Source type</CardTitle>
            <FileText className="h-4 w-4 text-amber-400" />
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium">{String(doc.metadata?.source_type ?? "unknown")}</p>
          </CardContent>
        </Card>
      </div>

      <KnowledgeGraphInspector graph={payload.knowledge_graph} />

      <div className="grid gap-6 lg:grid-cols-3">
        <DocumentActions documentId={doc.id} />
        <DocumentProfilePanel profile={profile} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Page previews</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {doc.pages.slice(0, 8).map((page) => (
              <div key={page.id} className="rounded-lg border bg-card p-4">
                <p className="text-xs font-semibold text-muted-foreground">Page {page.number}</p>
                <p className="mt-2 line-clamp-4 text-sm text-foreground/80">{page.text || "(empty text)"}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
