import type { Project } from "@/lib/api";

/** Допуск площади для быстрых отборов (м² вверх и вниз). */
export const AREA_TOLERANCE_M2 = 5;

export type CatalogPreset = {
  id: string;
  /** Короткий ярлык в UI */
  label: string;
  /** Название в списке каталогов (для менеджера) */
  name: string;
  /** Крупный заголовок на обложке PDF */
  title: string;
  /** Короткая строка под заголовком на обложке */
  subtitle: string;
  match: (p: Project) => boolean;
};

function hasArea(p: Project): p is Project & { area: number } {
  return typeof p.area === "number" && Number.isFinite(p.area);
}

function inAreaRange(p: Project, min: number | null, max: number | null): boolean {
  if (!hasArea(p)) return false;
  // Открытые края («до N» / «более N») — жёсткий порог без допуска
  const openLow = min == null;
  const openHigh = max == null;
  const lo = openLow ? null : openHigh ? min : min! - AREA_TOLERANCE_M2;
  const hi = openHigh ? null : openLow ? max : max! + AREA_TOLERANCE_M2;
  if (lo != null && p.area < lo) return false;
  if (hi != null && p.area > hi) return false;
  return true;
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
    subtitle: "Подборка домов, произведённых по модульной технологии",
    match: (p) => p.technology === "modular",
  },
  {
    id: "panel",
    label: "Панельно-каркасные",
    name: "Подборка панельно-каркасных домов",
    title: "Панельно-каркасные дома",
    subtitle: "Подборка домов, произведённых по панельно-каркасной технологии",
    match: (p) => p.technology === "panel",
  },
  {
    id: "floors-1",
    label: "Одноэтажные",
    name: "Подборка одноэтажных домов",
    title: "Одноэтажные дома",
    subtitle: "Подборка комфортных одноэтажных домов для жизни и отдыха",
    match: (p) => p.floors === 1,
  },
  {
    id: "floors-2",
    label: "Двухэтажные",
    name: "Подборка двухэтажных домов",
    title: "Двухэтажные дома",
    subtitle: "Подборка комфортных двухэтажных домов для жизни и отдыха",
    match: (p) => p.floors === 2,
  },
  {
    id: "barnhouse",
    label: "Барнхаус",
    name: "Подборка домов в стиле Барнхаус",
    title: "Барнхаус",
    subtitle: "Подборка домов в стиле Барнхаус для жизни и отдыха",
    match: isBarnhouse,
  },
  {
    id: "bedrooms-1",
    label: "1 спальня",
    name: "Подборка домов с 1 спальней",
    title: "Дома с 1 спальней",
    subtitle: "Подборка домов с одной спальней для жизни и отдыха",
    match: (p) => p.bedrooms === 1,
  },
  {
    id: "bedrooms-2",
    label: "2 спальни",
    name: "Подборка домов с 2 спальнями",
    title: "Дома с 2 спальнями",
    subtitle: "Подборка домов с двумя спальнями для жизни и отдыха",
    match: (p) => p.bedrooms === 2,
  },
  {
    id: "bedrooms-3",
    label: "3 спальни",
    name: "Подборка домов с 3 спальнями",
    title: "Дома с 3 спальнями",
    subtitle: "Подборка домов с тремя спальнями для жизни и отдыха",
    match: (p) => p.bedrooms === 3,
  },
  {
    id: "bedrooms-4",
    label: "4 спальни",
    name: "Подборка домов с 4 спальнями",
    title: "Дома с 4 спальнями",
    subtitle: "Подборка домов с четырьмя спальнями для жизни и отдыха",
    match: (p) => p.bedrooms === 4,
  },
  {
    id: "bedrooms-5plus",
    label: "5+ спален",
    name: "Подборка домов с 5 и более спальнями",
    title: "Дома с 5+ спальнями",
    subtitle: "Подборка домов с пятью и более спальнями",
    match: (p) => typeof p.bedrooms === "number" && p.bedrooms >= 5,
  },
  {
    id: "area-lt-80",
    label: "до 80 м²",
    name: "Подборка домов до 80 м²",
    title: "Дома до 80 м²",
    subtitle: "Подборка компактных домов площадью до 80 м²",
    match: (p) => inAreaRange(p, null, 80),
  },
  {
    id: "area-80-100",
    label: "80–100 м²",
    name: "Подборка домов 80–100 м²",
    title: "Дома 80–100 м²",
    subtitle: "Подборка домов площадью 80–100 м² для жизни и отдыха",
    match: (p) => inAreaRange(p, 80, 100),
  },
  {
    id: "area-100-120",
    label: "100–120 м²",
    name: "Подборка домов 100–120 м²",
    title: "Дома 100–120 м²",
    subtitle: "Подборка домов площадью 100–120 м² для жизни и отдыха",
    match: (p) => inAreaRange(p, 100, 120),
  },
  {
    id: "area-120-150",
    label: "120–150 м²",
    name: "Подборка домов 120–150 м²",
    title: "Дома 120–150 м²",
    subtitle: "Подборка просторных домов площадью 120–150 м²",
    match: (p) => inAreaRange(p, 120, 150),
  },
  {
    id: "area-150-200",
    label: "150–200 м²",
    name: "Подборка домов 150–200 м²",
    title: "Дома 150–200 м²",
    subtitle: "Подборка просторных домов площадью 150–200 м²",
    match: (p) => inAreaRange(p, 150, 200),
  },
  {
    id: "area-gt-200",
    label: "более 200 м²",
    name: "Подборка домов более 200 м²",
    title: "Дома более 200 м²",
    subtitle: "Подборка домов площадью более 200 м²",
    match: (p) => inAreaRange(p, 200, null),
  },
];

export function applyCatalogPreset(projects: Project[], preset: CatalogPreset): string[] {
  return projects.filter(preset.match).map((p) => p.id);
}

/** Группы быстрых отборов для UI. */
export const CATALOG_PRESET_GROUPS: { id: string; label: string; presetIds: string[] }[] = [
  {
    id: "tech",
    label: "Технология",
    presetIds: ["modular", "panel", "barnhouse"],
  },
  {
    id: "floors",
    label: "Этажность",
    presetIds: ["floors-1", "floors-2"],
  },
  {
    id: "bedrooms",
    label: "Спальни",
    presetIds: ["bedrooms-1", "bedrooms-2", "bedrooms-3", "bedrooms-4", "bedrooms-5plus"],
  },
  {
    id: "area",
    label: "Площадь",
    presetIds: [
      "area-lt-80",
      "area-80-100",
      "area-100-120",
      "area-120-150",
      "area-150-200",
      "area-gt-200",
    ],
  },
];

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
