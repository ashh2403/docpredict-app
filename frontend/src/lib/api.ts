import type {
  AnalysisDetail,
  AnalysisPage,
  HistoryQuery,
  ModelInfo,
  Stats,
  Theme,
  TokenResponse,
  User,
} from "./types";

const API_BASE = "/api";
const TOKEN_KEY = "docpredict.token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

/** Session token lives in sessionStorage: it is cleared when the browser tab session ends. */
export const tokenStore = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable: the session will last only for this page load */
    }
  },
  clear() {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();
export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

function messageFrom(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  if (status === 0) return "Cannot reach the DocPredict server. Make sure the backend is running.";
  if (status >= 500) return "The server encountered an error. Please try again.";
  return `Request failed (${status}).`;
}

async function request<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  if (auth && token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, messageFrom(0, null));
  }
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    if (response.status === 401 && auth && token) {
      tokenStore.clear();
      unauthorizedListeners.forEach((l) => l());
    }
    throw new ApiError(response.status, messageFrom(response.status, body));
  }
  return body as T;
}

const json = (data: unknown) => JSON.stringify(data);

function toQuery(params: HistoryQuery): string {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    qs.set(key, String(value));
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export const api = {
  register: (email: string, full_name: string, password: string) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: json({ email, full_name, password }) }, false),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: json({ email, password }) }, false),
  logout: () => request<{ detail: string }>("/auth/logout", { method: "POST" }),

  me: () => request<User>("/users/me"),
  updateProfile: (data: { full_name?: string; theme?: Theme }) =>
    request<User>("/users/me", { method: "PATCH", body: json(data) }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ detail: string }>("/users/me/password", { method: "POST", body: json({ current_password, new_password }) }),
  deleteAccount: (password: string) =>
    request<{ detail: string }>("/users/me", { method: "DELETE", body: json({ password }) }),

  listAnalyses: (query: HistoryQuery = {}) => request<AnalysisPage>(`/analyses${toQuery(query)}`),
  getAnalysis: (id: number) => request<AnalysisDetail>(`/analyses/${id}`),
  setBookmark: (id: number, bookmarked: boolean) =>
    request<AnalysisDetail>(`/analyses/${id}`, { method: "PATCH", body: json({ bookmarked }) }),
  deleteAnalysis: (id: number) => request<{ detail: string }>(`/analyses/${id}`, { method: "DELETE" }),
  deleteAllAnalyses: () => request<{ detail: string }>("/analyses", { method: "DELETE" }),
  stats: () => request<Stats>("/analyses/stats"),
  modelInfo: () => request<ModelInfo>("/model"),

  /** Upload with progress reporting (fetch cannot report upload progress). */
  uploadDocument(file: File, onProgress?: (fraction: number) => void, signal?: AbortSignal): Promise<AnalysisDetail> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/analyses`);
      const token = tokenStore.get();
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
      };
      xhr.onload = () => {
        let body: unknown = null;
        try {
          body = xhr.responseText ? JSON.parse(xhr.responseText) : null;
        } catch {
          body = null;
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as AnalysisDetail);
          return;
        }
        if (xhr.status === 401 && token) {
          tokenStore.clear();
          unauthorizedListeners.forEach((l) => l());
        }
        reject(new ApiError(xhr.status, messageFrom(xhr.status, body)));
      };
      xhr.onerror = () => reject(new ApiError(0, messageFrom(0, null)));
      xhr.onabort = () => reject(new ApiError(-1, "Upload cancelled."));
      signal?.addEventListener("abort", () => xhr.abort());
      const form = new FormData();
      form.append("file", file);
      xhr.send(form);
    });
  },
};
