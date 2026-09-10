"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AdminClaim } from "@/lib/types";

type Dashboard = Awaited<ReturnType<typeof api.adminDashboard>>;
type Report = Awaited<ReturnType<typeof api.adminReports>>[number];
type CsvResult = Awaited<ReturnType<typeof api.bulkUploadStores>>;

export default function AdminPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [claims, setClaims] = useState<AdminClaim[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [mergeTarget, setMergeTarget] = useState("");
  const [mergeSource, setMergeSource] = useState("");
  const [mergeMsg, setMergeMsg] = useState<string | null>(null);
  const [merging, setMerging] = useState(false);
  const [csvText, setCsvText] = useState("");
  const [csvName, setCsvName] = useState<string | null>(null);
  const [csvResult, setCsvResult] = useState<CsvResult | null>(null);
  const [csvBusy, setCsvBusy] = useState(false);
  const [csvErr, setCsvErr] = useState<string | null>(null);

  const runCsv = async (dryRun: boolean) => {
    setCsvErr(null);
    setCsvResult(null);
    setCsvBusy(true);
    try {
      setCsvResult(await api.bulkUploadStores(csvText, dryRun));
    } catch (e) {
      setCsvErr(e instanceof Error ? e.message : "업로드에 실패했습니다.");
    } finally {
      setCsvBusy(false);
    }
  };

  const loadReports = () =>
    api.adminReports().then(setReports).catch(() => setReports([]));

  const loadClaims = () =>
    api.adminClaims().then(setClaims).catch(() => setClaims([]));

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
      loadClaims();
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
        ["소유권 신청", data.pending_claims],
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

      <div className="section-title">매장 소유권 신청 ({claims.length})</div>
      {claims.length === 0 ? (
        <div className="card list-empty">대기 중인 신청이 없습니다.</div>
      ) : (
        claims.map((c) => (
          <div key={c.id} className="card">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="badge badge-gold">{c.store_name}</span>
              <span className="muted" style={{ fontSize: 11 }}>
                {new Date(c.created_at).toLocaleDateString("ko-KR")}
              </span>
            </div>
            <p style={{ fontSize: 13, margin: "8px 0 4px" }}>
              신청자 <strong>{c.user_nickname}</strong> · {c.contact_phone}
            </p>
            <a
              href={c.business_license_image_url}
              target="_blank"
              rel="noreferrer"
              className="link-accent"
              style={{ fontSize: 12 }}
            >
              사업자등록증 보기 ↗
            </a>
            <div className="row" style={{ gap: 8, marginTop: 10 }}>
              <button
                className="btn btn-ghost"
                style={{ width: "auto", padding: "8px 12px" }}
                onClick={async () => {
                  await api.reviewClaim(c.id, true, "서류 확인 완료");
                  loadClaims();
                  api.adminDashboard().then(setData).catch(() => {});
                }}
              >
                승인
              </button>
              <button
                className="btn btn-ghost"
                style={{ width: "auto", padding: "8px 12px" }}
                onClick={async () => {
                  await api.reviewClaim(c.id, false, "서류 미비");
                  loadClaims();
                  api.adminDashboard().then(setData).catch(() => {});
                }}
              >
                반려
              </button>
            </div>
          </div>
        ))
      )}

      <div className="section-title">매장 CSV 대량 등록 (F-ADMIN-05)</div>
      <div className="card">
        <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
          헤더: <code>name,address,region_sido,lat,lng,category</code> (name·address·lat·lng
          필수). 반경 30m 내 기존/직전 행과 겹치면 자동 스킵됩니다.
        </p>
        <label
          className="btn btn-ghost"
          style={{ cursor: "pointer", marginBottom: 8 }}
        >
          {csvName ? `📄 ${csvName}` : "📄 CSV 파일 선택"}
          <input
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              setCsvName(f.name);
              setCsvResult(null);
              setCsvErr(null);
              f.text().then(setCsvText);
            }}
          />
        </label>
        {csvErr && <p className="error-text">{csvErr}</p>}
        <div className="row" style={{ gap: 8 }}>
          <button
            className="btn btn-ghost"
            style={{ width: "auto", padding: "8px 12px" }}
            disabled={csvBusy || !csvText}
            onClick={() => runCsv(true)}
          >
            미리보기
          </button>
          <button
            className="btn btn-secondary"
            style={{ width: "auto", padding: "8px 12px" }}
            disabled={csvBusy || !csvText}
            onClick={() => runCsv(false)}
          >
            {csvBusy ? "처리 중…" : "등록 실행"}
          </button>
        </div>

        {csvResult && (
          <div style={{ marginTop: 12 }}>
            <p style={{ fontSize: 13, fontWeight: 700 }}>
              {csvResult.dry_run ? "미리보기" : "등록 완료"} · 총 {csvResult.total} —
              생성 {csvResult.created} / 스킵 {csvResult.skipped_duplicate} / 실패{" "}
              {csvResult.failed}
            </p>
            <div style={{ maxHeight: 220, overflowY: "auto", fontSize: 12 }}>
              {csvResult.rows.map((r) => (
                <div
                  key={r.line}
                  className="row"
                  style={{ justifyContent: "space-between", padding: "3px 0" }}
                >
                  <span>
                    {r.line}행 {r.name}
                  </span>
                  <span
                    className={`badge ${
                      r.status === "created"
                        ? "badge-verified"
                        : r.status === "skipped"
                          ? "badge-silver"
                          : "badge-gold"
                    }`}
                  >
                    {r.status}
                    {r.detail ? ` · ${r.detail}` : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="section-title">중복 매장 병합 (F-ADMIN-04)</div>
      <div className="card">
        <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
          <strong>병합 대상(target)</strong>에 <strong>원본(source)</strong>의 깃발·리뷰·게시글·QR·
          소유권 신청을 모두 이관하고, 원본은 폐점 처리합니다. 되돌릴 수 없습니다.
        </p>
        <div className="row" style={{ gap: 10 }}>
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="mt">대상 매장 ID (남길 쪽)</label>
            <input
              id="mt"
              value={mergeTarget}
              inputMode="numeric"
              onChange={(e) => setMergeTarget(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="ms">원본 매장 ID (폐점될 쪽)</label>
            <input
              id="ms"
              value={mergeSource}
              inputMode="numeric"
              onChange={(e) => setMergeSource(e.target.value.replace(/\D/g, ""))}
            />
          </div>
        </div>
        {mergeMsg && (
          <p
            style={{ fontSize: 13, margin: "4px 0 8px" }}
            className={mergeMsg.startsWith("✅") ? "link-accent" : "error-text"}
          >
            {mergeMsg}
          </p>
        )}
        <button
          className="btn btn-ghost"
          disabled={merging || !mergeTarget || !mergeSource}
          onClick={async () => {
            setMergeMsg(null);
            setMerging(true);
            try {
              const res = await api.mergeStores(
                Number(mergeTarget),
                Number(mergeSource),
              );
              setMergeMsg(
                `✅ 병합 완료 — 깃발 ${res.moved_flags}, 리뷰 ${res.moved_reviews}` +
                  ` (중복 ${res.dropped_duplicate_reviews} 폐기), 게시글 ${res.moved_posts}` +
                  (res.owner_inherited ? ", 소유자 승계됨" : ""),
              );
              setMergeSource("");
              api.adminDashboard().then(setData).catch(() => {});
            } catch (e) {
              setMergeMsg(
                e instanceof Error ? e.message : "병합에 실패했습니다.",
              );
            } finally {
              setMerging(false);
            }
          }}
        >
          {merging ? "병합 중…" : "병합 실행"}
        </button>
      </div>

      <div className="section-title">운영 메뉴 (API)</div>
      <div className="card muted" style={{ fontSize: 13, lineHeight: 1.7 }}>
        · 깃발 검토 큐 <code>GET /admin/flags/review-queue</code>
        <br />· 계정 정지/해제 <code>POST /admin/users/&#123;id&#125;/suspend</code>
        <br />· 경험치 조정 <code>POST /admin/users/&#123;id&#125;/adjust-exp</code>
        <br />· 콘텐츠 모더레이션 <code>POST /admin/posts/&#123;id&#125;/moderate</code>
        <br />· 소유권 신청 승인 <code>POST /admin/claims/&#123;id&#125;/approve</code>
        <br />· 매장 CSV 대량 등록 <code>POST /admin/stores/bulk-upload</code>
      </div>
    </div>
  );
}
