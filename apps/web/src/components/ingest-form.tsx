"use client";

import { useState } from "react";
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
      setMessage("Pick a file first.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${apiBaseUrl()}/api/documents/ingest`, {
        method: "POST",
        body: data,
      });
      const payload = await response.json();
      if (!response.ok) {
        setMessage(payload?.detail || "Upload failed.");
      } else {
        setMessage(`Ingested document ${payload.document_id}. Refresh to see it in the list.`);
        form.reset();
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h3 className="text-sm font-semibold text-zinc-100">Ingest document</h3>
      <input
        type="file"
        name="file"
        className="block w-full rounded-md border border-zinc-700 bg-zinc-950 p-2 text-sm text-zinc-200"
      />
      <div className="grid grid-cols-3 gap-2">
        <label className="flex items-center gap-2 text-xs text-zinc-300">
          <input type="checkbox" name="ocr" value="true" />
          OCR
        </label>
        <select
          name="mode"
          defaultValue="Hybrid"
          className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-200"
        >
          <option value="Hybrid">Hybrid</option>
          <option value="Pure Local">Pure Local</option>
          <option value="Pure Cloud">Pure Cloud</option>
        </select>
        <input
          type="number"
          name="dpi"
          defaultValue={150}
          min={72}
          className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-200"
        />
      </div>
      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
      >
        {isSubmitting ? "Ingesting..." : "Upload and ingest"}
      </button>
      {message ? <p className="text-xs text-zinc-300">{message}</p> : null}
    </form>
  );
}
