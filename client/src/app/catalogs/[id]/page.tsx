"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { IconDownload, IconEye, IconPlayerPlay, IconShieldCheck } from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const LAYOUTS = ["project_spread", "hero_plan_right", "split_equal"];

const selectClass =
  "h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

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

  if (!data) return <p className="text-muted-foreground">Загрузка…</p>;

  return (
    <div className="space-y-6">
      <PageHeader
        backHref="/catalogs"
        backLabel="К списку каталогов"
        title={data.name}
        description={
          <>
            {data.title} · статус {data.status}
            {status?.build ? ` · сборка ${status.build.status} (${status.build.stage})` : ""}
          </>
        }
        actions={
          <>
            <Button type="button" variant="outline" onClick={() => preflight.mutate()}>
              <IconShieldCheck className="size-4" stroke={1.75} />
              Preflight
            </Button>
            <Button type="button" onClick={() => build.mutate()} disabled={build.isPending}>
              <IconPlayerPlay className="size-4" stroke={1.75} />
              Собрать PDF
            </Button>
            <Link
              href={`/catalogs/${id}/preview`}
              className={cn(buttonVariants({ variant: "outline", size: "default" }))}
            >
              <IconEye className="size-4" stroke={1.75} />
              Превью
            </Link>
            <a
              href={api.downloadUrl(id)}
              className={cn(buttonVariants({ variant: "outline", size: "default" }))}
            >
              <IconDownload className="size-4" stroke={1.75} />
              Скачать PDF
            </a>
          </>
        }
      />

      {status?.build?.error_message && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {status.build.error_message}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>Проект</TableHead>
              <TableHead>Layout</TableHead>
              <TableHead>Override</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {[...data.projects].sort((a, b) => a.order - b.order).map((cp, idx) => (
              <TableRow key={cp.id}>
                <TableCell>{idx + 1}</TableCell>
                <TableCell>{cp.project?.short_name || cp.project_id}</TableCell>
                <TableCell>{cp.layout_variant || "—"}</TableCell>
                <TableCell>
                  <select
                    value={cp.layout_variant_override || ""}
                    onChange={(e) =>
                      updateLayout.mutate({ projectId: cp.project_id, layout: e.target.value })
                    }
                    className={selectClass}
                  >
                    <option value="">Авто</option>
                    {LAYOUTS.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </select>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
