"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold">Превью каталога</h1>
          <p className="text-sm text-[#737373]">
            {data ? `${data.page_count} страниц` : "После успешной сборки здесь появятся страницы"}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={`/catalogs/${id}`} className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm">
            Назад
          </Link>
          <a href={api.downloadUrl(id)} className="rounded-md bg-[#48B062] px-3 py-2 text-sm text-white">
            Скачать PDF
          </a>
        </div>
      </div>

      {isLoading && <p className="text-[#737373]">Загрузка…</p>}
      {error && (
        <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Превью ещё нет. Соберите каталог на странице настроек.
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {data?.pages.map((page, idx) => (
          <div key={page} className="overflow-hidden rounded-lg border border-[#D9D9D4] bg-white">
            <div className="border-b border-[#EEE] px-3 py-2 text-xs uppercase tracking-wide text-[#737373]">
              Страница {idx + 1}
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={api.assetUrl(page)} alt={`page-${idx + 1}`} className="w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}
