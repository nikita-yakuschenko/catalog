"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

function formatPrice(value: number | null) {
  if (value == null) return "—";
  return new Intl.NumberFormat("ru-RU").format(value) + " ₽";
}

export default function ProjectsPage() {
  const [technology, setTechnology] = useState<string>("");
  const [q, setQ] = useState("");
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery({
    queryKey: ["projects", technology, q],
    queryFn: () =>
      api.projects({
        technology: technology || undefined,
        q: q || undefined,
      }),
  });

  const sync = useMutation({
    mutationFn: api.sync,
    onSuccess: (res) => {
      toast.success(
        `Синхронизация: +${res.created as number} / ~${res.updated as number}. Ошибок: ${(res.errors as string[])?.length || 0}`
      );
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const counts = useMemo(() => {
    return {
      all: data.length,
      modular: data.filter((p) => p.technology === "modular").length,
      panel: data.filter((p) => p.technology === "panel").length,
    };
  }, [data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Проекты</h1>
          <p className="mt-1 text-sm text-[#737373]">
            Всего {counts.all}: модульные {counts.modular}, панельно-каркасные {counts.panel}
          </p>
        </div>
        <button
          onClick={() => sync.mutate()}
          disabled={sync.isPending}
          className="rounded-md bg-[#48B062] px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {sync.isPending ? "Синхронизация…" : "Синхронизировать с Tilda"}
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={technology}
          onChange={(e) => setTechnology(e.target.value)}
          className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm"
        >
          <option value="">Все технологии</option>
          <option value="modular">Модульные</option>
          <option value="panel">Панельно-каркасные</option>
        </select>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Поиск по названию"
          className="min-w-[240px] rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm"
        />
      </div>

      <div className="overflow-hidden rounded-lg border border-[#D9D9D4] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[#D9D9D4] bg-[#FAFAF8] text-xs uppercase tracking-wide text-[#737373]">
            <tr>
              <th className="px-4 py-3">Название</th>
              <th className="px-4 py-3">Технология</th>
              <th className="px-4 py-3">Площадь</th>
              <th className="px-4 py-3">Спальни</th>
              <th className="px-4 py-3">Цена</th>
              <th className="px-4 py-3">Ассеты</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[#737373]">
                  Загрузка…
                </td>
              </tr>
            )}
            {!isLoading && data.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[#737373]">
                  Нет проектов. Нажмите «Синхронизировать с Tilda».
                </td>
              </tr>
            )}
            {data.map((p) => (
              <tr key={p.id} className="border-t border-[#EEE]">
                <td className="px-4 py-3">
                  <Link href={`/projects/${p.id}`} className="font-medium hover:text-[#48B062]">
                    {p.short_name}
                  </Link>
                </td>
                <td className="px-4 py-3">{p.category}</td>
                <td className="px-4 py-3">{p.area ?? "—"}</td>
                <td className="px-4 py-3">{p.bedrooms ?? "—"}</td>
                <td className="px-4 py-3">{formatPrice(p.price)}</td>
                <td className="px-4 py-3">{p.assets?.length ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
