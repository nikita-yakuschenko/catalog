"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
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
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Каталоги</h1>
        <Link href="/catalogs/new" className="rounded-md bg-[#48B062] px-4 py-2 text-sm text-white">
          Новый каталог
        </Link>
      </div>

      <div className="grid gap-4">
        {isLoading && <p className="text-[#737373]">Загрузка…</p>}
        {!isLoading && data.length === 0 && (
          <p className="text-[#737373]">Каталогов пока нет.</p>
        )}
        {data.map((c) => (
          <div
            key={c.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#D9D9D4] bg-white p-4"
          >
            <div>
              <Link href={`/catalogs/${c.id}`} className="text-lg font-semibold hover:text-[#48B062]">
                {c.name}
              </Link>
              <p className="text-sm text-[#737373]">
                {c.title} · {c.projects?.length || 0} проектов · статус {c.status}
              </p>
            </div>
            <div className="flex gap-2">
              <Link
                href={`/catalogs/${c.id}/preview`}
                className="rounded-md border border-[#D9D9D4] px-3 py-2 text-sm"
              >
                Превью
              </Link>
              <button
                onClick={() => remove.mutate(c.id)}
                className="rounded-md border border-[#D9D9D4] px-3 py-2 text-sm text-red-700"
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
