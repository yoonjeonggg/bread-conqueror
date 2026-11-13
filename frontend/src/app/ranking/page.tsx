"use client";

import { useEffect, useState } from "react";

import { TierBadge } from "@/components/badges";
import { BreadAvatar, breadFor } from "@/components/BreadAvatar";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { RankingEntry, RankingResponse } from "@/lib/types";

type Tab = "national" | "friends";

// 시상대 칸: 화면 순서는 2위·1위·3위.
const PODIUM_ORDER = [1, 0, 2];
const PODIUM_STEP = [
  { height: 116, background: "#ffd25a", avatar: 84 },
  { height: 84, background: "#d5dbe6", avatar: 64 },
  { height: 60, background: "#e6eaf1", avatar: 64 },
];

function PodiumConfetti() {
  const spark = "M200 8l1.6 4.4 4.4 1.6-4.4 1.6L200 20l-1.6-4.4-4.4-1.6 4.4-1.6z";
  return (
    <svg className="podium-confetti" viewBox="0 0 400 120" aria-hidden="true">
      <g fill="#ffb800">
        <circle cx="150" cy="30" r="3" />
        <circle cx="250" cy="22" r="2.5" />
        <circle cx="118" cy="62" r="2" />
        <circle cx="282" cy="58" r="2.2" />
      </g>
      <g fill="#ff5a1f">
        <circle cx="180" cy="14" r="2.2" />
        <circle cx="222" cy="40" r="2" />
      </g>
      <path d={spark} fill="#ffb800" transform="translate(-52 6)" />
      <path d={spark} fill="#ff5a1f" transform="translate(58 14)" />
    </svg>
  );
}

function Podium({ top }: { top: RankingEntry[] }) {
  return (
    <div className="card podium">
      <PodiumConfetti />
      <div className="podium-row">
        {PODIUM_ORDER.map((i) => {
          const e = top[i];
          if (!e) return <div key={i} className="podium-slot" />;
          const step = PODIUM_STEP[i];
          return (
            <div key={e.user_id} className="podium-slot">
              <BreadAvatar
                variant={i === 0 ? "king" : breadFor(e.user_id)}
                size={step.avatar}
              />
              <div className="podium-name">{e.nickname}</div>
              <div className="podium-exp">EXP {e.exp.toLocaleString()}</div>
              <div
                className="podium-step"
                style={{ height: step.height, background: step.background }}
              >
                {e.rank}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function RankingPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("national");
  const [data, setData] = useState<RankingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    const p =
      tab === "friends" ? api.friendsRanking() : api.nationalRanking();
    p.then(setData).catch(() => setError("랭킹을 불러오지 못했습니다."));
  }, [tab]);

  const entries = data?.entries ?? [];
  const top = entries.slice(0, 3);
  const rest = entries.slice(3);

  // 다음 순위까지 남은 EXP: 내 바로 위 순위가 목록에 있을 때만 계산된다.
  const myRank = data?.my_rank ?? null;
  const myExp =
    entries.find((e) => e.user_id === user?.id)?.exp ?? user?.stat.exp ?? null;
  const above =
    myRank && myRank > 1
      ? entries.filter((e) => e.rank < myRank).pop()
      : undefined;
  const toNext = above && myExp != null ? above.exp - myExp + 1 : null;

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">랭킹</div>
      </div>

      <div className="tabs" style={{ marginBottom: 14 }}>
        <button
          className={`tab${tab === "national" ? " on" : ""}`}
          onClick={() => setTab("national")}
        >
          전국
        </button>
        <button
          className={`tab${tab === "friends" ? " on" : ""}`}
          onClick={() => setTab("friends")}
          disabled={!user}
        >
          친구
        </button>
      </div>

      {tab === "friends" && !user && (
        <div className="card list-empty">로그인하면 친구 랭킹을 볼 수 있습니다.</div>
      )}

      {error && <div className="card list-empty">{error}</div>}

      {(tab === "national" || user) && !error && (
        <>
          {!data && <div className="card list-empty">불러오는 중…</div>}
          {data && entries.length === 0 && (
            <div className="card list-empty">아직 랭킹 데이터가 없습니다.</div>
          )}

          {top.length > 0 && <Podium top={top} />}

          {user && myRank && (
            <div className="hero my-rank">
              <span className="my-rank-avatar">
                <BreadAvatar variant="flag" size={44} />
              </span>
              <div style={{ flex: 1 }}>
                <div className="hsub">{user.nickname} 님의 순위</div>
                <div className="my-rank-no">
                  {tab === "friends" ? "친구 중" : "전국"} {myRank.toLocaleString()}위
                </div>
              </div>
              {toNext != null && toNext > 0 && (
                <span className="badge my-rank-gap">
                  다음 순위까지 EXP {toNext.toLocaleString()}
                </span>
              )}
            </div>
          )}

          {rest.length > 0 && (
            <div className="card" style={{ marginTop: 12, padding: "4px 16px" }}>
              {rest.map((e) => (
                <div key={e.user_id} className="rank-row">
                  <span className="no">{e.rank}</span>
                  <span className="rank-avatar">
                    <BreadAvatar variant={breadFor(e.user_id)} size={40} />
                  </span>
                  <div className="stack" style={{ flex: 1 }}>
                    <strong>{e.nickname}</strong>
                    <span className="muted" style={{ fontSize: 12 }}>
                      EXP {e.exp.toLocaleString()}
                    </span>
                  </div>
                  <TierBadge level={e.tier_level} />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
