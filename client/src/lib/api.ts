const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type Technology = "modular" | "panel";

export type Project = {
  id: string;
  technology: Technology;
  category: string;
  name: string;
  short_name: string;
  area: number | null;
  dimensions_display: string | null;
  bedrooms: number | null;
  bathrooms: string | null;
  price: number | null;
  project_url: string;
  active: boolean;
  last_synced_at: string | null;
  assets: Asset[];
};

export type Asset = {
  id: string;
  type: string;
  source_url: string;
  local_path: string;
  width: number;
  height: number;
  is_primary: boolean;
  excluded: boolean;
  quality_status: string;
};

export type Catalog = {
  id: string;
  name: string;
  status: string;
  title: string;
  subtitle: string;
  year: number;
  show_prices: boolean;
  price_actual_at: string | null;
  output_profile: string;
  projects: CatalogProject[];
};

export type CatalogProject = {
  id: string;
  project_id: string;
  order: number;
  layout_variant: string | null;
  layout_variant_override: string | null;
  project?: Project;
};

export type Build = {
  id: string;
  catalog_id: string;
  status: string;
  stage: string;
  page_count: number;
  error_message: string;
  preflight_report: Record<string, unknown>;
};

export const api = {
  sync: () => request<Record<string, unknown>>("/api/sync/tilda", { method: "POST" }),
  projects: (params?: { technology?: string; q?: string }) => {
    const qs = new URLSearchParams();
    if (params?.technology) qs.set("technology", params.technology);
    if (params?.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<Project[]>(`/api/projects${suffix}`);
  },
  project: (id: string) => request<Project>(`/api/projects/${id}`),
  updateProject: (id: string, body: Partial<Project>) =>
    request<Project>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  updateAsset: (id: string, body: Partial<Asset>) =>
    request<Asset>(`/api/assets/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  catalogs: () => request<Catalog[]>("/api/catalogs"),
  catalog: (id: string) => request<Catalog>(`/api/catalogs/${id}`),
  createCatalog: (body: Record<string, unknown>) =>
    request<Catalog>("/api/catalogs", { method: "POST", body: JSON.stringify(body) }),
  updateCatalog: (id: string, body: Record<string, unknown>) =>
    request<Catalog>(`/api/catalogs/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCatalog: (id: string) => request(`/api/catalogs/${id}`, { method: "DELETE" }),
  reorder: (id: string, items: { project_id: string; order: number }[]) =>
    request<Catalog>(`/api/catalogs/${id}/projects/reorder`, {
      method: "PATCH",
      body: JSON.stringify(items),
    }),
  updateCatalogProject: (catalogId: string, projectId: string, body: Record<string, unknown>) =>
    request<Catalog>(`/api/catalogs/${catalogId}/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  preflight: (id: string) => request<Record<string, unknown>>(`/api/catalogs/${id}/preflight`, { method: "POST" }),
  build: (id: string) => request<Build>(`/api/catalogs/${id}/build`, { method: "POST" }),
  status: (id: string) =>
    request<{ catalog_status: string; build: Build | null }>(`/api/catalogs/${id}/status`),
  preview: (id: string) =>
    request<{ pages: string[]; page_count: number; build_id: string }>(`/api/catalogs/${id}/preview`),
  downloadUrl: (id: string) => `${API_URL}/api/catalogs/${id}/download`,
  assetUrl: (path: string) => (path.startsWith("http") ? path : `${API_URL}${path}`),
};
