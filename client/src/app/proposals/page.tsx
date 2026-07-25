"use client";

import { useQuery } from "@tanstack/react-query";
import { IconDownload, IconRefresh } from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { StickyChrome } from "@/components/sticky-chrome";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, type ProposalListItem } from "@/lib/api";

function formatPrice(value: number | null) {
  if (value == null) return "—";
  return new Intl.NumberFormat("ru-RU").format(value) + " руб.";
}

function formatDate(value: string) {
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

function statusLabel(row: ProposalListItem) {
  if (row.status === "ready" && row.has_pdf) return { text: "Готово", variant: "default" as const };
  if (row.status === "failed" || row.build_status === "failed")
    return { text: "Ошибка", variant: "destructive" as const };
  if (row.status === "building" || row.build_status === "running" || row.build_status === "pending")
    return { text: "Сборка", variant: "secondary" as const };
  return { text: row.status || "—", variant: "outline" as const };
}

export default function ProposalsPage() {
  const query = useQuery({
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

  const rows = query.data || [];

  return (
    <div className="space-y-6">
      <StickyChrome>
        <PageHeader
          eyebrow="Bitrix24"
          title="Коммерческие предложения"
          description="Собранные КП по сделкам. Если файл не попал обратно в смарт-процесс — скачайте здесь."
          actions={
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <IconRefresh className="size-4" stroke={1.75} />
              Обновить
            </Button>
          }
        />
      </StickyChrome>

      <div className="rounded-xl border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Дата</TableHead>
              <TableHead>КП / Bitrix</TableHead>
              <TableHead>Проект</TableHead>
              <TableHead>Клиент</TableHead>
              <TableHead>Менеджер</TableHead>
              <TableHead>Сумма</TableHead>
              <TableHead>Статус</TableHead>
              <TableHead className="text-right">PDF</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {query.isLoading && (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                  Загрузка…
                </TableCell>
              </TableRow>
            )}
            {!query.isLoading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                  Пока нет коммерческих предложений. Создайте элемент в Bitrix — он появится здесь.
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => {
              const st = statusLabel(row);
              return (
                <TableRow key={row.id}>
                  <TableCell className="text-muted-foreground">{formatDate(row.created_at)}</TableCell>
                  <TableCell className="font-medium">
                    {row.external_id ? `#${row.external_id}` : row.id.slice(0, 8)}
                  </TableCell>
                  <TableCell>{row.project_name || "—"}</TableCell>
                  <TableCell>{row.client_name || "—"}</TableCell>
                  <TableCell>{row.manager_name || "—"}</TableCell>
                  <TableCell>{formatPrice(row.grand_total)}</TableCell>
                  <TableCell>
                    <Badge variant={st.variant}>{st.text}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {row.has_pdf ? (
                      <a
                        href={api.proposalDownloadUrl(row.id)}
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-brand)] hover:underline"
                      >
                        <IconDownload className="size-4" stroke={1.75} />
                        Скачать
                      </a>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
