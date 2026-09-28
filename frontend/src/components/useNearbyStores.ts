"use client";

import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { Store } from "@/lib/types";
import type { Coords } from "./useGeolocation";

export const NEARBY_LIMIT = 100;

interface CacheEntry {
  radius: number;
  stores: Store[];
}

// The API returns stores sorted by distance, so a result for radius R already
// contains every store within any r < R — as long as it wasn't cut off by the
// limit before reaching r. Deriving from it keeps the Store objects identical,
// which lets memoized cards and unchanged map pins skip re-rendering.
function deriveFrom(entries: CacheEntry[], radius: number): Store[] | null {
  for (const e of entries) {
    if (e.radius === radius) return e.stores;
  }
  for (const e of entries) {
    if (e.radius < radius) continue;
    const truncated = e.stores.length >= NEARBY_LIMIT;
    const last = e.stores[e.stores.length - 1]?.distance_m ?? 0;
    if (!truncated || last >= radius) {
      return e.stores.filter((s) => (s.distance_m ?? 0) <= radius);
    }
  }
  return null;
}

function coordsKey(c: Coords): string {
  return `${c.lat.toFixed(5)},${c.lng.toFixed(5)}`;
}

export function useNearbyStores(coords: Coords | null, radius: number) {
  const [stores, setStores] = useState<Store[]>([]);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // scoped to the mounted page: leaving the map and coming back refetches, so
  // a fresh conquest shows up without any explicit invalidation.
  const cacheRef = useRef(new Map<string, CacheEntry[]>());

  useEffect(() => {
    if (!coords) return;
    const key = coordsKey(coords);
    const entries = cacheRef.current.get(key) ?? [];
    const cached = deriveFrom(entries, radius);
    setError(null);
    if (cached) {
      setStores(cached);
      setFetching(false);
      return;
    }

    const controller = new AbortController();
    setFetching(true);
    api
      .nearbyStores(coords.lat, coords.lng, radius, controller.signal, NEARBY_LIMIT)
      .then((data) => {
        cacheRef.current.set(key, [...entries, { radius, stores: data }]);
        setStores(data);
      })
      .catch((e) => {
        if (controller.signal.aborted) return;
        setError(e instanceof ApiError ? e.message : "매장을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setFetching(false);
      });
    // aborts the request itself (not just its result) when radius/coords
    // change again before it resolves
    return () => controller.abort();
  }, [coords, radius]);

  return { stores, fetching, error };
}
