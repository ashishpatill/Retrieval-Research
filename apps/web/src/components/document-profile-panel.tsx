"use client";

import { useMemo, useState } from "react";

type Props = {
  profile: Record<string, unknown> | null | undefined;
};

function readStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function DocumentProfilePanel({ profile }: Props) {
  const [query, setQuery] = useState("");
  const [copiedKind, setCopiedKind] = useState<string | null>(null);
  const profileObj: Record<string, unknown> = profile && typeof profile === "object" ? profile : {};
  const headings = readStringList(profileObj.headings);
  const topics = readStringList(profileObj.topics);
  const entities = readStringList(profileObj.entities);
  const referenceInventory =
    profileObj.structured_reference_inventory &&
    typeof profileObj.structured_reference_inventory === "object" &&
    !Array.isArray(profileObj.structured_reference_inventory)
      ? (profileObj.structured_reference_inventory as Record<string, unknown>)
      : {};

  const rows = useMemo(() => {
    const base = Object.keys(referenceInventory)
      .sort()
      .map((kind) => ({
        kind,
        refs: readStringList(referenceInventory[kind]),
      }));
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return base;
    }
    return base.filter(
      (row) => row.kind.toLowerCase().includes(normalized) || row.refs.some((ref) => ref.toLowerCase().includes(normalized)),
    );
  }, [query, referenceInventory]);

  return (
    <section className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900 p-4 lg:col-span-2">
      <h2 className="text-sm font-semibold text-zinc-100">Document profile</h2>
      <div className="grid gap-3 text-xs text-zinc-200 md:grid-cols-2">
        <div>
          <p className="text-zinc-400">Headings</p>
          <p className="mt-1">{headings.length}</p>
        </div>
        <div>
          <p className="text-zinc-400">Topics</p>
          <p className="mt-1">{topics.length}</p>
        </div>
        <div>
          <p className="text-zinc-400">Entities</p>
          <p className="mt-1">{entities.length}</p>
        </div>
        <div>
          <p className="text-zinc-400">Reference kinds</p>
          <p className="mt-1">{rows.length}</p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-300">Structured references</h3>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter references"
            className="w-48 rounded-md border border-zinc-700 bg-zinc-950 p-2 text-xs text-zinc-100"
          />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {rows.map((row) => (
            <div key={row.kind} className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-zinc-200">
                  {row.kind} <span className="text-zinc-500">({row.refs.length})</span>
                </p>
                <button
                  type="button"
                  onClick={async () => {
                    if (!row.refs.length || !navigator.clipboard) {
                      return;
                    }
                    await navigator.clipboard.writeText(row.refs.join("\n"));
                    setCopiedKind(row.kind);
                    setTimeout(() => setCopiedKind((current) => (current === row.kind ? null : current)), 1400);
                  }}
                  className="rounded border border-zinc-700 px-2 py-1 text-[10px] text-zinc-300 hover:bg-zinc-900 disabled:opacity-40"
                  disabled={!row.refs.length}
                >
                  {copiedKind === row.kind ? "Copied" : "Copy"}
                </button>
              </div>
              <p className="mt-1 max-h-24 overflow-auto text-[11px] text-zinc-400">
                {row.refs.length ? row.refs.join(", ") : "No references"}
              </p>
            </div>
          ))}
        </div>
        {!rows.length ? <p className="text-xs text-zinc-500">No references match the filter.</p> : null}
      </div>
    </section>
  );
}
