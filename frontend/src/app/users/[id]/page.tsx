"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { TierBadge } from "@/components/badges";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { FollowCounts, Profile } from "@/lib/types";

export default function PublicProfilePage() {
  const params = useParams<{ id: string }>();
  const userId = Number(params.id);
  const { user } = useAuth();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [counts, setCounts] = useState<FollowCounts | null>(null);
  const [missing, setMissing] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadCounts = useCallback(() => {
    if (user)
      api.followCounts(userId).then(setCounts).catch(() => setCounts(null));
  }, [user, userId]);

  useEffect(() => {
    api.profile(userId).then(setProfile).catch(() => setMissing(true));
    loadCounts();
  }, [userId, loadCounts]);

  if (missing)
    return (
      <div className="page">
        <div className="card list-empty">사용자를 찾을 수 없습니다.</div>
      </div>
    );
  if (!profile)
    return (
      <div className="page">
        <div className="card list-empty">불러오는 중…</div>
      </div>
    );

  const isMe = user?.id === userId;
  const st = profile.stat;

  async function toggleFollow() {
    if (!counts) return;
    setBusy(true);
    try {
      if (counts.is_following) await api.unfollow(userId);
      else await api.follow(userId);
      loadCounts();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="hero">
        <div className="big">{profile.nickname}</div>
        <div className="row" style={{ marginTop: 10, gap: 8 }}>
          <TierBadge level={st.tier_level} />
          <span
            className="badge"
            style={{ background: "rgba(255,255,255,0.18)", color: "#fff" }}
          >
            {profile.tier_name}
          </span>
        </div>
        {counts && (
          <p style={{ color: "#f8e9d6", fontSize: 13, marginTop: 10 }}>
            팔로워 {counts.followers} · 팔로잉 {counts.following}
          </p>
        )}
      </div>

      {user && !isMe && counts && (
        <button
          className={counts.is_following ? "btn btn-ghost" : "btn btn-primary"}
          style={{ marginTop: 14 }}
          disabled={busy}
          onClick={toggleFollow}
        >
          {counts.is_following ? "팔로잉 해제" : "+ 팔로우"}
        </button>
      )}

      <div className="stat-grid" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="num">{st.gold_flag_count}</div>
          <div className="lbl">🥇 골드</div>
        </div>
        <div className="card">
          <div className="num">{st.silver_flag_count}</div>
          <div className="lbl">🥈 실버</div>
        </div>
        <div className="card">
          <div className="num">{st.conquered_store_count}</div>
          <div className="lbl">정복 빵집</div>
        </div>
        <div className="card">
          <div className="num">{st.review_count}</div>
          <div className="lbl">리뷰</div>
        </div>
        <div className="card">
          <div className="num">{st.received_like_count}</div>
          <div className="lbl">받은 ♥</div>
        </div>
        <div className="card">
          <div className="num">{profile.national_rank ?? "–"}</div>
          <div className="lbl">전국 순위</div>
        </div>
      </div>
    </div>
  );
}
