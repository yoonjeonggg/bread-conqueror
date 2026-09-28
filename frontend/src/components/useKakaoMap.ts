"use client";

import { useEffect, useState } from "react";

export type KakaoLatLng = { getLat(): number; getLng(): number };

export interface KakaoMap {
  setCenter(latlng: KakaoLatLng): void;
  setLevel(level: number): void;
}

export interface KakaoCustomOverlay {
  setMap(map: KakaoMap | null): void;
  setPosition(latlng: KakaoLatLng): void;
  setContent(content: HTMLElement | string): void;
}

interface KakaoMapsNS {
  LatLng: new (lat: number, lng: number) => KakaoLatLng;
  Map: new (
    container: HTMLElement,
    options: { center: KakaoLatLng; level: number },
  ) => KakaoMap;
  CustomOverlay: new (options: {
    position: KakaoLatLng;
    content: HTMLElement | string;
    map?: KakaoMap;
    yAnchor?: number;
    zIndex?: number;
  }) => KakaoCustomOverlay;
  load(callback: () => void): void;
}

declare global {
  interface Window {
    kakao?: { maps: KakaoMapsNS };
  }
}

const SCRIPT_ID = "kakao-maps-sdk";

let loadPromise: Promise<KakaoMapsNS> | null = null;

function loadKakaoMaps(appKey: string): Promise<KakaoMapsNS> {
  if (loadPromise) return loadPromise;
  loadPromise = new Promise((resolve, reject) => {
    const existing = document.getElementById(
      SCRIPT_ID,
    ) as HTMLScriptElement | null;
    const onReady = () => {
      if (!window.kakao) {
        reject(new Error("카카오맵 SDK 로드에 실패했습니다."));
        return;
      }
      window.kakao.maps.load(() => resolve(window.kakao!.maps));
    };
    if (existing) {
      if (window.kakao) onReady();
      else existing.addEventListener("load", onReady);
      return;
    }
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    // explicit https (a protocol-relative URL would follow the page's scheme)
    // and an encoded key so a malformed env value can't inject extra params
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appKey)}&autoload=false`;
    script.async = true;
    script.onload = onReady;
    script.onerror = () =>
      reject(new Error("카카오맵 SDK 스크립트를 불러오지 못했습니다."));
    document.head.appendChild(script);
  });
  return loadPromise;
}

export function useKakaoMaps(): {
  maps: KakaoMapsNS | null;
  error: string | null;
} {
  const [maps, setMaps] = useState<KakaoMapsNS | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const appKey = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY;
    if (!appKey) {
      setError("지도 API 키가 설정되지 않았습니다.");
      return;
    }
    loadKakaoMaps(appKey)
      .then(setMaps)
      .catch((e) => setError(e instanceof Error ? e.message : "지도를 불러오지 못했습니다."));
  }, []);

  return { maps, error };
}
