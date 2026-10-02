"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ChevronRight,
  Heart,
  LoaderCircle,
  LogOut,
  MapPin,
  RotateCw,
  Target,
  Trophy,
  TriangleAlert,
  Wrench,
} from "lucide-react";

import { FlagBadge, FlagMark, TierBadge } from "@/components/badges";
import { api, getToken } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { MyFlag, Profile, StoreClaim } from "@/lib/types";
import { formatDate } from "@/lib/format";

const PAGE_SIZE = 20;

const CLAIM_LABEL: Record<string, string> = {
  PENDING: "심사 중",
  APPROVED: "인증됨",
  REJECTED: "반려됨",
};

function TierProgress({ user }: { user: Profile }) {
  const st = user.stat;
  if (user.next_tier_exp === null || user.next_tier_name === null) {
    return (
      <div className="tier-progress">
        <div className="tier-progress-meta">
          <strong>최고 티어 달성</strong>
          <span>EXP {st.exp.toLocaleString()}</span>
        </div>
      </div>
    );
  }

  const span = Math.max(user.next_tier_exp - user.tier_min_exp, 1);
  const pct = Math.min(100, Math.max(0, ((st.exp - user.tier_min_exp) / span) * 100));
  const remaining = user.next_tier_exp - st.exp;

  // upper tiers also gate on gold ratio, so enough exp alone may not promote
  const totalFlags = st.gold_flag_count + st.silver_flag_count;
  const goldRatio = totalFlags ? st.gold_flag_count / totalFlags : 0;
  const ratioShort =
    user.next_tier_gold_ratio !== null && goldRatio < user.next_tier_gold_ratio;

  return (
    <div className="tier-progress">
      <div
        className="mission-bar"
        role="progressbar"
        aria-label={`${user.next_tier_name} 승급 진행도`}
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="mission-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="tier-progress-meta">
        <span>
          EXP <strong>{st.exp.toLocaleString()}</strong> /{" "}
          {user.next_tier_exp.toLocaleString()}
        </span>
        <span>
          {remaining > 0 ? (
            <>
              <strong>{user.next_tier_name}</strong>까지 {remaining.toLocaleString()}
            </>
          ) : ratioShort ? (
            <>
              골드 비율 {Math.round(user.next_tier_gold_ratio! * 100)}% 필요 (현재{" "}
              {Math.round(goldRatio * 100)}%)
            </>
          ) : (
            <strong>승급 대기</strong>
          )}
        </span>
      </div>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="page" aria-busy="true" aria-label="내 정보 불러오는 중">
      <div className="page-header">
        <div className="page-title">내 정보</div>
      </div>
      <div className="hero">
        <div className="skeleton" style={{ height: 32, width: "50%" }} />
        <div className="skeleton" style={{ height: 22, width: "40%", marginTop: 12 }} />
        <div className="skeleton" style={{ height: 8, marginTop: 20 }} />
      </div>
      <div className="stat-grid" style={{ marginTop: 16 }}>
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="skeleton" style={{ height: 64 }} />
        ))}
      </div>
      <FlagListSkeleton />
    </div>
  );
}

function FlagListSkeleton() {
  return (
    <>
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="skeleton" style={{ height: 62, marginTop: 10 }} />
      ))}
    </>
  );
}

export default function ProfilePage() {
  const { user, loading: authLoading, logout, refresh } = useRequireAuth();
  const [flags, setFlags] = useState<MyFlag[] | null>(null);
  const [flagsError, setFlagsError] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [claims, setClaims] = useState<StoreClaim[]>([]);

  const loadFlags = useCallback(async (beforeId?: number) => {
    setFlagsError(false);
    try {
      const rows = await api.myFlags(PAGE_SIZE, beforeId);
      setFlags((prev) => (beforeId && prev ? [...prev, ...rows] : rows));
      setHasMore(rows.length === PAGE_SIZE);
    } catch {
      setFlagsError(true);
      if (!beforeId) setFlags((prev) => prev ?? []);
    }
  }, []);

  // Kick off the lists as soon as a token exists instead of waiting for
  // /users/me to resolve — the three requests run side by side.
  useEffect(() => {
    if (!getToken()) return;
    loadFlags();
    api.myClaims().then(setClaims).catch(() => setClaims([]));
    // the auth context fetched the profile once at app start; stats change
    // after every conquest, so revalidate while showing the cached copy
    if (!authLoading) refresh();
    // mount-only: refresh/authLoading are read once on purpose
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadFlags]);

  const loadMore = async () => {
    if (!flags?.length) return;
    setLoadingMore(true);
    await loadFlags(flags[flags.length - 1].id);
    setLoadingMore(false);
  };

  if (!user) return <ProfileSkeleton />;

  const st = user.stat;

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">내 정보</div>
        <button onClick={logout} className="text-btn muted">
          <LogOut size={14} strokeWidth={2.5} />
          로그아웃
        </button>
      </div>

      <div className="hero">
        <div className="big">{user.nickname}</div>
        <div className="row" style={{ marginTop: 10, gap: 8 }}>
          <TierBadge level={st.tier_level} />
          <span className="badge badge-on-dark">Lv.{st.tier_level}</span>
        </div>
        <TierProgress user={user} />
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
        <Link href="/ranking" className="card">
          <div className="num">{user.national_rank ?? "–"}</div>
          <div className="lbl"><Trophy size={12} />전국 순위</div>
        </Link>
      </div>

      <Link href="/missions" className="btn btn-secondary" style={{ marginTop: 16 }}>
        <Target size={18} strokeWidth={2.5} />
        이번 주 미션
      </Link>

      {user.role === "ADMIN" && (
        <Link href="/admin" className="btn btn-ghost" style={{ marginTop: 10 }}>
          <Wrench size={18} strokeWidth={2.5} />
          관리자 대시보드
        </Link>
      )}

      {claims.length > 0 && (
        <>
          <div className="section-title">매장 소유권 신청</div>
          {claims.map((c) => (
            <Link key={c.id} href={`/stores/${c.store_id}`} className="card history-row">
              <div style={{ minWidth: 0 }}>
                <div className="name">{c.store_name}</div>
                {c.review_note && <div className="sub">{c.review_note}</div>}
              </div>
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
              </span>
            </Link>
          ))}
        </>
      )}

      <div className="section-title">내 깃발 기록</div>
      {flags === null ? (
        <FlagListSkeleton />
      ) : flags.length === 0 && flagsError ? (
        <div className="card list-empty">
          깃발 기록을 불러오지 못했습니다.
          <button
            className="btn btn-ghost"
            style={{ marginTop: 12 }}
            onClick={() => {
              setFlags(null);
              loadFlags();
            }}
          >
            <RotateCw size={16} strokeWidth={2.5} />
            다시 시도
          </button>
        </div>
      ) : flags.length === 0 ? (
        <div className="card list-empty">
          아직 꽂은 깃발이 없습니다.
          <Link href="/map" className="btn btn-primary" style={{ marginTop: 12 }}>
            <MapPin size={16} strokeWidth={2.5} />
            주변 빵집 찾아보기
          </Link>
        </div>
      ) : (
        <>
          {flags.map((f) => (
            <Link key={f.id} href={`/stores/${f.store_id}`} className="card history-row">
              <div style={{ minWidth: 0 }}>
                <div className="name">{f.store_name}</div>
                <div className="sub">
                  <FlagBadge type={f.type}>
                    {f.type === "GOLD" ? "골드" : "실버"} +{f.exp_granted}
                  </FlagBadge>
                  {formatDate(f.created_at)}
                  {f.is_flagged && (
                    <span className="inline-ico" style={{ color: "var(--danger)" }}>
                      <TriangleAlert size={12} strokeWidth={2.5} />
                      검토중
                    </span>
                  )}
                </div>
              </div>
              <ChevronRight size={18} className="chev" />
            </Link>
          ))}
          {flagsError && (
            <div className="error-text" role="alert">
              더 불러오지 못했습니다. 다시 시도해 주세요.
            </div>
          )}
          {hasMore && (
            <button
              className="btn btn-ghost"
              style={{ marginTop: 10 }}
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? <LoaderCircle size={16} className="spin" /> : null}
              {loadingMore ? "불러오는 중" : "더 보기"}
            </button>
          )}
        </>
      )}
    </div>
  );
}
