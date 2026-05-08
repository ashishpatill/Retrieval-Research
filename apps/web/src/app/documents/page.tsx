import { BookOpen, FileText } from "lucide-react";
import Link from "next/link";
import { IngestForm } from "@/components/ingest-form";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDocuments } from "@/lib/api";

export default async function DocumentsPage() {
  const { documents } = await getDocuments();
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
          <p className="mt-1 text-muted-foreground">{documents.length} document{documents.length !== 1 ? "s" : ""} indexed.</p>
        </div>
        <Badge variant="secondary" className="text-xs">{documents.length} total</Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          {documents.map((document) => (
            <Link key={document.id} href={`/documents/${document.id}`}>
              <Card className="transition-colors hover:bg-accent/50">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <FileText className="mt-0.5 h-5 w-5 text-primary" />
                      <div>
                        <p className="font-semibold leading-none">{document.title}</p>
                        <p className="mt-1.5 text-sm text-muted-foreground">{document.source_path}</p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {document.page_count} pages
                      </Badge>
                      <span className="font-mono text-xs text-muted-foreground">{document.id}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
          {documents.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-12">
                <BookOpen className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No documents found.</p>
              </CardContent>
            </Card>
          )}
        </div>
        <IngestForm />
      </div>
    </div>
  );
}
