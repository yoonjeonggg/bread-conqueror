"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Dashboard = Awaited<ReturnType<typeof api.adminDashboard>>;
type Report = Awaited<ReturnType<typeof api.adminReports>>[number];

export default function AdminPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadReports = () =>
    api.adminReports().then(setReports).catch(() => setReports([]));

  useEffect(() => {
    if (!loading && (!user || user.role !== "ADMIN")) router.replace("/");
  }, [loading, user, router]);

  useEffect(() => {
    if (user?.role === "ADMIN") {
      api
        .adminDashboard()
        .then(setData)
        .catch(() => setError("대시보드를 불러오지 못했습니다."));
      loadReports();
    }
  }, [user]);

  if (!user || user.role !== "ADMIN") return null;

  const tiles: [string, string | number][] = data
    ? [
        ["가입자", data.total_users],
        ["등록 매장", data.total_stores],
        ["총 깃발", data.total_flags],
        ["골드 비율", `${Math.round(data.gold_ratio * 100)}%`],
        ["이번 주 깃발", data.flags_this_week],
        ["깃발 검토", data.pending_review],
        ["신고 대기", data.pending_reports],
        ["정지 계정", data.suspended_users],
        ["평균 평점", data.average_store_rating ?? "–"],
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

      <div className="section-title">신고 대기 ({reports.length})</div>
      {reports.length === 0 ? (
        <div className="card list-empty">처리할 신고가 없습니다.</div>
      ) : (
        reports.map((r) => (
          <div key={r.id} className="card">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="badge badge-silver">
                {r.target_type} #{r.target_id}
              </span>
              <span className="muted" style={{ fontSize: 11 }}>
                {new Date(r.created_at).toLocaleDateString("ko-KR")}
              </span>
            </div>
            <p style={{ fontSize: 14, margin: "8px 0" }}>{r.reason}</p>
            <div className="row" style={{ gap: 8 }}>
              <button
                className="btn btn-ghost"
                style={{ width: "auto", padding: "8px 12px" }}
                onClick={async () => {
                  await api.resolveReport(r.id, "REVIEWED");
                  loadReports();
                }}
              >
                처리 완료
              </button>
              <button
                className="btn btn-ghost"
                style={{ width: "auto", padding: "8px 12px" }}
                onClick={async () => {
                  await api.resolveReport(r.id, "REJECTED");
                  loadReports();
                }}
              >
                반려
              </button>
            </div>
          </div>
        ))
      )}

      <div className="section-title">운영 메뉴 (API)</div>
      <div className="card muted" style={{ fontSize: 13, lineHeight: 1.7 }}>
        · 깃발 검토 큐 <code>GET /admin/flags/review-queue</code>
        <br />· 계정 정지/해제 <code>POST /admin/users/&#123;id&#125;/suspend</code>
        <br />· 경험치 조정 <code>POST /admin/users/&#123;id&#125;/adjust-exp</code>
        <br />· 콘텐츠 모더레이션 <code>POST /admin/posts/&#123;id&#125;/moderate</code>
        <br />· 매장 병합 · 엑셀 대량 업로드 — 다음 스프린트
      </div>
    </div>
  );
}
