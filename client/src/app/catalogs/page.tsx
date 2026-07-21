"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import { IconEye, IconPlus, IconTrash } from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

export default function CatalogsPage() {
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({
    queryKey: ["catalogs"],
    queryFn: api.catalogs,
  });

  const remove = useMutation({
    mutationFn: api.deleteCatalog,
    onSuccess: () => {
      toast.success("Каталог удалён");
      qc.invalidateQueries({ queryKey: ["catalogs"] });
    },
  });

  return (
    <div className="space-y-6">
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
                <Badge variant="secondary">{c.status}</Badge>
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
                  onClick={() => remove.mutate(c.id)}
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
    </div>
  );
}
