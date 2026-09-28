"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Heart, Target, TriangleAlert, Wrench } from "lucide-react";

import { FlagBadge, FlagMark, TierBadge } from "@/components/badges";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Flag, StoreClaim } from "@/lib/types";

const CLAIM_LABEL: Record<string, string> = {
  PENDING: "심사 중",
  APPROVED: "인증됨",
  REJECTED: "반려됨",
};

export default function ProfilePage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [flags, setFlags] = useState<Flag[]>([]);
  const [claims, setClaims] = useState<StoreClaim[]>([]);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (user) {
      api.myFlags().then(setFlags).catch(() => setFlags([]));
      api.myClaims().then(setClaims).catch(() => setClaims([]));
    }
  }, [user]);

  if (!user)
    return (
      <div className="page">
        <div className="card list-empty">로그인이 필요합니다.</div>
      </div>
    );

  const st = user.stat;

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">내 정보</div>
        <button
          onClick={logout}
          className="muted"
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          로그아웃
        </button>
      </div>

      <div className="hero">
        <div className="big">{user.nickname}</div>
        <div className="row" style={{ marginTop: 10, gap: 8 }}>
          <TierBadge level={st.tier_level} />
          <span className="badge badge-on-dark">
            {user.tier_name}
          </span>
        </div>
        <p className="hero-sub" style={{ marginTop: 10 }}>
          EXP {st.exp} · 전국{" "}
          {user.national_rank ? `${user.national_rank}위` : "순위권 밖"}
        </p>
      </div>

      <div className="stat-grid" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="num">{st.gold_flag_count}</div>
          <div className="lbl"><FlagMark type="GOLD" size={12} />골드</div>
        </div>
        <div className="card">
          <div className="num">{st.silver_flag_count}</div>
          <div className="lbl"><FlagMark type="SILVER" size={12} />실버</div>
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
          <div className="lbl"><Heart size={12} />받은 좋아요</div>
        </div>
        <div className="card">
          <div className="num">
            {st.gold_flag_count + st.silver_flag_count}
          </div>
          <div className="lbl">총 깃발</div>
        </div>
      </div>

      <Link href="/missions">
        <button className="btn btn-secondary" style={{ marginTop: 16 }}>
          <Target size={18} strokeWidth={2.5} />
          이번 주 미션
        </button>
      </Link>

      {user.role === "ADMIN" && (
        <Link href="/admin">
          <button className="btn btn-ghost" style={{ marginTop: 10 }}>
            <Wrench size={18} strokeWidth={2.5} />
            관리자 대시보드
          </button>
        </Link>
      )}

      {claims.length > 0 && (
        <>
          <div className="section-title">매장 소유권 신청</div>
          {claims.map((c) => (
            <div
              key={c.id}
              className="card row"
              style={{ justifyContent: "space-between", display: "flex" }}
            >
              <Link href={`/stores/${c.store_id}`} className="link-accent">
                {c.store_name}
              </Link>
              <span
                className={`badge ${
                  c.status === "APPROVED"
                    ? "badge-verified"
                    : c.status === "REJECTED"
                      ? "badge-dark"
                      : "badge-gold"
                }`}
              >
                {CLAIM_LABEL[c.status] ?? c.status}
                {c.review_note ? ` · ${c.review_note}` : ""}
              </span>
            </div>
          ))}
        </>
      )}

      <div className="section-title">내 깃발 기록</div>
      {flags.length === 0 ? (
        <div className="card list-empty">아직 꽂은 깃발이 없습니다.</div>
      ) : (
        flags.map((f) => (
          <Link
            key={f.id}
            href={`/stores/${f.store_id}`}
            className="card row"
            style={{ justifyContent: "space-between", display: "flex" }}
          >
            <FlagBadge type={f.type}>
              {f.type === "GOLD" ? "골드" : "실버"} · +{f.exp_granted} EXP
            </FlagBadge>
            <span className="muted" style={{ fontSize: 12 }}>
              {new Date(f.created_at).toLocaleDateString("ko-KR")}
              {f.is_flagged && (
                <span
                  className="inline-ico"
                  style={{ color: "var(--danger)", marginLeft: 6 }}
                >
                  <TriangleAlert size={12} strokeWidth={2.5} />
                  검토중
                </span>
              )}
            </span>
          </Link>
        ))
      )}
    </div>
  );
}
