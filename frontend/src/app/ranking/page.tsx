"use client";

import { useEffect, useState } from "react";

import { TierBadge } from "@/components/badges";
import { api } from "@/lib/api";
import type { RankingResponse } from "@/lib/types";

export default function RankingPage() {
  const [data, setData] = useState<RankingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .nationalRanking()
      .then(setData)
      .catch(() => setError("랭킹을 불러오지 못했습니다."));
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🏆 전국 랭킹</div>
      </div>

      {data?.my_rank && (
        <div className="hero" style={{ marginBottom: 16 }}>
          <div className="muted" style={{ color: "#f8e9d6", fontSize: 13 }}>
            내 순위
          </div>
          <div className="big">{data.my_rank}위</div>
        </div>
      )}

      {error && <div className="card list-empty">{error}</div>}

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
    </div>
  );
}
