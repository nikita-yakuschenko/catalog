"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { IconEye, IconPlus, IconTrash } from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { StickyChrome } from "@/components/sticky-chrome";
import { useAuth } from "@/components/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { catalogStatusLabel } from "@/lib/catalog-labels";
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

      <div className="grid gap-4">
        {isLoading && <p className="text-muted-foreground">Загрузка…</p>}
        {!isLoading && data.length === 0 && (
          <p className="text-muted-foreground">Каталогов пока нет.</p>
        )}
        {data.map((c) => (
          <Card key={c.id}>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 p-6">
              <div className="space-y-1">
                <Link href={`/catalogs/${c.id}`} className="text-lg font-semibold hover:text-primary">
                  {c.name}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {c.title} · {c.projects?.length || 0} проектов
                </p>
                <Badge variant="secondary">{catalogStatusLabel(c.status, isAdmin)}</Badge>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  href={`/catalogs/${c.id}/preview`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  <IconEye className="size-4" stroke={1.75} />
                  Превью
                </Link>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setPendingDelete({ id: c.id, name: c.name })}
                  disabled={remove.isPending}
                >
                  <IconTrash className="size-4" stroke={1.75} />
                  Удалить
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
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
