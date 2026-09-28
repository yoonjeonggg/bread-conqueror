import { Award, BadgeCheck, Crown, Flag, Medal } from "lucide-react";

import { TIER_NAMES } from "@/lib/types";

// filled flag glyph used wherever a gold/silver flag is shown
export function FlagMark({
  type,
  size = 14,
}: {
  type: "GOLD" | "SILVER";
  size?: number;
}) {
  const color = type === "GOLD" ? "var(--gold)" : "var(--silver)";
  return <Flag size={size} strokeWidth={2.5} color={color} fill={color} />;
}

export function FlagBadge({
  type,
  children,
}: {
  type: "GOLD" | "SILVER";
  children?: React.ReactNode;
}) {
  return (
    <span className={`badge ${type === "GOLD" ? "badge-gold" : "badge-silver"}`}>
      <Flag size={12} strokeWidth={2.5} fill="currentColor" />
      {children ?? (type === "GOLD" ? "골드" : "실버")}
    </span>
  );
}

export function FlagCount({
  gold,
  silver,
}: {
  gold: number;
  silver: number;
}) {
  return (
    <span className="pill-row">
      <FlagBadge type="GOLD">골드 {gold}</FlagBadge>
      <FlagBadge type="SILVER">실버 {silver}</FlagBadge>
    </span>
  );
}

export function TierBadge({ level }: { level: number }) {
  const Icon = level >= 4 ? Crown : level >= 3 ? Medal : Award;
  return (
    <span className="badge badge-gold">
      <Icon size={12} strokeWidth={2.5} />
      {TIER_NAMES[level] ?? `Lv.${level}`}
    </span>
  );
}

export function VerifiedBadge() {
  return (
    <span className="badge badge-verified">
      <BadgeCheck size={12} strokeWidth={2.5} />
      공식 인증 매장
    </span>
  );
}
