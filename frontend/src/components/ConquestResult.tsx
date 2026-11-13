import Link from "next/link";

import type { ConquestResponse, FlagType } from "@/lib/types";
import { FlagIcon } from "./badges";
import { Icon } from "./Icon";

// Celebration screen shown after a flag is planted (manual or QR conquest).
export function ConquestResult({
  result,
  flagType,
  title,
  description,
  storeHref,
  storeLabel,
}: {
  result: ConquestResponse;
  flagType: FlagType;
  /** Heading when the flag was not an upgrade from silver. */
  title: string;
  description: string;
  storeHref: string;
  storeLabel: string;
}) {
  const upgraded = result.upgraded_from_silver;
  return (
    <div className="page">
      <div className="conquer-celebrate">
        <div className="flag">
          {upgraded && (
            <>
              <FlagIcon type="SILVER" size={56} />
              <Icon name="arrowRight" size={28} color="var(--ink-soft)" />
            </>
          )}
          <FlagIcon type={upgraded ? "GOLD" : flagType} size={72} />
        </div>
        <h2 style={{ margin: "12px 0 4px" }}>
          {upgraded ? "골드로 업그레이드!" : title}
        </h2>
        <p className="muted">{description}</p>
        <div className="hero" style={{ marginTop: 20, textAlign: "left" }}>
          <div className="big">+{result.exp_granted} EXP</div>
          {result.tier_changed && (
            <p className="hsub ii" style={{ margin: "8px 0 0", fontSize: 14 }}>
              <Icon name="trendingUp" size={16} />
              티어가 Lv.{result.new_tier_level}로 상승했습니다!
            </p>
          )}
          {result.is_flagged && (
            <p className="hsub" style={{ margin: "8px 0 0" }}>
              <Icon name="alert" size={14} style={{ verticalAlign: "-2px", marginRight: 4 }} />
              이상 패턴이 감지되어 검토 대기 상태입니다.
              {result.abuse_reasons.map((r) => (
                <span key={r}> {r}.</span>
              ))}
            </p>
          )}
        </div>
        <div style={{ marginTop: 20, display: "grid", gap: 10 }}>
          <Link href={storeHref}>
            <button className="btn btn-secondary">{storeLabel}</button>
          </Link>
          <Link href="/profile">
            <button className="btn btn-ghost">내 깃발 보기</button>
          </Link>
        </div>
      </div>
    </div>
  );
}
