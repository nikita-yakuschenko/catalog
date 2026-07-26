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
import { applyCatalogPreset, CATALOG_PRESETS } from "@/lib/catalog-presets";
import { api, Project } from "@/lib/api";

export default function NewCatalogPage() {
  const router = useRouter();
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: () => api.projects() });
  const [name, setName] = useState("AVGST — подборка проектов");
  const [title, setTitle] = useState("Подборка проектов");
  const [subtitle, setSubtitle] = useState("Модульные и панельно-каркасные дома");
  const [showPrices, setShowPrices] = useState(true);
  const [selected, setSelected] = useState<string[]>([]);
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const modular = useMemo(() => projects.filter((p) => p.technology === "modular"), [projects]);
  const panel = useMemo(() => projects.filter((p) => p.technology === "panel"), [projects]);

  const presetCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const preset of CATALOG_PRESETS) {
      counts[preset.id] = projects.filter(preset.match).length;
    }
    return counts;
  }, [projects]);

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
    setActivePreset(null);
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function applyPreset(presetId: string) {
    const preset = CATALOG_PRESETS.find((p) => p.id === presetId);
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

      <div className="space-y-2">
        <p className="text-sm font-medium">Быстрые отборы</p>
        <div className="flex flex-wrap gap-2">
          {CATALOG_PRESETS.map((preset) => {
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
                <span className="text-muted-foreground">· {count}</span>
              </Button>
            );
          })}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Параметры каталога</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="name">Название</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="title">Заголовок</Label>
            <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label htmlFor="subtitle">Подзаголовок</Label>
            <Input id="subtitle" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} />
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-sm md:col-span-2">
            <Checkbox checked={showPrices} onCheckedChange={(v) => setShowPrices(v === true)} />
            Показывать цены
          </label>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {[
          ["Модульные", modular],
          ["Панельно-каркасные", panel],
        ].map(([label, list]) => (
          <Card key={label as string}>
            <CardHeader>
              <CardTitle>{label as string}</CardTitle>
            </CardHeader>
            <CardContent className="max-h-[420px] space-y-2 overflow-auto">
              {(list as Project[]).map((p) => (
                <label key={p.id} className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox checked={selected.includes(p.id)} onCheckedChange={() => toggle(p.id)} />
                  <span>
                    {p.short_name}
                    {p.area ? ` · ${p.area} м²` : ""}
                    {p.floors ? ` · ${p.floors} эт.` : ""}
                  </span>
                </label>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <Button disabled={create.isPending || selected.length === 0} onClick={() => create.mutate()}>
        Создать каталог ({selected.length})
      </Button>
    </div>
  );
}
