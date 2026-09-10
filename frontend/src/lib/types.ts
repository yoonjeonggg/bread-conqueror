export type FlagType = "GOLD" | "SILVER";

export interface UserStat {
  exp: number;
  tier_level: number;
  gold_flag_count: number;
  silver_flag_count: number;
  conquered_store_count: number;
  review_count: number;
  received_like_count: number;
}

export interface Profile {
  id: number;
  nickname: string;
  email: string;
  profile_image_url: string | null;
  role: "USER" | "ADMIN";
  stat: UserStat;
  tier_name: string;
  national_rank: number | null;
}

export interface StoreStat {
  gold_flag_count: number;
  silver_flag_count: number;
  conqueror_count: number;
  average_rating: number | null;
}

export interface Store {
  id: number;
  name: string;
  address: string;
  region_sido: string | null;
  lat: number;
  lng: number;
  category: string | null;
  thumbnail_url: string | null;
  created_source: "AUTO_COLLECTED" | "USER_ADDED";
  is_verified_owner: boolean;
  owner_id: number | null;
  status: string;
  stat: StoreStat | null;
  distance_m?: number | null;
  conquered_by_me?: boolean;
}

export interface Flag {
  id: number;
  store_id: number;
  user_id: number;
  type: FlagType;
  evidence_type: string;
  evidence_image_url: string | null;
  exp_granted: number;
  is_flagged: boolean;
  status: string;
  upgraded_from_silver: boolean;
  created_at: string;
}

export interface ConquestResponse {
  flag: Flag;
  exp_granted: number;
  tier_changed: boolean;
  new_tier_level: number;
  upgraded_from_silver: boolean;
  is_flagged: boolean;
  abuse_reasons: string[];
}

export interface RankingEntry {
  rank: number;
  user_id: number;
  nickname: string;
  tier_level: number;
  exp: number;
}

export interface RankingResponse {
  scope: string;
  region_sido: string | null;
  entries: RankingEntry[];
  my_rank: number | null;
}

export interface Review {
  id: number;
  store_id: number;
  user_id: number;
  rating: number;
  content: string | null;
  created_at: string;
  author_nickname?: string;
  author_tier_level?: number;
}

export interface FollowCounts {
  followers: number;
  following: number;
  is_following: boolean;
}

export interface Comment {
  id: number;
  post_id: number;
  user_id: number;
  content: string;
  created_at: string;
}

export interface Post {
  id: number;
  title: string;
  content: string;
  store_id: number | null;
  like_count: number;
  status: string;
  created_at: string;
  author_tier_snapshot: number;
  author_flag_count_snapshot: number;
}

export type ClaimStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface StoreClaim {
  id: number;
  store_id: number;
  user_id: number;
  status: ClaimStatus;
  review_note: string | null;
  created_at: string;
  reviewed_at: string | null;
  store_name: string;
}

export interface QrToken {
  id: number;
  store_id: number;
  token: string;
  label: string | null;
  max_uses: number | null;
  use_count: number;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
  active: boolean;
}

export interface AdminClaim extends StoreClaim {
  user_nickname: string;
  business_license_image_url: string;
  contact_phone: string;
}

export interface WeeklyMission {
  code: string;
  title: string;
  description: string;
  metric: string;
  target: number;
  reward_exp: number;
  progress: number;
  completed: boolean;
  claimed: boolean;
}

export interface WeeklyMissions {
  week_start: string;
  missions: WeeklyMission[];
}

export type NotificationType =
  | "FOLLOW"
  | "POST_COMMENT"
  | "POST_LIKE"
  | "CLAIM_APPROVED"
  | "CLAIM_REJECTED"
  | "TIER_UP"
  | "FLAG_APPROVED"
  | "FLAG_INVALIDATED"
  | "QR_CONQUEST";

export interface AppNotification {
  id: number;
  type: NotificationType;
  actor_id: number | null;
  actor_nickname: string | null;
  target_type: string | null;
  target_id: number | null;
  message: string;
  is_read: boolean;
  created_at: string;
}

export const TIER_NAMES: Record<number, string> = {
  1: "빵 입문자",
  2: "빵 탐험가",
  3: "지역 정복자",
  4: "전국 정복자",
  5: "전설의 빵 정복자",
};
