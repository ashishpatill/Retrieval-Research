"use client";

import { useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { apiBaseUrl } from "@/lib/api";

export function IngestForm() {
  const [message, setMessage] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    const form = event.currentTarget;
    const data = new FormData(form);
    if (!data.get("file")) {
      setMessage("Select a file first.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${apiBaseUrl()}/api/documents/ingest?sync=true`, {
        method: "POST",
        body: data,
      });
      const payload = await response.json();
      if (!response.ok) {
        setMessage(payload?.detail || "Upload failed.");
      } else {
        setMessage(`Ingested: ${payload.document_id}. Refresh to see it.`);
        form.reset();
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-4 w-4" />
          Ingest document
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="file">File</Label>
            <Input id="file" type="file" name="file" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="mode">Mode</Label>
              <Select name="mode" defaultValue="Hybrid">
                <SelectTrigger id="mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Hybrid">Hybrid</SelectItem>
                  <SelectItem value="Pure Local">Pure Local</SelectItem>
                  <SelectItem value="Pure Cloud">Pure Cloud</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="dpi">DPI</Label>
              <Input id="dpi" type="number" name="dpi" defaultValue={150} min={72} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="ocr" name="ocr" value="true" />
            <Label htmlFor="ocr" className="text-sm font-normal">Run OCR</Label>
          </div>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Ingesting..." : "Upload & ingest"}
          </Button>
          {message && <p className="text-xs text-muted-foreground">{message}</p>}
        </form>
      </CardContent>
    </Card>
  );
}
