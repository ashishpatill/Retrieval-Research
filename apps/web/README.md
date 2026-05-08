# Retrieval Inspector Web UI

This app is the Next.js inspector frontend for the retrieval research backend.

## Current Scope

- Document library and document detail views
- Query workbench with retrieval trace inspection
- Eval runner with report rendering
- Graph retrieval diagnostics in query and eval views
- Document-level knowledge graph stats in the detail page

## Progress Snapshot (2026-05-09 — UI/UX Overhaul)

- Complete UI redesign with professional dark theme and shadcn-style component system.
- Added 9 UI primitives: Button, Card, Badge, Input/Textarea, Select, Tabs, Dialog, Checkbox, Label, Skeleton — all built on `@radix-ui/*` headless primitives and `class-variance-authority`.
- Navigation upgraded to sticky header with backdrop blur, lucide-react icons, and active state highlighting.
- Dashboard redesigned with color-coded stat cards, icon-badged document list, and consistent spacing.
- Documents list uses card-based layout with source badges and page counts.
- Document detail shows index status badges, stat cards (pages/chunks/indexes/source type), and page previews.
- Ingest form uses Select and Checkbox primitives with proper labels and layout.
- Query workbench redesigned with collapsible planner options section, card-based answer/knowledge card/results layout, and graph/visual diagnostics as separate cards.
- Knowledge graph inspector uses Tabs for entities/sections/references with relation filter Select and search input.
- Document profile panel shows reference inventory as card grid with badge counters.
- Eval runner redesigned with structured metrics grid, collapsible planner options, and raw report JSON in collapsible details element.
- All forms use proper label+input associations, consistent spacing, and responsive grid layouts.
- Next.js build compiles with zero errors.

## Local Development

From this directory:

```bash
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Backend Requirement

Run the API server from repository root:

```bash
python3 -m uvicorn retrieval_research.api:app --host 127.0.0.1 --port 8000 --reload
```
