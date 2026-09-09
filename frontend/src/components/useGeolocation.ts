"use client";

import { useCallback, useEffect, useState } from "react";

export interface Coords {
  lat: number;
  lng: number;
}

// Seoul City Hall — fallback when geolocation is denied/unavailable.
export const DEFAULT_COORDS: Coords = { lat: 37.5663, lng: 126.9779 };

export function useGeolocation(auto = true) {
  const [coords, setCoords] = useState<Coords | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const locate = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setError("이 브라우저는 위치 서비스를 지원하지 않습니다.");
      setCoords(DEFAULT_COORDS);
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setError(null);
        setLoading(false);
      },
      () => {
        setError("위치 권한이 없어 기본 위치(서울시청)로 표시합니다.");
        setCoords(DEFAULT_COORDS);
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }, []);

  useEffect(() => {
    if (auto) locate();
  }, [auto, locate]);

  return { coords, error, loading, locate };
}
