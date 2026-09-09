"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useGeolocation } from "@/components/useGeolocation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function NewStorePage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { coords, locate } = useGeolocation();

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [category, setCategory] = useState("베이커리");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!loading && !user) {
    router.replace("/login");
    return null;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!coords) {
      setError("위치를 확인할 수 없습니다. 매장 앞에서 등록해 주세요.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const store = await api.createStore({
        name: name.trim(),
        address: address.trim(),
        lat: coords.lat,
        lng: coords.lng,
        category: category.trim() || undefined,
      });
      router.replace(`/stores/${store.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "등록에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <Link href="/map" className="link-accent">
          ← 지도
        </Link>
        <div className="page-title" style={{ fontSize: 18 }}>
          신규 매장 등록
        </div>
      </div>

      <div className="card muted" style={{ fontSize: 13 }}>
        지도에 없는 골목 빵집을 직접 추가합니다. 현재 GPS 좌표로 등록되며,
        반경 30m 내 중복 매장은 자동으로 걸러집니다. 등록된 매장은 관리자
        검토 후 노출됩니다.
      </div>

      <form onSubmit={submit} className="card" style={{ marginTop: 12 }}>
        <div className="field">
          <label htmlFor="name">매장명</label>
          <input
            id="name"
            value={name}
            maxLength={100}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="address">주소</label>
          <input
            id="address"
            value={address}
            maxLength={255}
            onChange={(e) => setAddress(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="category">카테고리</label>
          <input
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </div>

        <div
          className="row"
          style={{ justifyContent: "space-between", fontSize: 12 }}
        >
          <span className="muted">
            📍{" "}
            {coords
              ? `${coords.lat.toFixed(5)}, ${coords.lng.toFixed(5)}`
              : "위치 확인 중…"}
          </span>
          <button
            type="button"
            onClick={locate}
            className="link-accent"
            style={{ background: "none", border: "none", cursor: "pointer" }}
          >
            위치 새로고침
          </button>
        </div>

        {error && <p className="error-text">{error}</p>}
        <button
          className="btn btn-primary"
          style={{ marginTop: 12 }}
          disabled={busy || !coords}
        >
          {busy ? "등록 중…" : "이 위치로 매장 등록"}
        </button>
      </form>
    </div>
  );
}
