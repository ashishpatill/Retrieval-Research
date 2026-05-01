"use client";

import { useMemo, useState } from "react";

type GraphSection = {
  name?: string;
  chunk_ids?: string[];
  document_ids?: string[];
  pages?: number[];
};

type GraphEntity = {
  name?: string;
  chunk_ids?: string[];
  document_ids?: string[];
  pages?: number[];
};

type GraphReference = {
  reference?: string;
  source_chunk_ids?: string[];
  target_chunk_ids?: string[];
  document_ids?: string[];
};

type KnowledgeGraph = {
  stats?: {
    node_count?: number;
    edge_count?: number;
    section_count?: number;
    entity_count?: number;
    reference_count?: number;
    relation_counts?: Record<string, number>;
  };
  sections?: GraphSection[];
  entities?: GraphEntity[];
  references?: GraphReference[];
};

type Props = {
  graph: KnowledgeGraph | null;
};

type ArtifactKind = "sections" | "entities" | "references";

export function KnowledgeGraphInspector({ graph }: Props) {
  const [artifactKind, setArtifactKind] = useState<ArtifactKind>("entities");
  const [relationFilter, setRelationFilter] = useState("all");
  const [query, setQuery] = useState("");

  const relationRows = useMemo(
    () => Object.entries(graph?.stats?.relation_counts ?? {}).sort((left, right) => right[1] - left[1]),
    [graph],
  );
  const artifactRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const rows = graph?.[artifactKind] ?? [];
    if (!normalizedQuery) {
      return rows;
    }
    return rows.filter((row) => JSON.stringify(row).toLowerCase().includes(normalizedQuery));
  }, [artifactKind, graph, query]);

  if (!graph?.stats) {
    return null;
  }

  return (
    <section className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">Knowledge graph</h2>
          <p className="mt-1 text-xs text-zinc-500">Inspect extracted graph artifacts and relation mix.</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <select
            value={artifactKind}
            onChange={(event) => setArtifactKind(event.target.value as ArtifactKind)}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          >
            <option value="entities">Entities</option>
            <option value="sections">Sections</option>
            <option value="references">References</option>
          </select>
          <select
            value={relationFilter}
            onChange={(event) => setRelationFilter(event.target.value)}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          >
            <option value="all">All relations</option>
            {relationRows.map(([relation]) => (
              <option key={relation} value={relation}>
                {relation}
              </option>
            ))}
          </select>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`Filter ${artifactKind}`}
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          />
        </div>
      </div>

      <div className="grid gap-2 text-xs text-zinc-300 sm:grid-cols-5">
        <StatCard label="Nodes" value={graph.stats.node_count ?? 0} />
        <StatCard label="Edges" value={graph.stats.edge_count ?? 0} />
        <StatCard label="Sections" value={graph.stats.section_count ?? 0} />
        <StatCard label="Entities" value={graph.stats.entity_count ?? 0} />
        <StatCard label="References" value={graph.stats.reference_count ?? 0} />
      </div>

      {relationRows.length ? (
        <div className="flex flex-wrap gap-2">
          {relationRows
            .filter(([relation]) => relationFilter === "all" || relation === relationFilter)
            .map(([relation, count]) => (
              <span
                key={relation}
                className="rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-300"
              >
                {relation}: {count}
              </span>
            ))}
        </div>
      ) : null}

      <div className="space-y-2 rounded-md border border-zinc-800 bg-zinc-950 p-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-400">{artifactKind}</h3>
          <span className="text-xs text-zinc-500">{artifactRows.length} shown</span>
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          {artifactRows.slice(0, 24).map((row, index) => (
            <ArtifactCard key={`${artifactKind}-${index}`} kind={artifactKind} row={row} />
          ))}
        </div>
        {!artifactRows.length ? <p className="text-xs text-zinc-500">No matching graph artifacts.</p> : null}
      </div>
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
      <p className="text-zinc-500">{label}</p>
      <p className="text-zinc-100">{value}</p>
    </div>
  );
}

function ArtifactCard({
  kind,
  row,
}: {
  kind: ArtifactKind;
  row: GraphSection | GraphEntity | GraphReference;
}) {
  const title =
    kind === "references" ? (row as GraphReference).reference : (row as GraphSection | GraphEntity).name;
  const chunkCount =
    kind === "references"
      ? ((row as GraphReference).source_chunk_ids?.length ?? 0) + ((row as GraphReference).target_chunk_ids?.length ?? 0)
      : ((row as GraphSection | GraphEntity).chunk_ids?.length ?? 0);
  const pages = "pages" in row ? row.pages ?? [] : [];

  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-900 p-2 text-xs text-zinc-300">
      <p className="truncate font-medium text-zinc-100">{title ?? "(untitled)"}</p>
      <p className="mt-1 text-zinc-500">
        {chunkCount} chunks
        {pages.length ? ` | pages ${pages.slice(0, 6).join(", ")}` : ""}
      </p>
      {(row.document_ids?.length ?? 0) > 0 ? (
        <p className="mt-1 truncate font-mono text-[11px] text-zinc-500">{row.document_ids?.join(", ")}</p>
      ) : null}
    </div>
  );
}
