"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconBooks, IconFolder, IconPlus, IconSparkles } from "@tabler/icons-react";

import { cn } from "@/lib/utils";

const nav = [
  { href: "/projects", label: "Проекты", icon: IconFolder },
  { href: "/catalogs", label: "Каталоги", icon: IconBooks },
  { href: "/catalogs/new", label: "Новый каталог", icon: IconPlus },
] as const;

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-bold tracking-[0.18em] text-[var(--color-brand)] uppercase"
        >
          <IconSparkles className="size-4" stroke={1.75} />
          AVGST Catalog Builder
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2">
          {nav.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/catalogs"
                ? pathname === "/catalogs" ||
                  (pathname.startsWith("/catalogs/") && !pathname.startsWith("/catalogs/new"))
                : pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                )}
              >
                <Icon className="size-4 shrink-0" stroke={1.75} />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
