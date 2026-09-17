"use client";

import { useEffect, useState } from "react";

import { TierBadge } from "@/components/badges";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { RankingResponse } from "@/lib/types";

type Tab = "national" | "regional" | "friends";

export default function RankingPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("national");
  const [data, setData] = useState<RankingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regions, setRegions] = useState<string[]>([]);
  const [region, setRegion] = useState("");

  useEffect(() => {
    api
      .storeFilters()
      .then((f) => {
        setRegions(f.regions);
        setRegion((prev) => prev || f.regions[0] || "");
      })
      .catch(() => setRegions([]));
  }, []);

  useEffect(() => {
    if (tab === "regional" && !region) return;
    setData(null);
    setError(null);
    const p =
      tab === "friends"
        ? api.friendsRanking()
        : tab === "regional"
          ? api.regionalRanking(region)
          : api.nationalRanking();
    p.then(setData).catch(() => setError("랭킹을 불러오지 못했습니다."));
  }, [tab, region]);

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🏆 랭킹</div>
      </div>

      <div className="pill-row" style={{ marginBottom: 14 }}>
        <button
          className={`badge ${tab === "national" ? "badge-gold" : "badge-silver"}`}
          style={{ border: "none", cursor: "pointer", padding: "8px 16px" }}
          onClick={() => setTab("national")}
        >
          전국
        </button>
        <button
          className={`badge ${tab === "regional" ? "badge-gold" : "badge-silver"}`}
          style={{ border: "none", cursor: "pointer", padding: "8px 16px" }}
          onClick={() => setTab("regional")}
          disabled={regions.length === 0}
        >
          지역
        </button>
        <button
          className={`badge ${tab === "friends" ? "badge-gold" : "badge-silver"}`}
          style={{ border: "none", cursor: "pointer", padding: "8px 16px" }}
          onClick={() => setTab("friends")}
          disabled={!user}
        >
          친구
        </button>
      </div>

      {tab === "regional" && regions.length > 0 && (
        <select
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          style={{ marginBottom: 14 }}
        >
          {regions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      )}

      {tab === "friends" && !user && (
        <div className="card list-empty">로그인하면 친구 랭킹을 볼 수 있습니다.</div>
      )}

      {data?.my_rank && (
        <div className="hero" style={{ marginBottom: 16 }}>
          <div className="muted" style={{ color: "#f8e9d6", fontSize: 13 }}>
            내 순위 (
            {tab === "friends" ? "친구" : tab === "regional" ? region : "전국"})
          </div>
          <div className="big">{data.my_rank}위</div>
        </div>
      )}

      {error && <div className="card list-empty">{error}</div>}

      {(tab !== "friends" || user) && (
        <div className="card">
          {!data && !error && <div className="list-empty">불러오는 중…</div>}
          {data?.entries.length === 0 && (
            <div className="list-empty">아직 랭킹 데이터가 없습니다.</div>
          )}
          {data?.entries.map((e) => (
            <div key={e.user_id} className="rank-row">
              <span className="no">
                {e.rank <= 3 ? ["🥇", "🥈", "🥉"][e.rank - 1] : e.rank}
              </span>
              <div className="stack" style={{ flex: 1 }}>
                <strong>{e.nickname}</strong>
                <span className="muted" style={{ fontSize: 12 }}>
                  EXP {e.exp}
                </span>
              </div>
              <TierBadge level={e.tier_level} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
