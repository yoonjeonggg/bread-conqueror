"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Dashboard = Awaited<ReturnType<typeof api.adminDashboard>>;

export default function AdminPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "ADMIN")) router.replace("/");
  }, [loading, user, router]);

  useEffect(() => {
    if (user?.role === "ADMIN")
      api
        .adminDashboard()
        .then(setData)
        .catch(() => setError("대시보드를 불러오지 못했습니다."));
  }, [user]);

  if (!user || user.role !== "ADMIN") return null;

  const tiles: [string, string | number][] = data
    ? [
        ["가입자", data.total_users],
        ["등록 매장", data.total_stores],
        ["총 깃발", data.total_flags],
        ["골드 비율", `${Math.round(data.gold_ratio * 100)}%`],
        ["이번 주 깃발", data.flags_this_week],
        ["검토 대기", data.pending_review],
      ]
    : [];

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🛠️ 관리자</div>
        <Link href="/profile" className="link-accent">
          ← 내 정보
        </Link>
      </div>

      {error && <div className="card list-empty">{error}</div>}
      {!data && !error && <div className="card list-empty">불러오는 중…</div>}

      <div className="stat-grid">
        {tiles.map(([label, value]) => (
          <div key={label} className="card">
            <div className="num">{value}</div>
            <div className="lbl">{label}</div>
          </div>
        ))}
      </div>

      <div className="section-title">운영 메뉴</div>
      <div className="card muted" style={{ fontSize: 13, lineHeight: 1.7 }}>
        · 인증 검토 큐 <code>GET /admin/flags/review-queue</code>
        <br />· 깃발 무효화 / 승인 <code>POST /admin/flags/&#123;id&#125;/…</code>
        <br />· 매장 병합 · 대량 업로드 · 계정 제재 — 2차 스프린트
      </div>
    </div>
  );
}
