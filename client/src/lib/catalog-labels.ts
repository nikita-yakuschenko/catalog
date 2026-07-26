/** Русские подписи статусов каталога/сборки для обычных менеджеров. */

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

export function catalogStatusLabel(status: string, isAdmin = false): string {
  if (isAdmin) return status;
  return CATALOG_STATUS_RU[status] || status;
}

export function buildStatusLabel(status: string, isAdmin = false): string {
  if (isAdmin) return status;
  return BUILD_STATUS_RU[status] || status;
}

export function catalogStatusDescription(
  catalogStatus: string,
  build?: { status: string; stage?: string | null } | null,
  isAdmin = false
): string {
  if (isAdmin) {
    const buildPart = build ? ` · сборка ${build.status}${build.stage ? ` (${build.stage})` : ""}` : "";
    return `статус ${catalogStatus}${buildPart}`;
  }
  if (build && (build.status === "pending" || build.status === "running")) {
    return buildStatusLabel(build.status, false);
  }
  return catalogStatusLabel(catalogStatus, false);
}
