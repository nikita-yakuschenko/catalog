"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  IconBooks,
  IconDownload,
  IconFileText,
  IconFolder,
  IconLoader2,
} from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { StickyChrome } from "@/components/sticky-chrome";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { catalogStatusLabel, isCatalogBuilding } from "@/lib/catalog-labels";
import { catalogManagerName, formatCatalogDate } from "@/lib/catalog-presets";
import { api, type Catalog, type ProposalListItem } from "@/lib/api";
import { cn } from "@/lib/utils";

const RECENT_LIMIT = 6;

function formatDateTime(value: string) {
  try {
    return new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function proposalTitle(row: ProposalListItem) {
  if (row.project_name) return row.project_name;
  if (row.external_id) return `КП #${row.external_id}`;
  return "Коммерческое предложение";
}

function proposalStatus(row: ProposalListItem) {
  if (row.status === "ready" && row.has_pdf)
    return { text: "Готово", building: false, failed: false, ready: true };
  if (row.status === "failed" || row.build_status === "failed")
    return { text: "Ошибка", building: false, failed: true, ready: false };
  if (row.status === "building" || row.build_status === "running" || row.build_status === "pending")
    return { text: "Собирается", building: true, failed: false, ready: false };
  return { text: catalogStatusLabel(row.status), building: false, failed: false, ready: false };
}

function RecentSection({
  title,
  href,
  linkLabel,
  children,
  empty,
  loading,
}: {
  title: string;
  href: string;
  linkLabel: string;
  children: ReactNode;
  empty: boolean;
  loading: boolean;
}) {
  return (
    <section className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        <Link href={href} className="text-sm text-muted-foreground hover:text-foreground">
          {linkLabel}
        </Link>
      </div>
      {loading && (
        <p className="px-4 py-8 text-center text-sm text-muted-foreground">Загрузка…</p>
      )}
      {!loading && empty && (
        <p className="px-4 py-8 text-center text-sm text-muted-foreground">Пока пусто</p>
      )}
      {!loading && !empty && <ul className="divide-y divide-border">{children}</ul>}
    </section>
  );
}

export default function HomePage() {
  const proposals = useQuery({
    queryKey: ["proposals"],
    queryFn: () => api.proposals(),
    refetchInterval: (q) => {
      const rows = q.state.data || [];
      const busy = rows.some(
        (r) =>
          r.status === "building" ||
          r.build_status === "pending" ||
          r.build_status === "running"
      );
      return busy ? 4000 : false;
    },
  });

  const catalogs = useQuery({
    queryKey: ["catalogs"],
    queryFn: api.catalogs,
    refetchInterval: (q) => {
      const rows = q.state.data || [];
      return rows.some((c) => c.status === "rendering") ? 4000 : false;
    },
  });

  const recentProposals = (proposals.data || []).slice(0, RECENT_LIMIT);
  const recentCatalogs = (catalogs.data || []).slice(0, RECENT_LIMIT);

  return (
    <div className="space-y-8">
      <StickyChrome>
        <PageHeader
          title="AVGST"
          description="Генератор коммерческих предложений и конструктор каталогов и подборок"
        />
      </StickyChrome>

      <div className="flex flex-wrap gap-3">
        <Link href="/proposals" className={cn(buttonVariants({ size: "lg" }))}>
          <IconFileText className="size-4" stroke={1.75} />
          Коммерческие предложения
        </Link>
        <Link href="/catalogs/new" className={cn(buttonVariants({ variant: "outline", size: "lg" }))}>
          <IconBooks className="size-4" stroke={1.75} />
          Создать каталог
        </Link>
        <Link href="/projects" className={cn(buttonVariants({ variant: "outline", size: "lg" }))}>
          <IconFolder className="size-4" stroke={1.75} />
          Проекты
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentSection
          title="Недавние КП"
          href="/proposals"
          linkLabel="Все КП"
          loading={proposals.isLoading}
          empty={recentProposals.length === 0}
        >
          {recentProposals.map((row) => {
            const st = proposalStatus(row);
            const manager = row.manager_name?.trim() || "";
            return (
              <li key={row.id} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{proposalTitle(row)}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {row.client_name || "Без клиента"} · {formatDateTime(row.created_at)}
                  </p>
                </div>
                {manager ? (
                  <Badge variant="outline" className="max-w-[9rem] shrink-0 truncate font-normal">
                    {manager}
                  </Badge>
                ) : null}
                <Badge
                  variant={st.failed ? "destructive" : st.ready ? "success" : "secondary"}
                  className={cn(
                    "shrink-0 gap-1",
                    st.building &&
                      "border-amber-500/40 bg-amber-500/15 text-amber-950 dark:text-amber-100"
                  )}
                >
                  {st.building && <IconLoader2 className="size-3 animate-spin" stroke={2} />}
                  {st.text}
                </Badge>
                {row.has_pdf ? (
                  <a
                    href={api.proposalDownloadUrl(row.id)}
                    className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0")}
                  >
                    <IconDownload className="size-4" stroke={1.75} />
                    PDF
                  </a>
                ) : (
                  <span className="w-[4.5rem] shrink-0 text-center text-xs text-muted-foreground">—</span>
                )}
              </li>
            );
          })}
        </RecentSection>

        <RecentSection
          title="Недавние каталоги"
          href="/catalogs"
          linkLabel="Все каталоги"
          loading={catalogs.isLoading}
          empty={recentCatalogs.length === 0}
        >
          {recentCatalogs.map((c: Catalog) => {
            const building = isCatalogBuilding(c.status);
            const failed = c.status === "failed";
            const ready = c.status === "ready";
            const manager = catalogManagerName(c);
            return (
              <li key={c.id} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <Link href={`/catalogs/${c.id}`} className="block truncate text-sm font-medium hover:text-primary">
                    {c.name}
                  </Link>
                  <p className="truncate text-xs text-muted-foreground">
                    {c.title} · {formatCatalogDate(c.created_at)}
                  </p>
                </div>
                {manager !== "—" ? (
                  <Badge variant="outline" className="max-w-[9rem] shrink-0 truncate font-normal">
                    {manager}
                  </Badge>
                ) : null}
                <Badge
                  variant={failed ? "destructive" : ready ? "success" : "secondary"}
                  className={cn(
                    "shrink-0 gap-1",
                    building &&
                      "border-amber-500/40 bg-amber-500/15 text-amber-950 dark:text-amber-100"
                  )}
                >
                  {building && <IconLoader2 className="size-3 animate-spin" stroke={2} />}
                  {catalogStatusLabel(c.status)}
                </Badge>
                {ready ? (
                  <a
                    href={api.downloadUrl(c.id)}
                    className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0")}
                  >
                    <IconDownload className="size-4" stroke={1.75} />
                    PDF
                  </a>
                ) : (
                  <Link
                    href={`/catalogs/${c.id}`}
                    className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0")}
                  >
                    Открыть
                  </Link>
                )}
              </li>
            );
          })}
        </RecentSection>
      </div>
    </div>
  );
}
