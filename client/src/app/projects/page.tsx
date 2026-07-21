"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { IconExternalLink, IconFilterOff, IconRefresh } from "@tabler/icons-react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { cn } from "@/lib/utils";
import { api, Project } from "@/lib/api";

function formatPrice(value: number | null) {
  if (value == null) return "—";
  return new Intl.NumberFormat("ru-RU").format(value) + " ₽";
}

const selectClass =
  "h-8 w-full min-w-[180px] rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function bedroomLabel(value: number) {
  return value >= 5 ? "5+" : String(value);
}

function floorFilterLabel(value: number) {
  if (value >= 3) return "3+";
  return `${value} эт.`;
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="flex flex-wrap items-center gap-1.5">{children}</div>
    </div>
  );
}

function FilterChip({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant={selected ? "default" : "outline"}
      className={cn("h-8 min-w-8 px-3 font-normal", selected && "shadow-none")}
      onClick={onClick}
    >
      {children}
    </Button>
  );
}

function matchesFloors(project: Project, selected: number[]) {
  if (selected.length === 0) return true;
  const n = project.floors;
  if (n == null) return false;
  return selected.some((v) => (v >= 3 ? n >= 3 : n === v));
}

function matchesBedrooms(project: Project, selected: number[]) {
  if (selected.length === 0) return true;
  const n = project.bedrooms;
  if (n == null) return false;
  return selected.some((v) => (v >= 5 ? n >= 5 : n === v));
}

function filterProjects(
  projects: Project[],
  opts: {
    q: string;
    areaMin: string;
    areaMax: string;
    bedrooms: number[];
    bathrooms: string[];
    floors: number[];
  }
) {
  const ql = opts.q.trim().toLowerCase();
  const min = opts.areaMin.trim() ? Number(opts.areaMin) : null;
  const max = opts.areaMax.trim() ? Number(opts.areaMax) : null;

  return projects.filter((p) => {
    if (ql && !p.name.toLowerCase().includes(ql) && !p.short_name.toLowerCase().includes(ql)) {
      return false;
    }
    if (min != null && !Number.isNaN(min) && (p.area == null || p.area < min)) return false;
    if (max != null && !Number.isNaN(max) && (p.area == null || p.area > max)) return false;
    if (!matchesBedrooms(p, opts.bedrooms)) return false;
    if (!matchesFloors(p, opts.floors)) return false;
    if (opts.bathrooms.length > 0) {
      if (!p.bathrooms || !opts.bathrooms.includes(p.bathrooms)) return false;
    }
    return true;
  });
}

export default function ProjectsPage() {
  const [technology, setTechnology] = useState<string>("");
  const [q, setQ] = useState("");
  const [areaMin, setAreaMin] = useState("");
  const [areaMax, setAreaMax] = useState("");
  const [bedrooms, setBedrooms] = useState<number[]>([]);
  const [bathrooms, setBathrooms] = useState<string[]>([]);
  const [floors, setFloors] = useState<number[]>([]);
  const qc = useQueryClient();

  const { data: allProjects = [], isLoading } = useQuery({
    queryKey: ["projects", technology],
    queryFn: () =>
      api.projects({
        technology: technology || undefined,
      }),
  });

  const bedroomOptions = useMemo(() => {
    const nums = new Set<number>();
    for (const p of allProjects) {
      if (p.bedrooms != null) nums.add(p.bedrooms);
    }
    const list: number[] = [];
    for (let i = 1; i <= 4; i++) {
      if ([...nums].some((n) => n === i)) list.push(i);
    }
    if ([...nums].some((n) => n >= 5)) list.push(5);
    return list;
  }, [allProjects]);

  const floorOptions = useMemo(() => {
    const nums = new Set<number>();
    for (const p of allProjects) {
      if (p.floors != null) nums.add(p.floors);
    }
    const list: number[] = [];
    for (let i = 1; i <= 2; i++) {
      if ([...nums].some((n) => n === i)) list.push(i);
    }
    if ([...nums].some((n) => n >= 3)) list.push(3);
    return list;
  }, [allProjects]);

  const bathroomOptions = useMemo(() => {
    const set = new Set<string>();
    for (const p of allProjects) {
      if (p.bathrooms) set.add(p.bathrooms);
    }
    return [...set].sort((a, b) => a.localeCompare(b, "ru"));
  }, [allProjects]);

  const data = useMemo(
    () => filterProjects(allProjects, { q, areaMin, areaMax, bedrooms, bathrooms, floors }),
    [allProjects, q, areaMin, areaMax, bedrooms, bathrooms, floors]
  );

  const hasExtraFilters =
    areaMin !== "" ||
    areaMax !== "" ||
    bedrooms.length > 0 ||
    bathrooms.length > 0 ||
    floors.length > 0;

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

  function toggleBedroom(value: number) {
    setBedrooms((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  function toggleFloor(value: number) {
    setFloors((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  function toggleBathroom(value: string) {
    setBathrooms((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  function resetFilters() {
    setQ("");
    setAreaMin("");
    setAreaMax("");
    setBedrooms([]);
    setBathrooms([]);
    setFloors([]);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Проекты"
        description={
          <>
            Показано {counts.all} из {allProjects.length}: модульные {counts.modular}, панельно-каркасные{" "}
            {counts.panel}
          </>
        }
        actions={
          <Button onClick={() => sync.mutate()} disabled={sync.isPending}>
            <IconRefresh className={cn("size-4", sync.isPending && "animate-spin")} stroke={1.75} />
            {sync.isPending ? "Синхронизация…" : "Синхронизировать с Tilda"}
          </Button>
        }
      />

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
          <CardTitle className="text-base">Фильтры</CardTitle>
          {(hasExtraFilters || q) && (
            <Button type="button" variant="ghost" size="sm" onClick={resetFilters}>
              <IconFilterOff className="size-4" stroke={1.75} />
              Сбросить
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-x-6 gap-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="technology">Технология</Label>
              <select
                id="technology"
                value={technology}
                onChange={(e) => setTechnology(e.target.value)}
                className={selectClass}
              >
                <option value="">Все технологии</option>
                <option value="modular">Модульные</option>
                <option value="panel">Панельно-каркасные</option>
              </select>
            </div>
            <div className="min-w-[200px] flex-1 space-y-1.5">
              <Label htmlFor="search">Поиск</Label>
              <Input
                id="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="По названию"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="area-min">Площадь от, м²</Label>
              <Input
                id="area-min"
                type="number"
                min={0}
                step={0.1}
                value={areaMin}
                onChange={(e) => setAreaMin(e.target.value)}
                placeholder="мин"
                className="w-28"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="area-max">до, м²</Label>
              <Input
                id="area-max"
                type="number"
                min={0}
                step={0.1}
                value={areaMax}
                onChange={(e) => setAreaMax(e.target.value)}
                placeholder="макс"
                className="w-28"
              />
            </div>

            {floorOptions.length > 0 && (
              <FilterGroup label="Этажность">
                {floorOptions.map((n) => (
                  <FilterChip
                    key={n}
                    selected={floors.includes(n)}
                    onClick={() => toggleFloor(n)}
                  >
                    {floorFilterLabel(n)}
                  </FilterChip>
                ))}
              </FilterGroup>
            )}
            {bedroomOptions.length > 0 && (
              <FilterGroup label="Спальни">
                {bedroomOptions.map((n) => (
                  <FilterChip
                    key={n}
                    selected={bedrooms.includes(n)}
                    onClick={() => toggleBedroom(n)}
                  >
                    {bedroomLabel(n)}
                  </FilterChip>
                ))}
              </FilterGroup>
            )}
            {bathroomOptions.length > 0 && (
              <FilterGroup label="Санузлы">
                {bathroomOptions.map((value) => (
                  <FilterChip
                    key={value}
                    selected={bathrooms.includes(value)}
                    onClick={() => toggleBathroom(value)}
                  >
                    {value}
                  </FilterChip>
                ))}
              </FilterGroup>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="border-border bg-muted/50 hover:bg-muted/50">
              <TableHead className="px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Название
              </TableHead>
              <TableHead className="px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Технология
              </TableHead>
              <TableHead className="px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Площадь
              </TableHead>
              <TableHead className="px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Этажи
              </TableHead>
              <TableHead className="px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Спальни
              </TableHead>
              <TableHead className="px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Санузлы
              </TableHead>
              <TableHead className="px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Цена
              </TableHead>
              <TableHead className="px-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Ассеты
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                  Загрузка…
                </TableCell>
              </TableRow>
            )}
            {!isLoading && data.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                  {allProjects.length === 0
                    ? "Нет проектов. Нажмите «Синхронизировать с Tilda»."
                    : "Ничего не найдено. Измените фильтры."}
                </TableCell>
              </TableRow>
            )}
            {data.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="px-4 py-3">
                  <Link
                    href={`/projects/${p.id}`}
                    className="inline-flex items-center gap-1 font-medium outline-none hover:text-primary focus-visible:underline"
                  >
                    {p.short_name}
                    <IconExternalLink className="size-3.5 opacity-40" stroke={1.75} />
                  </Link>
                </TableCell>
                <TableCell className="px-4 py-3">{p.category}</TableCell>
                <TableCell className="px-4 py-3">{p.area != null ? `${p.area} м²` : "—"}</TableCell>
                <TableCell className="px-4 py-3">{p.floors ?? "—"}</TableCell>
                <TableCell className="px-4 py-3">{p.bedrooms ?? "—"}</TableCell>
                <TableCell className="px-4 py-3">{p.bathrooms ?? "—"}</TableCell>
                <TableCell className="px-4 py-3">{formatPrice(p.price)}</TableCell>
                <TableCell className="px-4 py-3 text-right">
                  <Badge
                    variant="outline"
                    className="inline-flex min-w-[2.25rem] justify-center rounded-full border-border bg-muted/40 px-2.5 py-0.5 tabular-nums font-semibold"
                  >
                    {p.assets?.length ?? 0}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
