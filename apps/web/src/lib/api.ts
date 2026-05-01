export function apiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type DocumentListItem = {
  id: string;
  title: string;
  source_path: string;
  created_at: string;
  page_count: number;
  source_type?: string | null;
  profile?: Record<string, unknown> | null;
};

export type DocumentDetailResponse = {
  document: {
    id: string;
    title: string;
    source_path: string;
    pages: Array<{
      id: string;
      number: number;
      text?: string;
    }>;
    metadata?: Record<string, unknown>;
  };
  profile: Record<string, unknown> | null;
  stats: {
    chunk_count: number;
    indexes: Record<string, boolean>;
    knowledge_graph?: Record<string, unknown> | null;
  };
  knowledge_graph: Record<string, unknown> | null;
};

export type RunSummary = {
  id: string;
  path?: string;
  files: string[];
};

export async function getDocuments() {
  return apiFetch<{ documents: DocumentListItem[] }>("/api/documents");
}

export async function getDocument(documentId: string) {
  return apiFetch<DocumentDetailResponse>(`/api/documents/${encodeURIComponent(documentId)}`);
}

export async function getRuns() {
  return apiFetch<{ runs: RunSummary[] }>("/api/runs");
}

export async function getRun(runId: string) {
  return apiFetch<{ id: string; files: Record<string, unknown> }>(`/api/runs/${runId}`);
}
