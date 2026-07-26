"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { IconDownload, IconEye, IconLoader2, IconPlus, IconTrash } from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { StickyChrome } from "@/components/sticky-chrome";
import { useAuth } from "@/components/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { catalogStatusLabel } from "@/lib/catalog-labels";
import { catalogManagerName, formatCatalogDate } from "@/lib/catalog-presets";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

export default function CatalogsPage() {
  const { isAdmin } = useAuth();
  const qc = useQueryClient();
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["catalogs"],
    queryFn: api.catalogs,
  });

  const remove = useMutation({
    mutationFn: api.deleteCatalog,
    onSuccess: () => {
      toast.success("Каталог удалён");
      setPendingDelete(null);
      qc.invalidateQueries({ queryKey: ["catalogs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  useEffect(() => {
    if (!pendingDelete) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !remove.isPending) setPendingDelete(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pendingDelete, remove.isPending]);

  return (
    <div className="space-y-6">
      <StickyChrome>
        <PageHeader
          title="Каталоги"
          description="Созданные сборки и их статус"
          actions={
            <Link href="/catalogs/new" className={cn(buttonVariants())}>
              <IconPlus className="size-4" stroke={1.75} />
              Новый каталог
            </Link>
          }
        />
      </StickyChrome>

      <div className="rounded-xl border border-border bg-card">
        {isLoading && <p className="p-6 text-muted-foreground">Загрузка…</p>}
        {!isLoading && data.length === 0 && (
          <p className="p-6 text-muted-foreground">Каталогов пока нет.</p>
        )}
        {!isLoading && data.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Каталог</TableHead>
                <TableHead className="w-[11rem]">Менеджер</TableHead>
                <TableHead className="w-[7rem]">Создан</TableHead>
                <TableHead className="w-[9.5rem]">Статус</TableHead>
                <TableHead className="w-[20rem] text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    <Link href={`/catalogs/${c.id}`} className="font-medium hover:text-primary">
                      {c.name}
                    </Link>
                    <div className="text-sm text-muted-foreground">
                      {c.title} · {c.projects?.length || 0} проектов
                    </div>
                  </TableCell>
                  <TableCell className="w-[11rem] whitespace-nowrap">{catalogManagerName(c)}</TableCell>
                  <TableCell className="w-[7rem] whitespace-nowrap">{formatCatalogDate(c.created_at)}</TableCell>
                  <TableCell className="w-[9.5rem]">
                    <Badge
                      variant={c.status === "failed" ? "destructive" : "secondary"}
                      className={cn(
                        "gap-1.5",
                        c.status === "rendering" &&
                          "border-amber-500/40 bg-amber-500/15 text-amber-950 dark:text-amber-100"
                      )}
                    >
                      {c.status === "rendering" && (
                        <IconLoader2 className="size-3.5 animate-spin" stroke={2} />
                      )}
                      {catalogStatusLabel(c.status, isAdmin)}
                    </Badge>
                  </TableCell>
                  <TableCell className="w-[20rem]">
                    <div className="flex flex-nowrap justify-end gap-2">
                      {c.status === "ready" && (
                        <a
                          href={api.downloadUrl(c.id)}
                          className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0")}
                        >
                          <IconDownload className="size-4" stroke={1.75} />
                          Скачать
                        </a>
                      )}
                      <Link
                        href={`/catalogs/${c.id}/preview?from=list`}
                        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0")}
                      >
                        <IconEye className="size-4" stroke={1.75} />
                        Превью
                      </Link>
                      <Button
                        variant="destructive"
                        size="sm"
                        className="shrink-0"
                        onClick={() => setPendingDelete({ id: c.id, name: c.name })}
                        disabled={remove.isPending}
                      >
                        <IconTrash className="size-4" stroke={1.75} />
                        Удалить
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {pendingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="presentation"
          onClick={() => {
            if (!remove.isPending) setPendingDelete(null);
          }}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-catalog-title"
            aria-describedby="delete-catalog-desc"
            className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="delete-catalog-title" className="text-lg font-semibold">
              Удалить каталог?
            </h2>
            <p id="delete-catalog-desc" className="mt-2 text-sm text-muted-foreground">
              Каталог «{pendingDelete.name}» будет удалён безвозвратно вместе со сборками и PDF.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setPendingDelete(null)}
                disabled={remove.isPending}
              >
                Отмена
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => remove.mutate(pendingDelete.id)}
                disabled={remove.isPending}
              >
                {remove.isPending ? "Удаление…" : "Удалить"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
