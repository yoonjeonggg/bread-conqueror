"use client";

import { useEffect, useRef, useState } from "react";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LoaderCircle, LocateFixed, Plus, Search } from "lucide-react";

import { StoreCard } from "@/components/StoreCard";
import { useGeolocation, DEFAULT_COORDS } from "@/components/useGeolocation";
import {
  useKakaoMaps,
  type KakaoCustomOverlay,
  type KakaoMap,
} from "@/components/useKakaoMap";
import { useNearbyStores } from "@/components/useNearbyStores";
import type { Store } from "@/lib/types";

const RADII = [1000, 3000, 8000] as const;

const LEVEL_BY_RADIUS: Record<number, number> = {
  1000: 5,
  3000: 7,
  8000: 9,
};

// pointer travel (px) beyond which a pointerdown→click is treated as a drag
const DRAG_TOLERANCE_PX = 6;

function levelForRadius(radius: number): number {
  return LEVEL_BY_RADIUS[radius] ?? 7;
}

// captures everything a pin renders, so unchanged stores can skip
// touching the DOM/overlay when the list is re-diffed
function pinSignature(store: Store): string {
  return [
    store.lat,
    store.lng,
    store.stat?.gold_flag_count ?? 0,
    store.stat?.silver_flag_count ?? 0,
    !!store.conquered_by_me,
  ].join("|");
}

// Pins are cloned from one parsed template and styled by class (.map-pin in
// globals.css). Benchmarked against inline-styled createElement and HTML-string
// content: all three cost the same (overlay creation dominates), so this one
// wins on keeping pin styling in CSS with the rest of the design tokens.
let pinTemplate: HTMLDivElement | null = null;

function buildPinContent(store: Store): HTMLDivElement {
  if (!pinTemplate) {
    pinTemplate = document.createElement("div");
    pinTemplate.className = "map-pin";
    // static markup only — store data is written via textContent/dataset below
    pinTemplate.innerHTML =
      '<div class="map-pin-body">' +
      '<span class="map-pin-count"><i class="map-pin-dot gold"></i><b></b></span>' +
      '<span class="map-pin-count"><i class="map-pin-dot silver"></i><b></b></span>' +
      "</div>" +
      '<div class="map-pin-tip"></div>';
  }
  const pin = pinTemplate.cloneNode(true) as HTMLDivElement;
  pin.dataset.storeId = String(store.id);
  if (store.conquered_by_me) pin.classList.add("mine");
  const [gold, silver] = pin.querySelectorAll("b");
  gold.textContent = String(store.stat?.gold_flag_count ?? 0);
  silver.textContent = String(store.stat?.silver_flag_count ?? 0);
  pin.title = store.name;
  return pin;
}

export default function MapPage() {
  const router = useRouter();
  const { coords, error, loading, locate } = useGeolocation();
  const { maps, error: mapError } = useKakaoMaps();
  const [radius, setRadius] = useState(3000);
  const { stores, fetching, error: status } = useNearbyStores(coords, radius);

  const mapDivRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<KakaoMap | null>(null);

  const c = coords ?? DEFAULT_COORDS;

  // init map once the SDK + container are ready
  useEffect(() => {
    if (!maps || !mapDivRef.current || mapRef.current) return;
    mapRef.current = new maps.Map(mapDivRef.current, {
      center: new maps.LatLng(c.lat, c.lng),
      level: levelForRadius(radius),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maps]);

  // re-center when coords/radius change
  useEffect(() => {
    if (!maps || !mapRef.current) return;
    mapRef.current.setCenter(new maps.LatLng(c.lat, c.lng));
    mapRef.current.setLevel(levelForRadius(radius));
  }, [maps, c.lat, c.lng, radius]);

  // reconcile markers against the previous batch instead of tearing every
  // pin down and rebuilding it: stores whose position/flags/conquest are
  // unchanged (the common case when toggling radius back and forth) keep
  // their existing overlay untouched, avoiding needless DOM churn.
  const overlaysRef = useRef(
    new Map<number, { overlay: KakaoCustomOverlay; sig: string }>(),
  );

  useEffect(() => {
    if (!maps || !mapRef.current) return;
    const map = mapRef.current;
    const live = overlaysRef.current;
    const seen = new Set<number>();

    for (const store of stores) {
      seen.add(store.id);
      const sig = pinSignature(store);
      const entry = live.get(store.id);
      if (!entry) {
        const overlay = new maps.CustomOverlay({
          position: new maps.LatLng(store.lat, store.lng),
          content: buildPinContent(store),
          yAnchor: 1,
        });
        overlay.setMap(map);
        live.set(store.id, { overlay, sig });
      } else if (entry.sig !== sig) {
        entry.overlay.setPosition(new maps.LatLng(store.lat, store.lng));
        entry.overlay.setContent(buildPinContent(store));
        entry.sig = sig;
      }
    }

    for (const [id, entry] of live) {
      if (!seen.has(id)) {
        entry.overlay.setMap(null);
        live.delete(id);
      }
    }
  }, [maps, stores]);

  // tear every remaining pin down on unmount only (reconciliation above
  // already removes pins for stores that drop out of the list)
  useEffect(() => {
    const overlays = overlaysRef.current;
    return () => {
      overlays.forEach(({ overlay }) => overlay.setMap(null));
      overlays.clear();
    };
  }, []);

  // event delegation: Kakao clones overlay content nodes internally, so a
  // listener attached directly to a pin is silently dropped. data-store-id
  // survives the clone, so delegate from the (stable) map container instead.
  // A drag that starts on a pin also ends on it (the pin moves with the map),
  // so a click after the pointer travelled more than a few px is ignored.
  useEffect(() => {
    const el = mapDivRef.current;
    if (!el) return;
    let downX = 0;
    let downY = 0;
    const onDown = (e: PointerEvent) => {
      downX = e.clientX;
      downY = e.clientY;
    };
    const onClick = (e: MouseEvent) => {
      if (Math.hypot(e.clientX - downX, e.clientY - downY) > DRAG_TOLERANCE_PX) {
        return;
      }
      const pin = (e.target as HTMLElement).closest<HTMLElement>(
        "[data-store-id]",
      );
      const id = pin?.dataset.storeId;
      // only ever navigate to a numeric store route, whatever ends up in the DOM
      if (id && /^\d+$/.test(id)) router.push(`/stores/${id}`);
    };
    el.addEventListener("pointerdown", onDown, true);
    el.addEventListener("click", onClick);
    return () => {
      el.removeEventListener("pointerdown", onDown, true);
      el.removeEventListener("click", onClick);
    };
  }, [router]);

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">지도</div>
        <Link href="/search" className="link-accent" aria-label="매장 검색">
          <Search size={18} strokeWidth={2.5} />
          검색
        </Link>
      </div>

      {mapError ? (
        <div className="card list-empty">
          지도를 표시할 수 없습니다 ({mapError}). 아래 목록으로 확인하세요.
        </div>
      ) : (
        <div className="map-frame">
          <div ref={mapDivRef} className="map-canvas" />
          {fetching && (
            <span className="badge badge-dark map-loading">
              <LoaderCircle size={12} className="spin" />
              불러오는 중
            </span>
          )}
          <button
            className="map-locate"
            onClick={locate}
            aria-label="내 위치로 이동"
          >
            <LocateFixed size={20} strokeWidth={2.25} />
          </button>
        </div>
      )}

      <div className="tabs" style={{ marginTop: 12 }}>
        {RADII.map((r) => (
          <button
            key={r}
            className={`tab ${radius === r ? "active" : ""}`}
            onClick={() => setRadius(r)}
          >
            {r / 1000}km
          </button>
        ))}
      </div>
      <p
        className="muted"
        style={{ fontSize: 13, textAlign: "center", margin: "8px 0 0" }}
      >
        {error ?? (
          <>
            반경 {radius / 1000}km 안의 베이커리{" "}
            <strong style={{ color: "var(--ink)" }}>{stores.length}곳</strong>
          </>
        )}
      </p>

      <div
        className="row"
        style={{ justifyContent: "space-between", margin: "26px 0 10px" }}
      >
        <div className="section-title" style={{ margin: 0 }}>
          주변 베이커리
        </div>
        <Link href="/stores/new" className="link-accent" style={{ fontSize: 14 }}>
          <Plus size={16} strokeWidth={2.5} />
          매장 등록
        </Link>
      </div>
      {loading && <div className="card list-empty">위치 확인 중…</div>}
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
