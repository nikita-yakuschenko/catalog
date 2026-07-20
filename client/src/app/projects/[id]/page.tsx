"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";

const ASSET_TYPES = [
  "exterior",
  "floor_plan",
  "facade",
  "section",
  "interior",
  "detail",
  "decorative",
  "unknown",
];

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: () => api.project(id),
  });

  const updateAsset = useMutation({
    mutationFn: ({ assetId, body }: { assetId: string; body: Record<string, unknown> }) =>
      api.updateAsset(assetId, body),
    onSuccess: () => {
      toast.success("Ассет обновлён");
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateProject = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.updateProject(id, body),
    onSuccess: () => {
      toast.success("Проект сохранён");
      qc.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading || !data) {
    return <p className="text-[#737373]">Загрузка…</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs tracking-[0.16em] text-[#48B062] uppercase">{data.category}</p>
        <h1 className="mt-2 text-3xl font-semibold">{data.short_name}</h1>
        <a href={data.project_url} target="_blank" className="mt-2 inline-block text-sm text-[#737373] underline">
          Открыть на avgst.ru
        </a>
      </div>

      <form
        className="grid gap-4 rounded-lg border border-[#D9D9D4] bg-white p-5 md:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          updateProject.mutate({
            short_name: String(fd.get("short_name") || ""),
            area: fd.get("area") ? Number(fd.get("area")) : null,
            bedrooms: fd.get("bedrooms") ? Number(fd.get("bedrooms")) : null,
            bathrooms: String(fd.get("bathrooms") || "") || null,
            dimensions_display: String(fd.get("dimensions_display") || "") || null,
            price: fd.get("price") ? Number(fd.get("price")) : null,
          });
        }}
      >
        {(
          [
            ["short_name", "Название", data.short_name],
            ["area", "Площадь", data.area ?? ""],
            ["dimensions_display", "Габариты", data.dimensions_display ?? ""],
            ["bedrooms", "Спальни", data.bedrooms ?? ""],
            ["bathrooms", "Санузлы", data.bathrooms ?? ""],
            ["price", "Цена", data.price ?? ""],
          ] as const
        ).map(([name, label, value]) => (
          <label key={name} className="text-sm">
            <span className="mb-1 block text-xs uppercase tracking-wide text-[#737373]">{label}</span>
            <input
              name={name}
              defaultValue={String(value)}
              className="w-full rounded-md border border-[#D9D9D4] px-3 py-2"
            />
          </label>
        ))}
        <div className="md:col-span-3">
          <button type="submit" className="rounded-md bg-[#111] px-4 py-2 text-sm text-white">
            Сохранить характеристики
          </button>
        </div>
      </form>

      <div className="space-y-3">
        <h2 className="text-xl font-semibold">Изображения</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {data.assets.map((asset) => (
            <div key={asset.id} className="rounded-lg border border-[#D9D9D4] bg-white p-4">
              <div className="mb-3 aspect-video overflow-hidden bg-[#F2F2EF]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={asset.source_url} alt="" className="h-full w-full object-contain" />
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <select
                  value={asset.type}
                  onChange={(e) =>
                    updateAsset.mutate({ assetId: asset.id, body: { type: e.target.value } })
                  }
                  className="rounded-md border border-[#D9D9D4] px-2 py-1"
                >
                  {ASSET_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <button
                  className="rounded-md border border-[#D9D9D4] px-2 py-1"
                  onClick={() =>
                    updateAsset.mutate({ assetId: asset.id, body: { is_primary: true } })
                  }
                >
                  {asset.is_primary ? "Главный" : "Сделать главным"}
                </button>
                <button
                  className="rounded-md border border-[#D9D9D4] px-2 py-1"
                  onClick={() =>
                    updateAsset.mutate({
                      assetId: asset.id,
                      body: { excluded: !asset.excluded },
                    })
                  }
                >
                  {asset.excluded ? "Вернуть" : "Исключить"}
                </button>
                <span className="text-[#737373]">
                  {asset.width}×{asset.height} · {asset.quality_status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
