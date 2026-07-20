"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const LAYOUTS = ["project_spread", "hero_plan_right", "split_equal"];

export default function CatalogDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const qc = useQueryClient();
  const [polling, setPolling] = useState(false);

  const { data } = useQuery({
    queryKey: ["catalog", id],
    queryFn: () => api.catalog(id),
  });

  const { data: status } = useQuery({
    queryKey: ["catalog-status", id],
    queryFn: () => api.status(id),
    refetchInterval: polling ? 2000 : false,
  });

  useEffect(() => {
    const st = status?.build?.status;
    if (st === "pending" || st === "running") setPolling(true);
    if (st === "ready" || st === "failed") {
      setPolling(false);
      qc.invalidateQueries({ queryKey: ["catalog", id] });
    }
  }, [status, id, qc]);

  const build = useMutation({
    mutationFn: () => api.build(id),
    onSuccess: () => {
      toast.message("Сборка запущена");
      setPolling(true);
      qc.invalidateQueries({ queryKey: ["catalog-status", id] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const preflight = useMutation({
    mutationFn: () => api.preflight(id),
    onSuccess: (report) => {
      toast.message(`Preflight: ${report.status as string}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateLayout = useMutation({
    mutationFn: ({ projectId, layout }: { projectId: string; layout: string }) =>
      api.updateCatalogProject(id, projectId, { layout_variant_override: layout || null }),
    onSuccess: () => {
      toast.success("Layout обновлён");
      qc.invalidateQueries({ queryKey: ["catalog", id] });
    },
  });

  if (!data) return <p className="text-[#737373]">Загрузка…</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">{data.name}</h1>
          <p className="text-sm text-[#737373]">
            {data.title} · статус {data.status}
            {status?.build ? ` · сборка ${status.build.status} (${status.build.stage})` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => preflight.mutate()} className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm">
            Preflight
          </button>
          <button
            onClick={() => build.mutate()}
            disabled={build.isPending}
            className="rounded-md bg-[#48B062] px-3 py-2 text-sm text-white"
          >
            Собрать PDF
          </button>
          <Link href={`/catalogs/${id}/preview`} className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm">
            Превью
          </Link>
          <a href={api.downloadUrl(id)} className="rounded-md border border-[#D9D9D4] bg-white px-3 py-2 text-sm">
            Скачать PDF
          </a>
        </div>
      </div>

      {status?.build?.error_message && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {status.build.error_message}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-[#D9D9D4] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[#D9D9D4] bg-[#FAFAF8] text-xs uppercase tracking-wide text-[#737373]">
            <tr>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Проект</th>
              <th className="px-4 py-3">Layout</th>
              <th className="px-4 py-3">Override</th>
            </tr>
          </thead>
          <tbody>
            {[...data.projects].sort((a, b) => a.order - b.order).map((cp, idx) => (
              <tr key={cp.id} className="border-t border-[#EEE]">
                <td className="px-4 py-3">{idx + 1}</td>
                <td className="px-4 py-3">{cp.project?.short_name || cp.project_id}</td>
                <td className="px-4 py-3">{cp.layout_variant || "—"}</td>
                <td className="px-4 py-3">
                  <select
                    value={cp.layout_variant_override || ""}
                    onChange={(e) =>
                      updateLayout.mutate({ projectId: cp.project_id, layout: e.target.value })
                    }
                    className="rounded-md border border-[#D9D9D4] px-2 py-1"
                  >
                    <option value="">Авто</option>
                    {LAYOUTS.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
