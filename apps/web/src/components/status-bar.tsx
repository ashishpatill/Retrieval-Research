"use client";

import { useEffect, useState } from "react";
import { Check, X, Loader2 } from "lucide-react";
import { apiBaseUrl } from "@/lib/api";

type Health = {
  mlx_available: boolean;
  gemini_configured: boolean;
};

export function StatusBar() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${apiBaseUrl()}/api/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  if (!health && !error) return null;

  return (
    <div className="border-b bg-muted/30 text-xs text-muted-foreground">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-1.5">
        <span className="font-medium">System</span>
        <span className="inline-flex items-center gap-1">
          {health ? (
            health.mlx_available ? (
              <Check className="h-3 w-3 text-emerald-400" />
            ) : (
              <X className="h-3 w-3 text-amber-400" />
            )
          ) : (
            <Loader2 className="h-3 w-3 animate-spin" />
          )}
          MLX
        </span>
        <span className="inline-flex items-center gap-1">
          {health ? (
            health.gemini_configured ? (
              <Check className="h-3 w-3 text-emerald-400" />
            ) : (
              <X className="h-3 w-3 text-amber-400" />
            )
          ) : (
            <Loader2 className="h-3 w-3 animate-spin" />
          )}
          Gemini
        </span>
      </div>
    </div>
  );
}
