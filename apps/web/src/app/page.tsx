import { FileText, Layers, FileUp, Activity } from "lucide-react";
import Link from "next/link";
import { IngestForm } from "@/components/ingest-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getDocuments, getRuns } from "@/lib/api";

export default async function Home() {
  const [documentsData, runsData] = await Promise.all([getDocuments(), getRuns()]);
  const documents = documentsData.documents;
  const runs = runsData.runs;

  const stats = [
    { label: "Documents", value: documents.length, icon: FileText, color: "text-emerald-400" },
    { label: "Eval runs", value: runs.length, icon: Activity, color: "text-blue-400" },
    { label: "Latest document", value: documents[0]?.title ?? "None", icon: FileUp, color: "text-violet-400", truncate: true },
    { label: "Latest run", value: runs[0]?.id ?? "None", icon: Layers, color: "text-amber-400", mono: true, truncate: true },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-muted-foreground">Overview of documents and evaluation runs.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{stat.label}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <p className={`text-2xl font-bold ${stat.truncate ? "truncate" : ""} ${stat.mono ? "font-mono text-sm" : ""}`}>
                {stat.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent documents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {documents.slice(0, 8).map((document) => (
                <Link
                  key={document.id}
                  href={`/documents/${document.id}`}
                  className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 text-sm transition-colors hover:bg-accent"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{document.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-[10px]">
                      {document.page_count} pages
                    </Badge>
                    <span className="font-mono text-xs text-muted-foreground">{document.id}</span>
                  </div>
                </Link>
              ))}
              {documents.length === 0 && (
                <p className="py-8 text-center text-sm text-muted-foreground">No documents yet. Ingest one to get started.</p>
              )}
            </div>
          </CardContent>
        </Card>
        <IngestForm />
      </div>
    </div>
  );
}
