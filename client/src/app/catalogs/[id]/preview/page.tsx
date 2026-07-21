"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { IconDownload } from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function CatalogPreviewPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const { data, error, isLoading } = useQuery({
    queryKey: ["preview", id],
    queryFn: () => api.preview(id),
    retry: false,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        backHref={`/catalogs/${id}`}
        backLabel="Настройки каталога"
        title="Превью каталога"
        description={
          data ? `${data.page_count} страниц` : "После успешной сборки здесь появятся страницы"
        }
        actions={
          <a
            href={api.downloadUrl(id)}
            className={cn(buttonVariants())}
          >
            <IconDownload className="size-4" stroke={1.75} />
            Скачать PDF
          </a>
        }
      />

      {isLoading && <p className="text-muted-foreground">Загрузка…</p>}
      {error && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Превью ещё нет. Соберите каталог на странице настроек.
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {data?.pages.map((page, idx) => (
          <Card key={page}>
            <CardHeader className="border-b pb-4">
              <CardTitle className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                Страница {idx + 1}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={api.assetUrl(page)} alt={`page-${idx + 1}`} className="w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
