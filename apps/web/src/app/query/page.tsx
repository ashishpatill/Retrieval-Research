import { QueryWorkbench } from "@/components/query-workbench";

export default function QueryPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-zinc-100">Query</h1>
      <QueryWorkbench />
    </div>
  );
}
