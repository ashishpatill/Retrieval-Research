"use client";

import { useMemo, useState } from "react";
import { Copy, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

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
    if (!normalized) return base;
    return base.filter(
      (row) =>
        row.kind.toLowerCase().includes(normalized) ||
        row.refs.some((ref) => ref.toLowerCase().includes(normalized)),
    );
  }, [query, referenceInventory]);

  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>Document profile</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Headings</p>
            <p className="text-lg font-semibold">{headings.length}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Topics</p>
            <p className="text-lg font-semibold">{topics.length}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Entities</p>
            <p className="text-lg font-semibold">{entities.length}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Reference kinds</p>
            <p className="text-lg font-semibold">{rows.length}</p>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Structured references
            </h3>
            <div className="relative w-48">
              <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter"
                className="h-8 pl-7 text-xs"
              />
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {rows.map((row) => (
              <div key={row.kind} className="rounded-lg border bg-card p-3">
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="text-xs">{row.kind}</Badge>
                  <span className="text-xs text-muted-foreground">{row.refs.length}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                  {row.refs.length ? row.refs.join(", ") : "No references"}
                </p>
              </div>
            ))}
          </div>
          {!rows.length && <p className="text-xs text-muted-foreground">No matches.</p>}
        </div>
      </CardContent>
    </Card>
  );
}
