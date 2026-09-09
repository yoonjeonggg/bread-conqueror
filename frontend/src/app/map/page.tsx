"use client";

import { useEffect, useState } from "react";

import { StoreCard } from "@/components/StoreCard";
import { DEFAULT_COORDS, useGeolocation } from "@/components/useGeolocation";
import { api, ApiError } from "@/lib/api";
import type { Store } from "@/lib/types";

export default function MapPage() {
  const { coords, error, loading, locate } = useGeolocation();
  const [stores, setStores] = useState<Store[]>([]);
  const [radius, setRadius] = useState(3000);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!coords) return;
    setStatus(null);
    api
      .nearbyStores(coords.lat, coords.lng, radius)
      .then(setStores)
      .catch((e) =>
        setStatus(e instanceof ApiError ? e.message : "매장을 불러오지 못했습니다."),
      );
  }, [coords, radius]);

  const c = coords ?? DEFAULT_COORDS;

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🗺️ 지도</div>
        <button
          className="link-accent"
          onClick={locate}
          style={{ background: "none", border: "none", cursor: "pointer" }}
        >
          내 위치 새로고침
        </button>
      </div>

      {/* Kakao Maps SDK drops in here — set NEXT_PUBLIC_KAKAO_MAP_KEY and
          render a <div id="kakao-map"/>. For now: a location-aware list. */}
      <div
        className="card"
        style={{
          background:
            "linear-gradient(135deg,#f8f1e5,#efe2ca)",
          textAlign: "center",
          padding: "26px 16px",
        }}
      >
        <div style={{ fontSize: 30 }}>📍</div>
        <div style={{ fontWeight: 700, marginTop: 4 }}>
          현재 위치 {c.lat.toFixed(4)}, {c.lng.toFixed(4)}
        </div>
        <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          {error ?? `반경 ${radius / 1000}km 안의 베이커리 ${stores.length}곳`}
        </div>
        <div className="pill-row" style={{ justifyContent: "center", marginTop: 12 }}>
          {[1000, 3000, 8000].map((r) => (
            <button
              key={r}
              className={`badge ${radius === r ? "badge-gold" : "badge-silver"}`}
              style={{ border: "none", cursor: "pointer" }}
              onClick={() => setRadius(r)}
            >
              {r / 1000}km
            </button>
          ))}
        </div>
      </div>

      <div className="section-title">주변 베이커리</div>
      {loading && <div className="card list-empty">위치 확인 중…</div>}
      {status && <div className="card list-empty">{status}</div>}
      {!loading && !status && stores.length === 0 && (
        <div className="card list-empty">
          이 반경에는 등록된 빵집이 없습니다.
        </div>
      )}
      {stores.map((s) => (
        <StoreCard key={s.id} store={s} />
      ))}
    </div>
  );
}
