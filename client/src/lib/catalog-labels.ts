/** Русские подписи статусов и макетов в UI. */

const CATALOG_STATUS_RU: Record<string, string> = {
  draft: "Черновик",
  rendering: "Собирается",
  ready: "Готово",
  failed: "Ошибка",
};

const BUILD_STATUS_RU: Record<string, string> = {
  pending: "В очереди",
  running: "Собирается",
  ready: "Готово",
  failed: "Ошибка",
};

/** Ключ API → подпись в интерфейсе (значение в select остаётся английским). */
export const LAYOUT_LABELS: Record<string, string> = {
  project_spread: "Стандартный разворот",
  hero_plan_right: "Фото и план справа",
  split_equal: "Две колонки",
};

export const LAYOUT_OPTIONS = Object.keys(LAYOUT_LABELS);

export function layoutLabel(key: string | null | undefined): string {
  if (!key) return "—";
  return LAYOUT_LABELS[key] || key;
}

export function catalogStatusLabel(status: string, _isAdmin = false): string {
  return CATALOG_STATUS_RU[status] || status;
}

export function buildStatusLabel(status: string, _isAdmin = false): string {
  return BUILD_STATUS_RU[status] || status;
}

export function catalogStatusDescription(
  catalogStatus: string,
  build?: { status: string; stage?: string | null } | null,
  _isAdmin = false
): string {
  if (build && (build.status === "pending" || build.status === "running")) {
    return buildStatusLabel(build.status);
  }
  return catalogStatusLabel(catalogStatus);
}

/** Идёт сборка PDF (очередь или рендер). */
export function isCatalogBuilding(
  catalogStatus: string,
  build?: { status: string } | null
): boolean {
  if (build?.status === "pending" || build?.status === "running") return true;
  return catalogStatus === "rendering";
}
