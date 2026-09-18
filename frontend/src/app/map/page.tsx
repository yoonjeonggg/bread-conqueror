"use client";

import { useEffect, useRef, useState } from "react";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { StoreCard } from "@/components/StoreCard";
import { useGeolocation, DEFAULT_COORDS } from "@/components/useGeolocation";
import {
  useKakaoMaps,
  type KakaoCustomOverlay,
  type KakaoMap,
} from "@/components/useKakaoMap";
import { api, ApiError } from "@/lib/api";
import type { Store } from "@/lib/types";

const LEVEL_BY_RADIUS: Record<number, number> = {
  1000: 5,
  3000: 7,
  8000: 9,
};

function buildPinContent(store: Store): HTMLDivElement {
  const conquered = !!store.conquered_by_me;
  const color = conquered ? "#2f9e6b" : "#c68642";
  const gold = store.stat?.gold_flag_count ?? 0;
  const silver = store.stat?.silver_flag_count ?? 0;

  const wrap = document.createElement("div");
  wrap.dataset.storeId = String(store.id);
  wrap.style.cssText =
    "cursor:pointer;display:flex;flex-direction:column;align-items:center;transform:translateY(-100%);";

  const pill = document.createElement("div");
  pill.style.cssText = `background:${color};color:#fff;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:700;box-shadow:0 2px 8px rgba(43,33,24,0.3);white-space:nowrap;`;
  pill.textContent = `${conquered ? "✅ " : ""}🥇${gold} · 🥈${silver}`;

  const tip = document.createElement("div");
  tip.style.cssText = `width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid ${color};margin-top:-1px;`;

  wrap.appendChild(pill);
  wrap.appendChild(tip);
  return wrap;
}

export default function MapPage() {
  const router = useRouter();
  const { coords, error, loading, locate } = useGeolocation();
  const { maps, error: mapError } = useKakaoMaps();
  const [stores, setStores] = useState<Store[]>([]);
  const [radius, setRadius] = useState(3000);
  const [status, setStatus] = useState<string | null>(null);

  const mapDivRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<KakaoMap | null>(null);
  const overlaysRef = useRef<KakaoCustomOverlay[]>([]);

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

  // init map once the SDK + container are ready
  useEffect(() => {
    if (!maps || !mapDivRef.current || mapRef.current) return;
    mapRef.current = new maps.Map(mapDivRef.current, {
      center: new maps.LatLng(c.lat, c.lng),
      level: LEVEL_BY_RADIUS[radius] ?? 7,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maps]);

  // re-center when coords/radius change
  useEffect(() => {
    if (!maps || !mapRef.current) return;
    mapRef.current.setCenter(new maps.LatLng(c.lat, c.lng));
    mapRef.current.setLevel(LEVEL_BY_RADIUS[radius] ?? 7);
  }, [maps, c.lat, c.lng, radius]);

  // rebuild markers when the store list changes
  useEffect(() => {
    if (!maps || !mapRef.current) return;
    overlaysRef.current.forEach((o) => o.setMap(null));
    overlaysRef.current = stores.map((store) => {
      return new maps.CustomOverlay({
        position: new maps.LatLng(store.lat, store.lng),
        content: buildPinContent(store),
        yAnchor: 1,
      });
    });
    overlaysRef.current.forEach((o) => o.setMap(mapRef.current));
  }, [maps, stores]);

  // event delegation: Kakao clones overlay content nodes internally, so a
  // listener attached directly to a pin is silently dropped. data-store-id
  // survives the clone, so delegate from the (stable) map container instead.
  useEffect(() => {
    const el = mapDivRef.current;
    if (!el) return;
    const onClick = (e: MouseEvent) => {
      const pin = (e.target as HTMLElement).closest<HTMLElement>(
        "[data-store-id]",
      );
      if (pin?.dataset.storeId) router.push(`/stores/${pin.dataset.storeId}`);
    };
    el.addEventListener("click", onClick);
    return () => el.removeEventListener("click", onClick);
  }, [router]);

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🗺️ 지도</div>
        <div className="row" style={{ gap: 12 }}>
          <Link href="/search" className="link-accent">
            🔍 검색
          </Link>
          <button
            className="link-accent"
            onClick={locate}
            style={{ background: "none", border: "none", cursor: "pointer" }}
          >
            내 위치
          </button>
        </div>
      </div>

      {mapError ? (
        <div className="card list-empty">
          지도를 표시할 수 없습니다 ({mapError}). 아래 목록으로 확인하세요.
        </div>
      ) : (
        <div
          ref={mapDivRef}
          style={{
            width: "100%",
            height: 320,
            borderRadius: "var(--radius)",
            boxShadow: "var(--shadow)",
            background: "var(--warm-beige)",
          }}
        />
      )}

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
      <p className="muted" style={{ fontSize: 12, textAlign: "center", marginTop: 6 }}>
        {error ?? `반경 ${radius / 1000}km 안의 베이커리 ${stores.length}곳`}
      </p>

      <div className="row" style={{ justifyContent: "space-between", marginTop: 12 }}>
        <div className="section-title">주변 베이커리</div>
        <Link href="/stores/new" className="link-accent" style={{ fontSize: 13 }}>
          + 매장 등록
        </Link>
      </div>
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
