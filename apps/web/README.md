# Web Inspector

Next.js 16 frontend for the Retrieval Research backend. Professional dark theme with shadcn-style UI primitives and lucide-react icons.

## Quick start

```bash
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Requires the backend API running:

```bash
python3 -m uvicorn retrieval_research.api:app --host 127.0.0.1 --port 8000 --reload
```

## Pages

- `/` — Dashboard with document stats and recent activity
- `/documents` — Document library with card-based layout
- `/documents/[id]` — Document detail with knowledge graph, profile, and page previews
- `/query` — Query workbench with planner controls and result diagnostics
- `/evals` — Evaluation runner with manifest editor and multi-mode benchmarks

## Tech

- Next.js 16 (App Router) · React 19 · TypeScript
- Tailwind CSS v4 with CSS design tokens
- shadcn-style primitives on `@radix-ui/*` + `class-variance-authority`
- lucide-react icons
