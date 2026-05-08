"use client";

import { cn } from "@/lib/utils";
import { BookOpen, FlaskConical, Home, Search, Layers } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/documents", label: "Documents", icon: BookOpen },
  { href: "/query", label: "Query", icon: Search },
  { href: "/evals", label: "Evals", icon: FlaskConical },
];

export function TopNav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <Layers className="h-5 w-5 text-primary" />
          <span>Retrieval Research</span>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <link.icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
