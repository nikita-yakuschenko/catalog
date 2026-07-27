import type { Project } from "@/lib/api";

/** Допуск площади для быстрых отборов (м² вверх и вниз). */
export const AREA_TOLERANCE_M2 = 5;

export type PresetGroupId = "technology" | "floors" | "style" | "bedrooms" | "area";

export const PRESET_GROUP_ORDER: PresetGroupId[] = [
  "technology",
  "floors",
  "style",
  "bedrooms",
  "area",
];

export const PRESET_GROUP_LABELS: Record<PresetGroupId, string> = {
  technology: "Технология",
  floors: "Этажность",
  style: "Стиль",
  bedrooms: "Спальни",
  area: "Площадь",
};

export type CatalogPreset = {
  id: string;
  group: PresetGroupId;
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
    group: "technology",
    label: "Модульные",
    name: "Подборка модульных домов",
    title: "Модульные дома",
    subtitle: "Подборка домов, произведённых по модульной технологии",
    match: (p) => p.technology === "modular",
  },
  {
    id: "panel",
    group: "technology",
    label: "Панельно-каркасные",
    name: "Подборка панельно-каркасных домов",
    title: "Панельно-каркасные дома",
    subtitle: "Подборка домов, произведённых по панельно-каркасной технологии",
    match: (p) => p.technology === "panel",
  },
  {
    id: "floors-1",
    group: "floors",
    label: "Одноэтажные",
    name: "Подборка одноэтажных домов",
    title: "Одноэтажные дома",
    subtitle: "Подборка комфортных одноэтажных домов для жизни и отдыха",
    match: (p) => p.floors === 1,
  },
  {
    id: "floors-2",
    group: "floors",
    label: "Двухэтажные",
    name: "Подборка двухэтажных домов",
    title: "Двухэтажные дома",
    subtitle: "Подборка комфортных двухэтажных домов для жизни и отдыха",
    match: (p) => p.floors === 2,
  },
  {
    id: "barnhouse",
    group: "style",
    label: "Барнхаус",
    name: "Подборка домов в стиле Барнхаус",
    title: "Барнхаус",
    subtitle: "Подборка домов в стиле Барнхаус для жизни и отдыха",
    match: isBarnhouse,
  },
  {
    id: "bedrooms-1",
    group: "bedrooms",
    label: "1 спальня",
    name: "Подборка домов с 1 спальней",
    title: "Дома с 1 спальней",
    subtitle: "Подборка домов с одной спальней для жизни и отдыха",
    match: (p) => p.bedrooms === 1,
  },
  {
    id: "bedrooms-2",
    group: "bedrooms",
    label: "2 спальни",
    name: "Подборка домов с 2 спальнями",
    title: "Дома с 2 спальнями",
    subtitle: "Подборка домов с двумя спальнями для жизни и отдыха",
    match: (p) => p.bedrooms === 2,
  },
  {
    id: "bedrooms-3",
    group: "bedrooms",
    label: "3 спальни",
    name: "Подборка домов с 3 спальнями",
    title: "Дома с 3 спальнями",
    subtitle: "Подборка домов с тремя спальнями для жизни и отдыха",
    match: (p) => p.bedrooms === 3,
  },
  {
    id: "bedrooms-4",
    group: "bedrooms",
    label: "4 спальни",
    name: "Подборка домов с 4 спальнями",
    title: "Дома с 4 спальнями",
    subtitle: "Подборка домов с четырьмя спальнями для жизни и отдыха",
    match: (p) => p.bedrooms === 4,
  },
  {
    id: "bedrooms-5plus",
    group: "bedrooms",
    label: "5+ спален",
    name: "Подборка домов с 5 и более спальнями",
    title: "Дома с 5+ спальнями",
    subtitle: "Подборка домов с пятью и более спальнями",
    match: (p) => typeof p.bedrooms === "number" && p.bedrooms >= 5,
  },
  {
    id: "area-lt-80",
    group: "area",
    label: "до 80 м²",
    name: "Подборка домов до 80 м²",
    title: "Дома до 80 м²",
    subtitle: "Подборка компактных домов площадью до 80 м²",
    match: (p) => inAreaRange(p, null, 80),
  },
  {
    id: "area-80-100",
    group: "area",
    label: "80–100 м²",
    name: "Подборка домов 80–100 м²",
    title: "Дома 80–100 м²",
    subtitle: "Подборка домов площадью 80–100 м² для жизни и отдыха",
    match: (p) => inAreaRange(p, 80, 100),
  },
  {
    id: "area-100-120",
    group: "area",
    label: "100–120 м²",
    name: "Подборка домов 100–120 м²",
    title: "Дома 100–120 м²",
    subtitle: "Подборка домов площадью 100–120 м² для жизни и отдыха",
    match: (p) => inAreaRange(p, 100, 120),
  },
  {
    id: "area-120-150",
    group: "area",
    label: "120–150 м²",
    name: "Подборка домов 120–150 м²",
    title: "Дома 120–150 м²",
    subtitle: "Подборка просторных домов площадью 120–150 м²",
    match: (p) => inAreaRange(p, 120, 150),
  },
  {
    id: "area-150-200",
    group: "area",
    label: "150–200 м²",
    name: "Подборка домов 150–200 м²",
    title: "Дома 150–200 м²",
    subtitle: "Подборка просторных домов площадью 150–200 м²",
    match: (p) => inAreaRange(p, 150, 200),
  },
  {
    id: "area-gt-200",
    group: "area",
    label: "более 200 м²",
    name: "Подборка домов более 200 м²",
    title: "Дома более 200 м²",
    subtitle: "Подборка домов площадью более 200 м²",
    match: (p) => inAreaRange(p, 200, null),
  },
];

const PRESET_BY_ID = new Map(CATALOG_PRESETS.map((p) => [p.id, p]));

export function getCatalogPreset(id: string): CatalogPreset | undefined {
  return PRESET_BY_ID.get(id);
}

/** Пресеты сгруппированы для UI быстрых отборов. */
export function catalogPresetsByGroup(): Record<PresetGroupId, CatalogPreset[]> {
  const out: Record<PresetGroupId, CatalogPreset[]> = {
    technology: [],
    floors: [],
    style: [],
    bedrooms: [],
    area: [],
  };
  for (const preset of CATALOG_PRESETS) {
    out[preset.group].push(preset);
  }
  return out;
}

function groupActivePresetIds(activeIds: string[]): Map<PresetGroupId, string[]> {
  const grouped = new Map<PresetGroupId, string[]>();
  for (const id of activeIds) {
    const preset = PRESET_BY_ID.get(id);
    if (!preset) continue;
    const list = grouped.get(preset.group) ?? [];
    list.push(id);
    grouped.set(preset.group, list);
  }
  return grouped;
}

/**
 * Комбинированный отбор: внутри группы — ИЛИ, между группами — И.
 * Пустой activeIds → ничего не подходит.
 */
export function projectMatchesPresetSelection(p: Project, activeIds: string[]): boolean {
  if (activeIds.length === 0) return false;
  const grouped = groupActivePresetIds(activeIds);
  for (const ids of grouped.values()) {
    const presets = ids.map((id) => PRESET_BY_ID.get(id)).filter(Boolean) as CatalogPreset[];
    if (presets.length === 0) continue;
    if (!presets.some((preset) => preset.match(p))) return false;
  }
  return true;
}

export function filterProjectsByPresets(projects: Project[], activeIds: string[]): Project[] {
  if (activeIds.length === 0) return [];
  return projects.filter((p) => projectMatchesPresetSelection(p, activeIds));
}

export function applyCatalogPresets(projects: Project[], activeIds: string[]): string[] {
  return filterProjectsByPresets(projects, activeIds).map((p) => p.id);
}

/** Сколько проектов попадёт в отбор, если включить presetId (вместе с уже активными). */
export function countProjectsWithPreset(
  projects: Project[],
  activeIds: string[],
  presetId: string
): number {
  const hypothetical = activeIds.includes(presetId) ? activeIds : [...activeIds, presetId];
  return filterProjectsByPresets(projects, hypothetical).length;
}

/** Сколько новых проектов добавится при включении presetId поверх текущего выбора. */
export function countAdditionalProjectsWithPreset(
  projects: Project[],
  activeIds: string[],
  presetId: string,
  currentSelectedIds: string[]
): number {
  if (activeIds.includes(presetId)) return 0;
  const hypothetical = [...activeIds, presetId];
  const matched = new Set(applyCatalogPresets(projects, hypothetical));
  const selected = new Set(currentSelectedIds);
  let added = 0;
  for (const id of matched) {
    if (!selected.has(id)) added += 1;
  }
  return added;
}

function bedroomNumberFromPresetId(id: string): number | null {
  if (id === "bedrooms-5plus") return 5;
  const m = /^bedrooms-(\d+)$/.exec(id);
  return m ? Number(m[1]) : null;
}

function formatBedroomChip(nums: number[]): string {
  if (nums.length === 0) return "";
  const sorted = [...nums].sort((a, b) => a - b);
  const has5plus = sorted.includes(5);
  const regular = sorted.filter((n) => n < 5);

  if (regular.length >= 2) {
    const consecutive = regular.every((n, i) => i === 0 || n === regular[i - 1] + 1);
    if (consecutive) {
      const tail = has5plus ? "+5" : "";
      return `${regular[0]}–${regular[regular.length - 1]}${tail} спал.`;
    }
  }

  const parts: string[] = regular.map(String);
  if (has5plus) parts.push("5+");
  return `${parts.join(", ")} спал.`;
}

function formatBedroomTitle(nums: number[]): string {
  if (nums.length === 0) return "";
  const sorted = [...nums].sort((a, b) => a - b);
  const has5plus = sorted.includes(5);
  const regular = sorted.filter((n) => n < 5);

  if (regular.length === 1 && !has5plus) {
    const n = regular[0];
    if (n === 1) return "Дома с 1 спальней";
    return `Дома с ${n} спальнями`;
  }

  if (regular.length >= 2 && regular.every((n, i) => i === 0 || n === regular[i - 1] + 1)) {
    const range = `${regular[0]}–${regular[regular.length - 1]}`;
    if (has5plus) return `Дома с ${range} и 5+ спальнями`;
    return `Дома с ${range} спальнями`;
  }

  const parts: string[] = [];
  for (const n of regular) {
    parts.push(n === 1 ? "1 спальней" : `${n} спальнями`);
  }
  if (has5plus) parts.push("5+ спальнями");
  return `Дома с ${parts.join(", ")}`;
}

function formatAreaChip(presets: CatalogPreset[]): string {
  if (presets.length === 0) return "";
  if (presets.length === 1) return presets[0].label;
  return presets.map((p) => p.label).join(", ");
}

function formatAreaTitle(presets: CatalogPreset[]): string {
  if (presets.length === 0) return "";
  if (presets.length === 1) return presets[0].title;
  const labels = presets.map((p) => p.label).join(", ");
  return `Дома ${labels}`;
}

function formatFloorsTitle(presets: CatalogPreset[]): string {
  if (presets.length === 0) return "";
  if (presets.length === 1) return presets[0].title;
  return "Одно- и двухэтажные дома";
}

function formatTechnologyTitle(presets: CatalogPreset[]): string {
  if (presets.length === 0) return "";
  if (presets.length === 1) return presets[0].title;
  return "Модульные и панельно-каркасные дома";
}

/** Человекочитаемое описание активных отборов для подсказки в UI. */
export function formatPresetSelectionSummary(activeIds: string[]): string {
  if (activeIds.length === 0) return "";
  const grouped = groupActivePresetIds(activeIds);
  const parts: string[] = [];

  const tech = (grouped.get("technology") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  if (tech.length === 1) parts.push(tech[0].label);
  else if (tech.length > 1) parts.push("Модульные + панельно-каркасные");

  const floors = (grouped.get("floors") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  if (floors.length === 1) parts.push(floors[0].label);
  else if (floors.length > 1) parts.push("1–2 этажа");

  const style = (grouped.get("style") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  for (const p of style) parts.push(p.label);

  const bedroomIds = grouped.get("bedrooms") ?? [];
  const bedroomNums = bedroomIds
    .map(bedroomNumberFromPresetId)
    .filter((n): n is number => n != null);
  const bedroomChip = formatBedroomChip(bedroomNums);
  if (bedroomChip) parts.push(bedroomChip);

  const area = (grouped.get("area") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  const areaChip = formatAreaChip(area);
  if (areaChip) parts.push(areaChip);

  return parts.join(" · ");
}

export type CatalogPresetMeta = {
  name: string;
  title: string;
  subtitle: string;
};

/** Метаданные каталога из комбинации активных отборов. */
export function buildCatalogMetaFromPresets(activeIds: string[]): CatalogPresetMeta {
  if (activeIds.length === 0) {
    return { name: "", title: "", subtitle: "" };
  }

  const grouped = groupActivePresetIds(activeIds);
  const titleParts: string[] = [];

  const style = (grouped.get("style") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  for (const p of style) titleParts.push(p.title);

  const tech = (grouped.get("technology") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  const techTitle = formatTechnologyTitle(tech);
  if (techTitle) titleParts.push(techTitle);

  const floors = (grouped.get("floors") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  const floorsTitle = formatFloorsTitle(floors);
  if (floorsTitle) titleParts.push(floorsTitle);

  const bedroomIds = grouped.get("bedrooms") ?? [];
  const bedroomNums = bedroomIds
    .map(bedroomNumberFromPresetId)
    .filter((n): n is number => n != null);
  const bedroomTitle = formatBedroomTitle(bedroomNums);
  if (bedroomTitle) titleParts.push(bedroomTitle);

  const area = (grouped.get("area") ?? [])
    .map((id) => PRESET_BY_ID.get(id))
    .filter(Boolean) as CatalogPreset[];
  const areaTitle = formatAreaTitle(area);
  if (areaTitle) titleParts.push(areaTitle);

  const title = titleParts.join(" · ");
  const summary = formatPresetSelectionSummary(activeIds);
  const name = summary ? `Подборка: ${summary}` : "Подборка проектов";
  const subtitle = summary
    ? `Подборка домов: ${summary.replace(/ · /g, ", ")}`
    : "Подборка проектов для жизни и отдыха";

  return { name, title, subtitle };
}

/** @deprecated Используйте applyCatalogPresets */
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
