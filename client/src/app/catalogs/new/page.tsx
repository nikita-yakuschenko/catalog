"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { api, Project } from "@/lib/api";

export default function NewCatalogPage() {
  const router = useRouter();
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => api.projects() });
  const [name, setName] = useState("AVGST — 20 проектов");
  const [title, setTitle] = useState("20 проектов домов");
  const [subtitle, setSubtitle] = useState("Модульные и панельно-каркасные дома");
  const [showPrices, setShowPrices] = useState(true);
  const [selected, setSelected] = useState<string[]>([]);

  const modular = useMemo(() => projects.filter((p) => p.technology === "modular"), [projects]);
  const panel = useMemo(() => projects.filter((p) => p.technology === "panel"), [projects]);

  const create = useMutation({
    mutationFn: () =>
      api.createCatalog({
        name,
        title,
        subtitle,
        show_prices: showPrices,
        price_actual_at: new Date().toISOString().slice(0, 10),
        project_ids: selected,
        contacts: { site: "avgst.ru" },
      }),
    onSuccess: (catalog) => {
      toast.success("Каталог создан");
      router.push(`/catalogs/${catalog.id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function pickFirst(list: Project[], n: number) {
    const ids = list.slice(0, n).map((p) => p.id);
    setSelected((prev) => Array.from(new Set([...prev.filter((id) => !list.some((p) => p.id === id)), ...ids])));
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Новый каталог</h1>

      <div className="grid gap-4 rounded-lg border border-[#D9D9D4] bg-white p-5 md:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block text-xs uppercase tracking-wide text-[#737373]">Название</span>
          <input className="w-full rounded-md border border-[#D9D9D4] px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs uppercase tracking-wide text-[#737373]">Заголовок</span>
          <input className="w-full rounded-md border border-[#D9D9D4] px-3 py-2" value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="text-sm md:col-span-2">
          <span className="mb-1 block text-xs uppercase tracking-wide text-[#737373]">Подзаголовок</span>
          <input className="w-full rounded-md border border-[#D9D9D4] px-3 py-2" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showPrices} onChange={(e) => setShowPrices(e.target.checked)} />
          Показывать цены
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button onClick={() => pickFirst(modular, 10)} className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm">
          10 модульных
        </button>
        <button onClick={() => pickFirst(panel, 10)} className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm">
          10 панельно-каркасных
        </button>
        <button
          onClick={() => {
            const ids = [...modular.slice(0, 10), ...panel.slice(0, 10)].map((p) => p.id);
            setSelected(ids);
          }}
          className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm"
        >
          Как в примере (10+10)
        </button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {[
          ["Модульные", modular],
          ["Панельно-каркасные", panel],
        ].map(([label, list]) => (
          <div key={label as string} className="rounded-lg border border-[#D9D9D4] bg-white p-4">
            <h2 className="mb-3 font-semibold">{label as string}</h2>
            <div className="max-h-[420px] space-y-2 overflow-auto">
              {(list as Project[]).map((p) => (
                <label key={p.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggle(p.id)} />
                  <span>
                    {p.short_name}
                    {p.area ? ` · ${p.area} м²` : ""}
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        disabled={create.isPending || selected.length === 0}
        onClick={() => create.mutate()}
        className="rounded-md bg-[#48B062] px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
      >
        Создать каталог ({selected.length})
      </button>
    </div>
  );
}
