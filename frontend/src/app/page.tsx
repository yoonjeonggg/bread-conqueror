"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StoreCard } from "@/components/StoreCard";
import { TierBadge } from "@/components/badges";
import { DEFAULT_COORDS, useGeolocation } from "@/components/useGeolocation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Post, Store } from "@/lib/types";

export default function HomePage() {
  const { user, loading } = useAuth();
  const { coords } = useGeolocation();
  const [popular, setPopular] = useState<Store[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);

  useEffect(() => {
    const c = coords ?? DEFAULT_COORDS;
    api
      .nearbyStores(c.lat, c.lng, 8000)
      .then((rows) => {
        const sorted = [...rows].sort(
          (a, b) =>
            (b.stat?.conqueror_count ?? 0) - (a.stat?.conqueror_count ?? 0),
        );
        setPopular(sorted.slice(0, 5));
      })
      .catch(() => setPopular([]));
    api.posts().then(setPosts).catch(() => setPosts([]));
  }, [coords]);

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🥐 Bread Conqueror</div>
        {!loading && !user && (
          <Link href="/login" className="link-accent">
            로그인
          </Link>
        )}
      </div>

      {user ? (
        <div className="hero">
          <div className="muted" style={{ color: "#f8e9d6", fontSize: 13 }}>
            {user.nickname} 님
          </div>
          <div className="big">EXP {user.stat.exp}</div>
          <div className="row" style={{ marginTop: 10, gap: 8 }}>
            <TierBadge level={user.stat.tier_level} />
            <span
              className="badge"
              style={{ background: "rgba(255,255,255,0.18)", color: "#fff" }}
            >
              전국 {user.national_rank ? `${user.national_rank}위` : "순위권 밖"}
            </span>
          </div>
          <div className="stat-grid" style={{ marginTop: 14 }}>
            <div className="card">
              <div className="num">{user.stat.gold_flag_count}</div>
              <div className="lbl">골드 깃발</div>
            </div>
            <div className="card">
              <div className="num">{user.stat.silver_flag_count}</div>
              <div className="lbl">실버 깃발</div>
            </div>
            <div className="card">
              <div className="num">{user.stat.conquered_store_count}</div>
              <div className="lbl">정복한 빵집</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="hero">
          <div className="big">전국 빵집을 정복하세요</div>
          <p style={{ color: "#f8e9d6", fontSize: 14, margin: "8px 0 14px" }}>
            방문하고 깃발을 꽂으면 경험치와 티어가 올라갑니다.
          </p>
          <Link href="/signup">
            <button className="btn btn-primary">시작하기</button>
          </Link>
        </div>
      )}

      <div className="section-title">🔥 이번 주 인기 정복지</div>
      {popular.length === 0 ? (
        <div className="card list-empty">
          주변 빵집 데이터를 불러오는 중입니다.
        </div>
      ) : (
        popular.map((s) => <StoreCard key={s.id} store={s} />)
      )}

      <div className="section-title">📝 추천 게시글</div>
      {posts.length === 0 ? (
        <div className="card list-empty">아직 추천 게시글이 없습니다.</div>
      ) : (
        posts.slice(0, 3).map((p) => (
          <div key={p.id} className="card">
            <strong>{p.title}</strong>
            <p className="muted" style={{ fontSize: 13, margin: "6px 0 0" }}>
              {p.content.slice(0, 80)}
            </p>
            <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              작성자 티어 Lv.{p.author_tier_snapshot} · 깃발{" "}
              {p.author_flag_count_snapshot}개 · ♥ {p.like_count}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
