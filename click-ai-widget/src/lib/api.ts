const API_BASE = import.meta.env.VITE_API_BASE || "";

function getToken(): string | null {
  return localStorage.getItem("isdelal_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Auth
export const auth = {
  google: (credential: string) =>
    request<{ access_token: string; user: any }>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ credential }),
    }),
  me: () => request<any>("/auth/me"),
};

// Sites
export const sites = {
  list: () => request<any[]>("/api/sites"),
  get: (id: number) => request<any>(`/api/sites/${id}`),
  create: (url: string) => request<any>("/api/sites", { method: "POST", body: JSON.stringify({ url }) }),
  updateWidget: (id: number, config: Record<string, string>) =>
    request<any>(`/api/sites/${id}/widget`, { method: "PUT", body: JSON.stringify(config) }),
  delete: (id: number) => request<any>(`/api/sites/${id}`, { method: "DELETE" }),
};

// Stats
export const stats = {
  user: () => request<any>("/api/user/stats"),
};

// Tariffs
export const tariffs = {
  list: () => request<any[]>("/api/tariffs"),
  mySubscription: () => request<any>("/api/user/subscription"),
};

// Telegram bot (public)
export const bot = {
  info: () => request<{ enabled: boolean; username: string | null }>("/api/bot/info"),
};

// Payments
export const payments = {
  list: () => request<any[]>("/api/user/payments"),
  yookassa: (tariff_name: string) =>
    request<{ confirmation_url: string; payment_id: number }>("/api/payments/yookassa", {
      method: "POST",
      body: JSON.stringify({ tariff_name }),
    }),
};

// Ingest
export const ingest = {
  start: (url: string, collection: string) =>
    request<any>("/ingest", { method: "POST", body: JSON.stringify({ url, collection }) }),
  status: (jobId: string) => request<any>(`/ingest/status/${jobId}`),
};

// Collections
export const collections = {
  list: () => request<{ collections: { name: string }[] }>("/collections"),
  get: (name: string) => request<any>(`/collections/${name}`),
};

// Documents (client files indexed into a site's knowledge base)
export interface SiteDocument {
  id: number;
  site_id: number;
  name: string;
  source_type: "pdf" | "xlsx" | "google_doc" | "google_sheet";
  source_url: string | null;
  file_name: string | null;
  status: "processing" | "completed" | "failed";
  error: string | null;
  chunk_count: number;
  created_at: string;
}

/** POST multipart/form-data (document endpoints accept `file` or `url` fields). */
async function sendForm<T>(path: string, formData: FormData): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  // No Content-Type here — the browser sets the multipart boundary itself.
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", headers, body: formData });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const documents = {
  list: (siteId: number) => request<SiteDocument[]>(`/api/sites/${siteId}/documents`),
  upload: (siteId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return sendForm<SiteDocument>(`/api/sites/${siteId}/documents`, fd);
  },
  addUrl: (siteId: number, url: string) => {
    const fd = new FormData();
    fd.append("url", url);
    return sendForm<SiteDocument>(`/api/sites/${siteId}/documents`, fd);
  },
  delete: (siteId: number, documentId: number) =>
    request<{ status: string; chunks_removed: number }>(
      `/api/sites/${siteId}/documents/${documentId}`,
      { method: "DELETE" },
    ),
};
