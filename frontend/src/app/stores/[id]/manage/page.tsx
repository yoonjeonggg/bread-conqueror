"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { QrToken, Store } from "@/lib/types";

function conquestUrl(token: string): string {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/qr?t=${token}`;
}

export default function StoreManagePage() {
  const params = useParams<{ id: string }>();
  const storeId = Number(params.id);
  const router = useRouter();
  const { user, loading } = useAuth();

  const [store, setStore] = useState<Store | null>(null);
  const [tokens, setTokens] = useState<QrToken[]>([]);
  const [label, setLabel] = useState("");
  const [maxUses, setMaxUses] = useState("");
  const [expiresHours, setExpiresHours] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);

  const load = useCallback(() => {
    api.storeQrTokens(storeId).then(setTokens).catch(() => setTokens([]));
  }, [storeId]);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    api.store(storeId).then(setStore).catch(() => setStore(null));
  }, [storeId]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const notOwner =
    store != null && user != null && store.owner_id !== user.id;

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.createQrToken(storeId, {
        label: label.trim() || null,
        max_uses: maxUses ? Number(maxUses) : null,
        expires_in_hours: expiresHours ? Number(expiresHours) : null,
      });
      setLabel("");
      setMaxUses("");
      setExpiresHours("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "발급에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(tokenId: number) {
    await api.revokeQrToken(storeId, tokenId).catch(() => {});
    load();
  }

  async function copy(t: QrToken) {
    try {
      await navigator.clipboard.writeText(conquestUrl(t.token));
      setCopied(t.id);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  if (!user) return null;

  return (
    <div className="page">
      <div className="page-header">
        <Link href={`/stores/${storeId}`} className="link-accent">
          ← 매장
        </Link>
        <div className="page-title" style={{ fontSize: 18 }}>
          매장 관리 · QR
        </div>
      </div>

      {notOwner ? (
        <div className="card list-empty">
          이 매장의 인증된 소유자만 접근할 수 있습니다.
        </div>
      ) : (
        <>
          <div className="card muted" style={{ fontSize: 13 }}>
            <strong>{store?.name}</strong> — 손님이 이 QR을 스캔하면 GPS 없이도
            골드 깃발을 꽂을 수 있습니다. 매장에 인쇄해 비치하세요. 사용 한도나
            만료를 지정하면 이벤트용으로도 쓸 수 있어요.
          </div>

          <form onSubmit={create} className="card" style={{ marginTop: 12 }}>
            <div className="field">
              <label htmlFor="label">라벨 (선택)</label>
              <input
                id="label"
                value={label}
                maxLength={50}
                placeholder="예: 카운터, 6월 이벤트"
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>
            <div className="row" style={{ gap: 10 }}>
              <div className="field" style={{ flex: 1 }}>
                <label htmlFor="max">최대 사용 횟수</label>
                <input
                  id="max"
                  value={maxUses}
                  inputMode="numeric"
                  placeholder="무제한"
                  onChange={(e) =>
                    setMaxUses(e.target.value.replace(/\D/g, ""))
                  }
                />
              </div>
              <div className="field" style={{ flex: 1 }}>
                <label htmlFor="exp">만료 (시간)</label>
                <input
                  id="exp"
                  value={expiresHours}
                  inputMode="numeric"
                  placeholder="무제한"
                  onChange={(e) =>
                    setExpiresHours(e.target.value.replace(/\D/g, ""))
                  }
                />
              </div>
            </div>
            {error && <p className="error-text">{error}</p>}
            <button
              className="btn btn-primary"
              style={{ marginTop: 12 }}
              disabled={busy}
            >
              {busy ? "발급 중…" : "QR 토큰 발급"}
            </button>
          </form>

          <div className="section-title">발급된 토큰 ({tokens.length})</div>
          {tokens.length === 0 ? (
            <div className="card list-empty">아직 발급된 QR이 없습니다.</div>
          ) : (
            tokens.map((t) => (
              <div key={t.id} className="card">
                <div
                  className="row"
                  style={{ justifyContent: "space-between" }}
                >
                  <span
                    className={`badge ${t.active ? "badge-gold" : "badge-silver"}`}
                  >
                    {t.active ? "사용 가능" : "만료/폐기"}
                  </span>
                  <span className="muted" style={{ fontSize: 11 }}>
                    {t.label || "라벨 없음"}
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 12,
                    wordBreak: "break-all",
                    margin: "8px 0",
                    fontFamily: "monospace",
                  }}
                >
                  {conquestUrl(t.token)}
                </p>
                <div className="muted" style={{ fontSize: 12 }}>
                  사용 {t.use_count}
                  {t.max_uses != null ? ` / ${t.max_uses}` : ""} 회
                  {t.expires_at
                    ? ` · 만료 ${new Date(t.expires_at).toLocaleString("ko-KR")}`
                    : ""}
                </div>
                <div className="row" style={{ gap: 8, marginTop: 8 }}>
                  <button
                    className="btn btn-ghost"
                    style={{ width: "auto", padding: "8px 12px" }}
                    onClick={() => copy(t)}
                  >
                    {copied === t.id ? "복사됨" : "링크 복사"}
                  </button>
                  {t.revoked_at == null && (
                    <button
                      className="btn btn-ghost"
                      style={{ width: "auto", padding: "8px 12px" }}
                      onClick={() => revoke(t.id)}
                    >
                      폐기
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </>
      )}
    </div>
  );
}
