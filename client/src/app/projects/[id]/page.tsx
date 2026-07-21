"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  IconExternalLink,
  IconPhoto,
  IconStar,
  IconStarFilled,
  IconTrash,
  IconTrashOff,
} from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
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
] as const;

function qualityBadgeVariant(status: string) {
  if (status === "ok") return "secondary" as const;
  if (status === "error") return "destructive" as const;
  return "outline" as const;
}

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
    return <p className="text-muted-foreground">Загрузка…</p>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        backHref="/projects"
        backLabel="К списку проектов"
        eyebrow={data.category}
        title={data.short_name}
        description={
          <a
            href={data.project_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 hover:text-primary"
          >
            Открыть на avgst.ru
            <IconExternalLink className="size-3.5" stroke={1.75} />
          </a>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Характеристики</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 md:grid-cols-3"
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
              <div key={name} className="space-y-1.5">
                <Label htmlFor={name}>{label}</Label>
                <Input id={name} name={name} defaultValue={String(value)} />
              </div>
            ))}
            <div className="md:col-span-3">
              <Button type="submit" disabled={updateProject.isPending}>
                Сохранить характеристики
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <IconPhoto className="size-5 text-muted-foreground" stroke={1.75} />
          <h2 className="text-xl font-semibold">Изображения</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {data.assets.map((asset) => (
            <Card key={asset.id} className={cn(asset.excluded && "opacity-60")}>
              <CardContent className="space-y-3 p-4">
                <div className="relative aspect-video overflow-hidden rounded-lg border border-border bg-muted">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={asset.source_url} alt="" className="h-full w-full object-contain" />
                  <Badge
                    variant={qualityBadgeVariant(asset.quality_status)}
                    className="absolute right-2 top-2 z-10 border-border/80 bg-background/90 tabular-nums shadow-sm backdrop-blur-sm"
                  >
                    {asset.width}×{asset.height} · {asset.quality_status}
                  </Badge>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Select
                    value={asset.type}
                    onValueChange={(value) =>
                      updateAsset.mutate({ assetId: asset.id, body: { type: value } })
                    }
                  >
                    <SelectTrigger size="sm" className="h-8 w-[10.5rem] rounded-lg">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ASSET_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant={asset.is_primary ? "default" : "outline"}
                    size="sm"
                    onClick={() =>
                      updateAsset.mutate({ assetId: asset.id, body: { is_primary: true } })
                    }
                  >
                    {asset.is_primary ? (
                      <IconStarFilled className="size-4" stroke={1.75} />
                    ) : (
                      <IconStar className="size-4" stroke={1.75} />
                    )}
                    {asset.is_primary ? "Главный" : "Сделать главным"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      updateAsset.mutate({
                        assetId: asset.id,
                        body: { excluded: !asset.excluded },
                      })
                    }
                  >
                    {asset.excluded ? (
                      <IconTrashOff className="size-4" stroke={1.75} />
                    ) : (
                      <IconTrash className="size-4" stroke={1.75} />
                    )}
                    {asset.excluded ? "Вернуть" : "Исключить"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
