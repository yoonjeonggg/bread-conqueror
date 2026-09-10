"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Store } from "@/lib/types";

export default function StoreClaimPage() {
  const params = useParams<{ id: string }>();
  const storeId = Number(params.id);
  const router = useRouter();
  const { user, loading } = useAuth();

  const [store, setStore] = useState<Store | null>(null);
  const [licenseUrl, setLicenseUrl] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    api.store(storeId).then(setStore).catch(() => setStore(null));
  }, [storeId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.createClaim(storeId, {
        business_license_image_url: licenseUrl.trim(),
        contact_phone: phone.trim(),
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "신청에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  if (done)
    return (
      <div className="page">
        <div className="card">
          <div className="page-title" style={{ fontSize: 18 }}>
            신청이 접수되었습니다
          </div>
          <p className="muted" style={{ fontSize: 14, marginTop: 8 }}>
            관리자가 사업자등록증을 확인한 뒤 소유권을 인증합니다. 진행 상황은
            프로필에서 확인할 수 있어요.
          </p>
          <div style={{ marginTop: 16, display: "grid", gap: 10 }}>
            <Link href="/profile">
              <button className="btn btn-secondary">내 신청 현황</button>
            </Link>
            <Link href={`/stores/${storeId}`}>
              <button className="btn btn-ghost">매장으로 돌아가기</button>
            </Link>
          </div>
        </div>
      </div>
    );

  return (
    <div className="page">
      <div className="page-header">
        <Link href={`/stores/${storeId}`} className="link-accent">
          ← 매장
        </Link>
        <div className="page-title" style={{ fontSize: 18 }}>
          매장 소유권 신청
        </div>
      </div>

      {store?.owner_id != null ? (
        <div className="card list-empty">
          이미 인증된 소유자가 있는 매장입니다.
        </div>
      ) : (
        <>
          <div className="card muted" style={{ fontSize: 13 }}>
            <strong>{store?.name}</strong>의 실제 사장님이신가요? 사업자등록증
            이미지와 연락처를 제출하면 관리자 확인 후 매장 소유자로 인증됩니다.
            인증되면 정복용 QR을 발급할 수 있어요.
          </div>

          <form onSubmit={submit} className="card" style={{ marginTop: 12 }}>
            <div className="field">
              <label htmlFor="license">사업자등록증 이미지 URL</label>
              <input
                id="license"
                value={licenseUrl}
                maxLength={500}
                placeholder="https://..."
                onChange={(e) => setLicenseUrl(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="phone">연락처</label>
              <input
                id="phone"
                value={phone}
                maxLength={20}
                inputMode="tel"
                placeholder="010-1234-5678"
                pattern="[0-9+\-]+"
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>

            {error && <p className="error-text">{error}</p>}
            <button
              className="btn btn-primary"
              style={{ marginTop: 12 }}
              disabled={busy}
            >
              {busy ? "제출 중…" : "소유권 신청 제출"}
            </button>
          </form>
        </>
      )}
    </div>
  );
}
