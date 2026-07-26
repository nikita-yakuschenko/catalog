import type { Project } from "@/lib/api";

export type CatalogPreset = {
  id: string;
  /** Короткий ярлык в UI */
  label: string;
  /** Полное название каталога */
  name: string;
  title: string;
  subtitle: string;
  match: (p: Project) => boolean;
};

function hasArea(p: Project): p is Project & { area: number } {
  return typeof p.area === "number" && Number.isFinite(p.area);
}

function isBarnhouse(p: Project): boolean {
  const hay = `${p.name} ${p.short_name} ${p.category}`.toLowerCase();
  return hay.includes("барнхаус") || hay.includes("barnhouse") || hay.includes("barn haus");
}

export const CATALOG_PRESETS: CatalogPreset[] = [
  {
    id: "modular",
    label: "Модульные",
    name: "Подборка модульных домов",
    title: "Модульные дома",
    subtitle: "Проекты заводской готовности",
    match: (p) => p.technology === "modular",
  },
  {
    id: "panel",
    label: "Панельно-каркасные",
    name: "Подборка панельно-каркасных домов",
    title: "Панельно-каркасные дома",
    subtitle: "Проекты для постоянного проживания",
    match: (p) => p.technology === "panel",
  },
  {
    id: "floors-1",
    label: "Одноэтажные",
    name: "Подборка одноэтажных домов",
    title: "Одноэтажные дома",
    subtitle: "Проекты в один этаж",
    match: (p) => p.floors === 1,
  },
  {
    id: "floors-2",
    label: "Двухэтажные",
    name: "Подборка двухэтажных домов",
    title: "Двухэтажные дома",
    subtitle: "Проекты в два этажа",
    match: (p) => p.floors === 2,
  },
  {
    id: "barnhouse",
    label: "Барнхаус",
    name: "Подборка домов в стиле Барнхаус",
    title: "Дома в стиле Барнхаус",
    subtitle: "Подборка проектов барнообразного стиля",
    match: isBarnhouse,
  },
  {
    id: "area-lt-80",
    label: "до 80 м²",
    name: "Подборка домов до 80 м²",
    title: "Дома до 80 м²",
    subtitle: "Компактные проекты",
    match: (p) => hasArea(p) && p.area < 80,
  },
  {
    id: "area-80-100",
    label: "80–100 м²",
    name: "Подборка домов 80 м² – 100 м²",
    title: "Дома 80–100 м²",
    subtitle: "Проекты площадью от 80 до 100 м²",
    match: (p) => hasArea(p) && p.area >= 80 && p.area < 100,
  },
  {
    id: "area-100-120",
    label: "100–120 м²",
    name: "Подборка домов 100 м² – 120 м²",
    title: "Дома 100–120 м²",
    subtitle: "Проекты площадью от 100 до 120 м²",
    match: (p) => hasArea(p) && p.area >= 100 && p.area < 120,
  },
  {
    id: "area-120-150",
    label: "120–150 м²",
    name: "Подборка домов 120 м² – 150 м²",
    title: "Дома 120–150 м²",
    subtitle: "Проекты площадью от 120 до 150 м²",
    match: (p) => hasArea(p) && p.area >= 120 && p.area < 150,
  },
  {
    id: "area-150-200",
    label: "150–200 м²",
    name: "Подборка домов 150 м² – 200 м²",
    title: "Дома 150–200 м²",
    subtitle: "Проекты площадью от 150 до 200 м²",
    match: (p) => hasArea(p) && p.area >= 150 && p.area < 200,
  },
  {
    id: "area-gt-200",
    label: "более 200 м²",
    name: "Подборка домов более 200 м²",
    title: "Дома более 200 м²",
    subtitle: "Проекты площадью от 200 м²",
    match: (p) => hasArea(p) && p.area >= 200,
  },
];

export function applyCatalogPreset(projects: Project[], preset: CatalogPreset): string[] {
  return projects.filter(preset.match).map((p) => p.id);
}

export function catalogManagerName(catalog: {
  contacts?: { manager?: { name?: string } } | null;
}): string {
  return catalog.contacts?.manager?.name?.trim() || "—";
}

export function formatCatalogDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
}
