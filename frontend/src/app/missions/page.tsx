"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { WeeklyMission } from "@/lib/types";

export default function MissionsPage() {
  const router = useRouter();
  const { user, loading, refresh } = useAuth();
  const [missions, setMissions] = useState<WeeklyMission[]>([]);
  const [weekStart, setWeekStart] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .weeklyMissions()
      .then((r) => {
        setMissions(r.missions);
        setWeekStart(r.week_start);
      })
      .catch(() => setMissions([]))
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    if (!loading && !user) router.replace("/login?next=/missions");
  }, [loading, user, router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  async function claim(code: string) {
    setBusy(code);
    setToast(null);
    try {
      const res = await api.claimMission(code);
      setToast(
        `+${res.reward_exp} EXP` +
          (res.tier_changed ? ` · 티어 Lv.${res.tier_level} 달성!` : ""),
      );
      await refresh();
      load();
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "수령에 실패했습니다.");
    } finally {
      setBusy(null);
    }
  }

  if (!user) return null;

  const claimable = missions.filter((m) => m.completed && !m.claimed).length;

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🎯 이번 주 미션</div>
        <Link href="/profile" className="link-accent">
          내 정보
        </Link>
      </div>

      <div className="card muted" style={{ fontSize: 13 }}>
        {weekStart && `${weekStart} 주간`} · 매주 월요일 초기화. 완료한 미션의
        보상은 직접 수령해야 EXP가 들어옵니다.
        {claimable > 0 && (
          <strong style={{ color: "var(--orange)" }}>
            {" "}
            받을 보상 {claimable}개!
          </strong>
        )}
      </div>

      {!ready ? (
        <div className="card list-empty">불러오는 중…</div>
      ) : missions.length === 0 ? (
        <div className="card list-empty">등록된 미션이 없습니다.</div>
      ) : (
        missions.map((m) => {
          const pct = Math.min(100, Math.round((m.progress / m.target) * 100));
          return (
            <div key={m.code} className="card">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong style={{ fontSize: 15 }}>{m.title}</strong>
                <span className="badge badge-gold">+{m.reward_exp} EXP</span>
              </div>
              <p className="muted" style={{ fontSize: 13, margin: "4px 0 10px" }}>
                {m.description}
              </p>
              <div className="mission-bar">
                <div className="mission-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              <div
                className="row"
                style={{ justifyContent: "space-between", marginTop: 8 }}
              >
                <span className="muted" style={{ fontSize: 12 }}>
                  {m.progress} / {m.target}
                </span>
                {m.claimed ? (
                  <span className="badge badge-verified">수령 완료</span>
                ) : m.completed ? (
                  <button
                    className="btn btn-primary"
                    style={{ width: "auto", padding: "6px 14px" }}
                    disabled={busy === m.code}
                    onClick={() => claim(m.code)}
                  >
                    {busy === m.code ? "…" : "보상 받기"}
                  </button>
                ) : (
                  <span className="badge badge-silver">진행 중</span>
                )}
              </div>
            </div>
          );
        })
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
