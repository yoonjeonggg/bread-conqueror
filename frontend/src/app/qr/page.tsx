"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { ConquestResult } from "@/components/ConquestResult";
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

  // "done" always has a result; the guard just narrows the type.
  if (!result) return null;

  return (
    <ConquestResult
      result={result}
      flagType="GOLD"
      title="QR 정복 완료!"
      description="매장 QR로 골드 깃발을 꽂았습니다."
      storeHref={`/stores/${result.flag.store_id}`}
      storeLabel="매장 보기"
    />
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
