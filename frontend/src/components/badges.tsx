import { TIER_NAMES } from "@/lib/types";

export function FlagCount({
  gold,
  silver,
}: {
  gold: number;
  silver: number;
}) {
  return (
    <span className="pill-row">
      <span className="badge badge-gold">🥇 골드 {gold}</span>
      <span className="badge badge-silver">🥈 실버 {silver}</span>
    </span>
  );
}

export function TierBadge({ level }: { level: number }) {
  const crown = level >= 4 ? "👑" : level >= 3 ? "🏅" : "🎖️";
  return (
    <span className="badge badge-gold">
      {crown} {TIER_NAMES[level] ?? `Lv.${level}`}
    </span>
  );
}

export function VerifiedBadge() {
  return <span className="badge badge-verified">✅ 공식 인증 매장</span>;
}
