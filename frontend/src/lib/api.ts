import type {
  ConquestResponse,
  Flag,
  Post,
  Profile,
  RankingResponse,
  Store,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "bc.access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface Options {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : `요청 실패 (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const api = {
  register: (nickname: string, email: string, password: string) =>
    request<Profile>("/auth/register", {
      method: "POST",
      body: { nickname, email, password },
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
    }),

  me: () => request<Profile>("/users/me", { auth: true }),

  profile: (userId: number) => request<Profile>(`/users/${userId}`),

  nearbyStores: (lat: number, lng: number, radiusM = 3000) =>
    request<Store[]>(
      `/stores?lat=${lat}&lng=${lng}&radius_m=${radiusM}&limit=100`,
      { auth: true },
    ),

  store: (id: number) => request<Store>(`/stores/${id}`),

  storeFlags: (id: number) => request<Flag[]>(`/flags/store/${id}`),

  createStore: (body: {
    name: string;
    address: string;
    lat: number;
    lng: number;
    region_sido?: string;
    category?: string;
  }) => request<Store>("/stores", { method: "POST", body, auth: true }),

  conquer: (body: {
    store_id: number;
    type: "GOLD" | "SILVER";
    lat?: number;
    lng?: number;
    evidence_type?: string;
    evidence_image_url?: string | null;
    visited_at?: string | null;
  }) =>
    request<ConquestResponse>("/flags", { method: "POST", body, auth: true }),

  myFlags: () => request<Flag[]>("/flags/me", { auth: true }),

  nationalRanking: () =>
    request<RankingResponse>("/rankings/national?limit=50", { auth: true }),

  posts: () => request<Post[]>("/posts"),

  adminDashboard: () =>
    request<{
      total_users: number;
      total_stores: number;
      total_flags: number;
      gold_ratio: number;
      flags_this_week: number;
      pending_review: number;
    }>("/admin/stats/dashboard", { auth: true }),
};
