"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { StickyChrome } from "@/components/sticky-chrome";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  applyCatalogPreset,
  CATALOG_PRESET_GROUPS,
  CATALOG_PRESETS,
} from "@/lib/catalog-presets";
import { api, type Project } from "@/lib/api";
import { cn } from "@/lib/utils";

function techLabel(tech: Project["technology"]) {
  return tech === "modular" ? "Модульный" : "Панельно-каркасный";
}

function sortProjects(list: Project[]) {
  return [...list].sort((a, b) => {
    if (a.technology !== b.technology) return a.technology === "modular" ? -1 : 1;
    return (a.short_name || a.name).localeCompare(b.short_name || b.name, "ru");
  });
}

export default function NewCatalogPage() {
  const router = useRouter();
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => api.projects() });
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [showPrices, setShowPrices] = useState(true);
  const [selected, setSelected] = useState<string[]>([]);
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const sorted = useMemo(() => sortProjects(projects), [projects]);

  const presetById = useMemo(() => {
    const map = new Map(CATALOG_PRESETS.map((p) => [p.id, p]));
    return map;
  }, []);

  const presetCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const preset of CATALOG_PRESETS) {
      counts[preset.id] = projects.filter(preset.match).length;
    }
    return counts;
  }, [projects]);

  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const allIds = useMemo(() => sorted.map((p) => p.id), [sorted]);
  const allSelected = allIds.length > 0 && allIds.every((id) => selectedSet.has(id));

  const create = useMutation({
    mutationFn: async () => {
      const catalog = await api.createCatalog({
        name,
        title,
        subtitle,
        show_prices: showPrices,
        price_actual_at: new Date().toISOString().slice(0, 10),
        project_ids: selected,
        contacts: { site: "avgst.ru" },
      });
      let buildStarted = true;
      try {
        await api.build(catalog.id);
      } catch {
        buildStarted = false;
      }
      return { catalog, buildStarted };
    },
    onSuccess: ({ catalog, buildStarted }) => {
      if (buildStarted) {
        toast.success("Каталог создан, сборка PDF запущена");
      } else {
        toast.message("Каталог создан — запустите сборку PDF вручную");
      }
      router.push(`/catalogs/${catalog.id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function toggle(id: string) {
    setActivePreset(null);
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function toggleAll() {
    setActivePreset(null);
    setSelected(allSelected ? [] : allIds);
  }

  function applyPreset(presetId: string) {
    const preset = presetById.get(presetId);
    if (!preset) return;
    const ids = applyCatalogPreset(projects, preset);
    setActivePreset(preset.id);
    setSelected(ids);
    setName(preset.name);
    setTitle(preset.title);
    setSubtitle(preset.subtitle);
    if (ids.length === 0) {
      toast.message("По этому отбору пока нет проектов");
    }
  }

  return (
    <div className="space-y-6">
      <StickyChrome>
        <PageHeader backHref="/catalogs" backLabel="К списку каталогов" title="Новый каталог" />
      </StickyChrome>

      <div className="space-y-4">
        <p className="text-sm font-medium">Быстрые отборы</p>
        {CATALOG_PRESET_GROUPS.map((group) => (
          <div key={group.id} className="space-y-1.5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {group.label}
            </p>
            <div className="flex flex-wrap gap-2">
              {group.presetIds.map((id) => {
                const preset = presetById.get(id);
                if (!preset) return null;
                const count = presetCounts[preset.id] ?? 0;
                return (
                  <Button
                    key={preset.id}
                    type="button"
                    variant={activePreset === preset.id ? "default" : "outline"}
                    size="sm"
                    title={preset.name}
                    onClick={() => applyPreset(preset.id)}
                  >
                    {preset.label}
                    <span
                      className={cn(
                        activePreset === preset.id ? "text-primary-foreground/80" : "text-muted-foreground"
                      )}
                    >
                      · {count}
                    </span>
                  </Button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Параметры каталога</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="name">Название в списке</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="title">Заголовок на обложке</Label>
            <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label htmlFor="subtitle">Подзаголовок на обложке</Label>
            <Input id="subtitle" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} />
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-sm md:col-span-2">
            <Checkbox checked={showPrices} onCheckedChange={(v) => setShowPrices(v === true)} />
            Показывать цены
          </label>
        </CardContent>
      </Card>

      <div className="rounded-xl border border-border bg-card">
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold tracking-tight">Проекты</h2>
            <p className="text-xs text-muted-foreground">
              Выбрано {selected.length} из {sorted.length}
            </p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={toggleAll} disabled={sorted.length === 0}>
            {allSelected ? "Снять все" : "Выбрать все"}
          </Button>
        </div>
        <div className="max-h-[520px] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-card">
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-12">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={() => toggleAll()}
                    aria-label="Выбрать все проекты"
                  />
                </TableHead>
                <TableHead>Проект</TableHead>
                <TableHead>Технология</TableHead>
                <TableHead className="text-right">Площадь</TableHead>
                <TableHead className="text-right">Этажи</TableHead>
                <TableHead className="text-right">Спальни</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    Нет проектов — сначала синхронизируйте с avgst.ru
                  </TableCell>
                </TableRow>
              )}
              {sorted.map((p) => {
                const checked = selectedSet.has(p.id);
                return (
                  <TableRow
                    key={p.id}
                    className={cn("cursor-pointer", checked && "bg-muted/40")}
                    onClick={() => toggle(p.id)}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox checked={checked} onCheckedChange={() => toggle(p.id)} />
                    </TableCell>
                    <TableCell className="font-medium">{p.short_name || p.name}</TableCell>
                    <TableCell className="text-muted-foreground">{techLabel(p.technology)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {p.area != null ? `${p.area} м²` : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{p.floors ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{p.bedrooms ?? "—"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>

      <Button disabled={create.isPending || selected.length === 0} onClick={() => create.mutate()}>
        Создать каталог ({selected.length})
      </Button>
    </div>
  );
}
