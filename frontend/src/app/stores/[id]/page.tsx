"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { FlagCount, VerifiedBadge } from "@/components/badges";
import { ReportButton } from "@/components/ReportButton";
import { ReviewSection } from "@/components/ReviewSection";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Flag, Store } from "@/lib/types";

export default function StoreDetailPage() {
  const params = useParams<{ id: string }>();
  const storeId = Number(params.id);
  const { user } = useAuth();
  const [store, setStore] = useState<Store | null>(null);
  const [flags, setFlags] = useState<Flag[]>([]);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    api.store(storeId).then(setStore).catch(() => setNotFound(true));
    api.storeFlags(storeId).then(setFlags).catch(() => setFlags([]));
  }, [storeId]);

  if (notFound)
    return (
      <div className="page">
        <div className="card list-empty">매장을 찾을 수 없습니다.</div>
      </div>
    );

  if (!store)
    return (
      <div className="page">
        <div className="card list-empty">불러오는 중…</div>
      </div>
    );

  const s = store.stat;

  return (
    <div className="page">
      <div className="page-header">
        <Link href="/map" className="link-accent">
          ← 지도
        </Link>
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="page-title">{store.name}</div>
          {store.is_verified_owner && <VerifiedBadge />}
        </div>
        <p className="muted" style={{ fontSize: 13, margin: "4px 0 12px" }}>
          {store.address}
          {store.category ? ` · ${store.category}` : ""}
        </p>
        <FlagCount
          gold={s?.gold_flag_count ?? 0}
          silver={s?.silver_flag_count ?? 0}
        />
        <div className="stat-grid" style={{ marginTop: 14 }}>
          <div className="card">
            <div className="num">{s?.conqueror_count ?? 0}</div>
            <div className="lbl">정복자</div>
          </div>
          <div className="card">
            <div className="num">
              {(s?.gold_flag_count ?? 0) + (s?.silver_flag_count ?? 0)}
            </div>
            <div className="lbl">총 깃발</div>
          </div>
          <div className="card">
            <div className="num">{s?.average_rating ?? "–"}</div>
            <div className="lbl">평점</div>
          </div>
        </div>
      </div>

      {user ? (
        <Link href={`/conquer/${store.id}`}>
          <button className="btn btn-primary" style={{ marginTop: 16 }}>
            🚩 방문 인증하고 정복하기
          </button>
        </Link>
      ) : (
        <Link href="/login">
          <button className="btn btn-ghost" style={{ marginTop: 16 }}>
            로그인하고 정복하기
          </button>
        </Link>
      )}

      {user && store.owner_id === user.id && (
        <Link href={`/stores/${store.id}/manage`}>
          <button className="btn btn-secondary" style={{ marginTop: 10 }}>
            🏪 매장 관리 · QR 발급
          </button>
        </Link>
      )}
      {user && store.owner_id == null && (
        <Link href={`/stores/${store.id}/claim`}>
          <button className="btn btn-ghost" style={{ marginTop: 10 }}>
            이 매장의 사장님이신가요? 소유권 신청
          </button>
        </Link>
      )}

      <ReviewSection storeId={store.id} />

      <div className="section-title">최근 깃발</div>
      {flags.length === 0 ? (
        <div className="card list-empty">아직 이 빵집에 깃발이 없습니다.</div>
      ) : (
        flags.slice(0, 20).map((f) => (
          <div key={f.id} className="card">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span
                className={`badge ${f.type === "GOLD" ? "badge-gold" : "badge-silver"}`}
              >
                {f.type === "GOLD" ? "🥇 골드" : "🥈 실버"}
              </span>
              <span className="muted" style={{ fontSize: 12 }}>
                {new Date(f.created_at).toLocaleDateString("ko-KR")}
                {f.upgraded_from_silver ? " · 업그레이드" : ""}
              </span>
            </div>
            <div style={{ marginTop: 6 }}>
              <ReportButton targetType="FLAG" targetId={f.id} label="이 인증 신고" />
            </div>
          </div>
        ))
      )}
    </div>
  );
}
