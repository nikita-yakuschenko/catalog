"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconBooks, IconFileText, IconFolder, IconLogout, IconPlus } from "@tabler/icons-react";

import { useAuth } from "@/components/auth-provider";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/projects", label: "Проекты", icon: IconFolder },
  { href: "/proposals", label: "Коммерческие предложения", icon: IconFileText },
  { href: "/catalogs", label: "Каталоги", icon: IconBooks },
  { href: "/catalogs/new", label: "Новый каталог", icon: IconPlus },
] as const;

export function AppHeader() {
  const pathname = usePathname();
  const { user, status, logout, loading } = useAuth();
  const onLogin = pathname === "/login";
  const displayName =
    user && ([user.name, user.last_name].filter(Boolean).join(" ") || user.email || user.id);

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        {!onLogin ? (
          <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
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
                  title={label}
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-muted font-medium text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                  )}
                >
                  <Icon className="size-4 shrink-0" stroke={1.75} />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>
        ) : (
          <div />
        )}
        {!onLogin && !loading && status?.authenticated && user && (
          <div className="flex shrink-0 items-center gap-2 border-l border-border pl-3">
            {user.photo ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.photo}
                alt=""
                className="size-7 rounded-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : (
              <span
                aria-hidden
                className="inline-flex size-7 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-muted-foreground"
              >
                {(displayName || "?").slice(0, 1).toUpperCase()}
              </span>
            )}
            <span className="max-w-[10rem] truncate text-xs text-muted-foreground">{displayName}</span>
            {status.auth_enabled && (
              <button
                type="button"
                onClick={() => void logout()}
                className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "gap-1")}
              >
                <IconLogout className="size-4" stroke={1.75} />
                Выйти
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
