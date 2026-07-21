"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
      <PageHeader backHref="/catalogs" backLabel="К списку каталогов" title="Новый каталог" />

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

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={() => pickFirst(modular, 10)}>
          10 модульных
        </Button>
        <Button type="button" variant="outline" onClick={() => pickFirst(panel, 10)}>
          10 панельно-каркасных
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            const ids = [...modular.slice(0, 10), ...panel.slice(0, 10)].map((p) => p.id);
            setSelected(ids);
          }}
        >
          Как в примере (10+10)
        </Button>
      </div>

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
