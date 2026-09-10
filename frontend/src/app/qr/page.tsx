"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ConquestResponse } from "@/lib/types";

function QrConquer() {
  const params = useSearchParams();
  const token = params.get("t");
  const router = useRouter();
  const { user, loading, refresh } = useAuth();

  const [state, setState] = useState<"idle" | "working" | "error" | "done">(
    "idle",
  );
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ConquestResponse | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      const back = token ? `/qr?t=${token}` : "/qr";
      router.replace(`/login?next=${encodeURIComponent(back)}`);
      return;
    }
    if (!token) {
      setState("error");
      setError("QR 토큰이 없습니다.");
      return;
    }
    if (ran.current) return;
    ran.current = true;
    setState("working");
    api
      .conquerByQr(token)
      .then(async (res) => {
        setResult(res);
        setState("done");
        await refresh();
      })
      .catch((e) => {
        setError(e instanceof ApiError ? e.message : "정복에 실패했습니다.");
        setState("error");
      });
  }, [loading, user, token, router, refresh]);

  if (state === "working" || state === "idle")
    return (
      <div className="page">
        <div className="card list-empty">QR 확인 중…</div>
      </div>
    );

  if (state === "error")
    return (
      <div className="page">
        <div className="card">
          <div className="page-title" style={{ fontSize: 18 }}>
            정복하지 못했습니다
          </div>
          <p className="error-text">{error}</p>
          <Link href="/map">
            <button className="btn btn-ghost" style={{ marginTop: 12 }}>
              지도로
            </button>
          </Link>
        </div>
      </div>
    );

  return (
    <div className="page">
      <div className="conquer-celebrate">
        <div className="flag">
          {result?.upgraded_from_silver ? "🥈➜🥇" : "🥇"}
        </div>
        <h2 style={{ margin: "12px 0 4px" }}>
          {result?.upgraded_from_silver ? "골드로 업그레이드!" : "QR 정복 완료!"}
        </h2>
        <p className="muted">매장 QR로 골드 깃발을 꽂았습니다.</p>
        <div className="hero" style={{ marginTop: 20, textAlign: "left" }}>
          <div className="big">+{result?.exp_granted} EXP</div>
          {result?.tier_changed && (
            <p style={{ color: "#f8e9d6", margin: "8px 0 0" }}>
              🎉 티어가 Lv.{result.new_tier_level}로 상승했습니다!
            </p>
          )}
        </div>
        <div style={{ marginTop: 20, display: "grid", gap: 10 }}>
          <Link href={`/stores/${result?.flag.store_id}`}>
            <button className="btn btn-secondary">매장 보기</button>
          </Link>
          <Link href="/profile">
            <button className="btn btn-ghost">내 깃발 보기</button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function QrPage() {
  return (
    <Suspense
      fallback={
        <div className="page">
          <div className="card list-empty">불러오는 중…</div>
        </div>
      }
    >
      <QrConquer />
    </Suspense>
  );
}
