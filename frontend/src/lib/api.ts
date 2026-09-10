import type {
  AdminClaim,
  AppNotification,
  Comment,
  ConquestResponse,
  Flag,
  FollowCounts,
  Post,
  Profile,
  QrToken,
  RankingResponse,
  Review,
  Store,
  StoreClaim,
  WeeklyMissions,
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

  conquerByQr: (token: string) =>
    request<ConquestResponse>("/flags/qr", {
      method: "POST",
      body: { token },
      auth: true,
    }),

  exifPreview: (imageBase64: string) =>
    request<{
      captured_at: string | null;
      lat: number | null;
      lng: number | null;
      has_gps: boolean;
      trust: "HIGH" | "MEDIUM" | "LOW";
    }>("/flags/exif-preview", {
      method: "POST",
      body: { image_base64: imageBase64 },
      auth: true,
    }),

  // reviews
  reviews: (storeId: number) =>
    request<Review[]>(`/stores/${storeId}/reviews`),

  upsertReview: (storeId: number, rating: number, content?: string) =>
    request<Review>(`/stores/${storeId}/reviews`, {
      method: "POST",
      body: { rating, content: content || null },
      auth: true,
    }),

  // social
  followCounts: (userId: number) =>
    request<FollowCounts>(`/users/${userId}/follow-counts`, { auth: true }),

  follow: (userId: number) =>
    request<void>(`/users/${userId}/follow`, { method: "POST", auth: true }),

  unfollow: (userId: number) =>
    request<void>(`/users/${userId}/follow`, { method: "DELETE", auth: true }),

  report: (targetType: "FLAG" | "POST" | "COMMENT", targetId: number, reason: string) =>
    request<{ id: number }>("/reports", {
      method: "POST",
      body: { target_type: targetType, target_id: targetId, reason },
      auth: true,
    }),

  // 매장 소유권 신청 / QR (로드맵 5단계)
  createClaim: (
    storeId: number,
    body: { business_license_image_url: string; contact_phone: string },
  ) =>
    request<StoreClaim>(`/stores/${storeId}/claims`, {
      method: "POST",
      body,
      auth: true,
    }),

  myClaims: () => request<StoreClaim[]>("/me/claims", { auth: true }),

  storeQrTokens: (storeId: number) =>
    request<QrToken[]>(`/stores/${storeId}/qr-tokens`, { auth: true }),

  createQrToken: (
    storeId: number,
    body: { label?: string | null; max_uses?: number | null; expires_in_hours?: number | null },
  ) =>
    request<QrToken>(`/stores/${storeId}/qr-tokens`, {
      method: "POST",
      body,
      auth: true,
    }),

  revokeQrToken: (storeId: number, tokenId: number) =>
    request<void>(`/stores/${storeId}/qr-tokens/${tokenId}`, {
      method: "DELETE",
      auth: true,
    }),

  adminClaims: () => request<AdminClaim[]>("/admin/claims", { auth: true }),

  // 주간 미션 (로드맵 8단계)
  weeklyMissions: () =>
    request<WeeklyMissions>("/missions/weekly", { auth: true }),

  claimMission: (code: string) =>
    request<{
      code: string;
      reward_exp: number;
      exp: number;
      tier_level: number;
      tier_changed: boolean;
    }>(`/missions/${code}/claim`, { method: "POST", auth: true }),

  // 알림 (로드맵 6단계)
  notifications: (onlyUnread = false) =>
    request<AppNotification[]>(
      `/notifications?only_unread=${onlyUnread}&limit=50`,
      { auth: true },
    ),

  unreadCount: () =>
    request<{ count: number }>("/notifications/unread-count", { auth: true }),

  markNotificationsRead: (ids?: number[]) =>
    request<void>("/notifications/read", {
      method: "POST",
      body: { ids: ids ?? null },
      auth: true,
    }),

  reviewClaim: (claimId: number, approve: boolean, note?: string) =>
    request<StoreClaim>(
      `/admin/claims/${claimId}/${approve ? "approve" : "reject"}`,
      { method: "POST", body: { note: note ?? null }, auth: true },
    ),

  bulkUploadStores: (csvText: string, dryRun: boolean) =>
    request<{
      dry_run: boolean;
      total: number;
      created: number;
      skipped_duplicate: number;
      failed: number;
      rows: {
        line: number;
        name: string;
        status: "created" | "skipped" | "failed";
        detail: string | null;
        store_id: number | null;
      }[];
    }>("/admin/stores/bulk-upload", {
      method: "POST",
      body: { csv_text: csvText, dry_run: dryRun },
      auth: true,
    }),

  mergeStores: (targetId: number, sourceId: number, note?: string) =>
    request<{
      target_id: number;
      source_id: number;
      moved_flags: number;
      moved_reviews: number;
      dropped_duplicate_reviews: number;
      moved_posts: number;
      moved_claims: number;
      moved_qr_tokens: number;
      owner_inherited: boolean;
    }>(`/admin/stores/${targetId}/merge`, {
      method: "POST",
      body: { source_id: sourceId, note: note ?? null },
      auth: true,
    }),

  // rankings
  nationalRanking: () =>
    request<RankingResponse>("/rankings/national?limit=50", { auth: true }),

  friendsRanking: () =>
    request<RankingResponse>("/rankings/friends", { auth: true }),

  // 매장 검색 / 필터 (F-SEARCH)
  searchStores: (params: {
    q?: string;
    region_sido?: string;
    category?: string;
    verified_only?: boolean;
    sort?: "popular" | "rating" | "recent";
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== false) qs.set(k, String(v));
    });
    return request<{ total: number; items: Store[] }>(
      `/stores/search?${qs.toString()}`,
      { auth: true },
    );
  },

  storeFilters: () =>
    request<{ regions: string[]; categories: string[] }>("/stores/filters"),

  // board
  posts: (params?: {
    q?: string;
    storeId?: number;
    sort?: "recent" | "popular";
  }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.storeId) qs.set("store_id", String(params.storeId));
    if (params?.sort) qs.set("sort", params.sort);
    const suffix = qs.toString();
    return request<Post[]>(`/posts${suffix ? `?${suffix}` : ""}`);
  },

  post: (id: number) => request<Post>(`/posts/${id}`),

  postComments: (id: number) => request<Comment[]>(`/posts/${id}/comments`),

  createPost: (title: string, content: string, storeId?: number) =>
    request<Post>("/posts", {
      method: "POST",
      body: { title, content, store_id: storeId ?? null },
      auth: true,
    }),

  addComment: (postId: number, content: string) =>
    request<Comment>(`/posts/${postId}/comments`, {
      method: "POST",
      body: { content },
      auth: true,
    }),

  likePost: (postId: number) =>
    request<void>(`/posts/${postId}/like`, { method: "POST", auth: true }),

  adminDashboard: () =>
    request<{
      total_users: number;
      total_stores: number;
      total_flags: number;
      gold_ratio: number;
      flags_this_week: number;
      pending_review: number;
      pending_reports: number;
      pending_claims: number;
      suspended_users: number;
      average_store_rating: number | null;
    }>("/admin/stats/dashboard", { auth: true }),

  adminReports: () =>
    request<
      {
        id: number;
        target_type: string;
        target_id: number;
        reason: string;
        status: string;
        created_at: string;
      }[]
    >("/admin/reports", { auth: true }),

  resolveReport: (reportId: number, status = "REVIEWED") =>
    request<{ id: number; status: string }>(
      `/admin/reports/${reportId}/resolve`,
      { method: "POST", body: { status }, auth: true },
    ),
};
