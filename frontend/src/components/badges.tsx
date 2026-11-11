import { TIER_NAMES } from "@/lib/types";
import { Icon } from "./Icon";

export function FlagIcon({
  type,
  size = 12,
}: {
  type?: "GOLD" | "SILVER";
  size?: number;
}) {
  // Without a type the flag takes the surrounding badge's text color.
  const color =
    type === "GOLD" ? "var(--gold)" : type === "SILVER" ? "var(--silver)" : "currentColor";
  return <Icon name="flag" size={size} color={color} fill />;
}

export function FlagBadge({
  type,
  children,
}: {
  type: "GOLD" | "SILVER";
  children: React.ReactNode;
}) {
  return (
    <span className={`badge ${type === "GOLD" ? "badge-gold" : "badge-silver"}`}>
      <FlagIcon />
      {children}
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
  return (
    <span className="badge badge-gold">
      <Icon name={level >= 4 ? "crown" : "medal"} size={12} />
      {TIER_NAMES[level] ?? `Lv.${level}`}
    </span>
  );
}

export function VerifiedBadge() {
  return (
    <span className="badge badge-verified">
      <Icon name="badgeCheck" size={12} />
      공식 인증 매장
    </span>
  );
}
