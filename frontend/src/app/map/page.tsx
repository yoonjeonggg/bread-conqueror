"use client";

import { useEffect, useState } from "react";

import Link from "next/link";

import { Icon } from "@/components/Icon";
import { StoreCard } from "@/components/StoreCard";
import { DEFAULT_COORDS, useGeolocation, type Coords } from "@/components/useGeolocation";
import { api, ApiError } from "@/lib/api";
import type { Store } from "@/lib/types";

const RADII = [1000, 3000, 8000];

// Pixels from the board centre that the search radius maps to. One scale for
// both axes keeps north/south and east/west distances comparable; it fits the
// board's short side (286px tall, see .map-board).
const RADIUS_PX = 120;
// A pin is anchored at its tip (translate(-50%, -100%)) and is about 64×36px,
// so keep its anchor this far from each edge to stay fully on the board.
const PIN_HALF_W = 34;
const PIN_H = 40;
const EDGE = 4;

function pinPosition(center: Coords, store: Store, radius: number) {
  const dx = (store.lng - center.lng) * 111320 * Math.cos((center.lat * Math.PI) / 180);
  const dy = (store.lat - center.lat) * 110540;
  const x = (dx / radius) * RADIUS_PX;
  const y = (dy / radius) * RADIUS_PX;
  return {
    left: `clamp(${PIN_HALF_W}px, calc(50% + ${x.toFixed(1)}px), calc(100% - ${PIN_HALF_W}px))`,
    top: `clamp(${PIN_H}px, calc(50% - ${y.toFixed(1)}px), calc(100% - ${EDGE}px))`,
  };
}

export default function MapPage() {
  const { coords, error, loading, locate } = useGeolocation();
  const [stores, setStores] = useState<Store[]>([]);
  const [radius, setRadius] = useState(3000);
  const [status, setStatus] = useState<string | null>(null);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (!coords) return;
    // Drop the previous radius's stores so they are never drawn at the new
    // scale, and ignore responses that arrive after a newer request started.
    let current = true;
    setStatus(null);
    setStores([]);
    setFetching(true);
    api
      .nearbyStores(coords.lat, coords.lng, radius)
      .then((rows) => current && setStores(rows))
      .catch(
        (e) =>
          current &&
          setStatus(e instanceof ApiError ? e.message : "매장을 불러오지 못했습니다."),
      )
      .finally(() => current && setFetching(false));
    return () => {
      current = false;
    };
  }, [coords, radius]);

  const c = coords ?? DEFAULT_COORDS;

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">지도</div>
        <Link href="/search" className="link-accent">
          <Icon name="search" size={18} />
          검색
        </Link>
      </div>

      {/* Kakao Maps SDK drops in here — set NEXT_PUBLIC_KAKAO_MAP_KEY and
          render a <div id="kakao-map"/>. For now: pins placed by distance. */}
      <div className="map-board">
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 336 250"
          preserveAspectRatio="xMidYMid slice"
          aria-hidden="true"
          style={{ position: "absolute", inset: 0 }}
        >
          {[
            [10, 10, 70, 46], [92, 10, 60, 46], [164, 10, 80, 46], [256, 10, 70, 46],
            [10, 68, 50, 40], [72, 68, 90, 40], [246, 68, 80, 40],
            [10, 120, 80, 50], [102, 120, 56, 50], [170, 120, 76, 50], [258, 120, 68, 50],
            [10, 182, 60, 52], [82, 182, 82, 52], [176, 182, 70, 52], [258, 182, 68, 52],
          ].map(([x, y, w, h]) => (
            <rect key={`${x}-${y}`} x={x} y={y} width={w} height={h} rx="3" fill="#d9dfe8" />
          ))}
          <rect x="164" y="68" width="70" height="40" rx="3" fill="#d3e8dc" />
          <path
            d="M-10 112 C 60 100, 120 150, 200 112 S 320 96, 360 118"
            stroke="#c9dcec"
            strokeWidth="14"
            fill="none"
          />
        </svg>
        <span className="map-me" role="img" aria-label="내 위치" />
        {stores.map((s) => (
          <Link
            key={s.id}
            href={`/stores/${s.id}`}
            className={`map-pin${s.conquered_by_me ? " mine" : ""}`}
            style={pinPosition(c, s, radius)}
            aria-label={`${s.name} 골드 ${s.stat?.gold_flag_count ?? 0} 실버 ${s.stat?.silver_flag_count ?? 0}`}
          >
            <span className="map-pin-body">
              <span className="ii" style={{ gap: 3 }}>
                <i style={{ background: "var(--gold)" }} />
                {s.stat?.gold_flag_count ?? 0}
              </span>
              <span className="ii" style={{ gap: 3 }}>
                <i style={{ background: "var(--silver-pin)" }} />
                {s.stat?.silver_flag_count ?? 0}
              </span>
            </span>
            <span className="map-pin-tip" />
          </Link>
        ))}
        <button className="map-locate" onClick={locate} aria-label="내 위치로 이동">
          <Icon name="locate" size={20} strokeWidth={2.25} color="var(--ink)" />
        </button>
      </div>

      <div className="tabs" style={{ marginTop: 12 }}>
        {RADII.map((r) => (
          <button
            key={r}
            className={`tab${radius === r ? " on" : ""}`}
            onClick={() => setRadius(r)}
          >
            {r / 1000}km
          </button>
        ))}
      </div>
      <div className="muted" style={{ fontSize: 13, textAlign: "center", marginTop: 8 }}>
        {error ?? (
          <>
            반경 {radius / 1000}km 안의 베이커리{" "}
            <strong style={{ color: "var(--ink)" }}>
              {fetching ? "…" : `${stores.length}곳`}
            </strong>
          </>
        )}
      </div>

      <div className="row" style={{ justifyContent: "space-between", margin: "20px 0 10px" }}>
        <div className="section-title" style={{ margin: 0 }}>주변 베이커리</div>
        <Link href="/stores/new" className="link-accent">
          <Icon name="plus" size={16} />
          매장 등록
        </Link>
      </div>
      {loading && <div className="card list-empty">위치 확인 중…</div>}
      {!loading && fetching && <div className="card list-empty">불러오는 중…</div>}
      {status && <div className="card list-empty">{status}</div>}
      {!loading && !fetching && !status && stores.length === 0 && (
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
