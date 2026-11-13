"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BackLink } from "@/components/BackLink";
import { FlagIcon } from "@/components/badges";
import { ConquestResult } from "@/components/ConquestResult";
import { Icon } from "@/components/Icon";
import { useGeolocation } from "@/components/useGeolocation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDistance, formatShortDate, haversineM } from "@/lib/format";
import type { ConquestResponse, Store } from "@/lib/types";

type Mode = "GOLD" | "SILVER";

// 골드 인증 반경 기본값 (서버 정책 CONQUEST_RADIUS_M). 화면 안내용이며
// 실제 판정은 서버가 한다.
const NEAR_M = 50;

const EXIF_LABEL = {
  HIGH: "촬영 정보 확인됨",
  MEDIUM: "촬영 정보 일부 확인",
  LOW: "촬영 정보 없음",
} as const;

export default function ConquerPage() {
  const params = useParams<{ storeId: string }>();
  const storeId = Number(params.storeId);
  const router = useRouter();
  const { user, loading, refresh } = useAuth();
  const { coords, error: geoError } = useGeolocation();

  const [store, setStore] = useState<Store | null>(null);
  const [mode, setMode] = useState<Mode>("GOLD");
  const [photoName, setPhotoName] = useState<string | null>(null);
  const [exif, setExif] = useState<{
    trust: "HIGH" | "MEDIUM" | "LOW";
    captured_at: string | null;
    has_gps: boolean;
  } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ConquestResponse | null>(null);

  async function onPhoto(file: File | undefined) {
    setExif(null);
    setPhotoName(file?.name ?? null);
    if (!file) return;
    const b64 = await new Promise<string>((resolve, reject) => {
      const fr = new FileReader();
      fr.onload = () => resolve(String(fr.result));
      fr.onerror = () => reject(fr.error);
      fr.readAsDataURL(file);
    });
    try {
      const info = await api.exifPreview(b64);
      setExif({
        trust: info.trust,
        captured_at: info.captured_at,
        has_gps: info.has_gps,
      });
    } catch {
      /* EXIF preview is best-effort */
    }
  }

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    api.store(storeId).then(setStore).catch(() => setStore(null));
  }, [storeId]);

  async function submit() {
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.conquer({
        store_id: storeId,
        type: mode,
        lat: mode === "GOLD" ? coords?.lat : undefined,
        lng: mode === "GOLD" ? coords?.lng : undefined,
        evidence_type:
          mode === "GOLD"
            ? "REALTIME_GPS"
            : photoName
              ? "PHOTO"
              : "NONE",
        evidence_image_url: photoName ? `local://${photoName}` : null,
        visited_at: mode === "SILVER" ? exif?.captured_at ?? null : null,
      });
      setResult(res);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "정복에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  const distance =
    coords && store ? haversineM(coords.lat, coords.lng, store.lat, store.lng) : null;

  if (result) {
    return (
      <ConquestResult
        result={result}
        flagType={mode}
        title="정복 완료!"
        description={`${store?.name}에 ${mode === "GOLD" ? "골드" : "실버"} 깃발을 꽂았습니다.`}
        storeHref={`/stores/${storeId}`}
        storeLabel="매장으로 돌아가기"
      />
    );
  }

  return (
    <div className="page">
      <div className="page-header" style={{ marginBottom: 14 }}>
        <BackLink href={`/stores/${storeId}`} label="취소" />
        <div className="page-title" style={{ fontSize: 18 }}>
          정복하기
        </div>
      </div>

      {store && (
        <div className="card">
          <strong>{store.name}</strong>
          <p className="muted" style={{ fontSize: 13, margin: "4px 0 0" }}>
            {store.address}
          </p>
        </div>
      )}

      <div className="section-title">어떻게 다녀오셨나요?</div>
      <div className="tabs">
        <button
          className={`tab${mode === "GOLD" ? " on" : ""}`}
          onClick={() => setMode("GOLD")}
        >
          지금 여기예요
        </button>
        <button
          className={`tab${mode === "SILVER" ? " on" : ""}`}
          onClick={() => setMode("SILVER")}
        >
          예전에 다녀왔어요
        </button>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        {mode === "GOLD" ? (
          <>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="ii" style={{ fontWeight: 700 }}>
                <Icon name="mapPin" size={16} />
                현재 위치
              </span>
              {distance == null ? (
                <span className="muted" style={{ fontSize: 12 }}>
                  {geoError ? "확인 불가" : "확인 중…"}
                </span>
              ) : distance <= NEAR_M ? (
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--ok)" }}>
                  매장 근처에 있어요
                </span>
              ) : (
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--danger)" }}>
                  매장에서 {formatDistance(distance)} 떨어져 있어요
                </span>
              )}
            </div>
            {geoError && (
              <p className="error-text">{geoError} 매장 근처에서 시도하세요.</p>
            )}
            <p className="muted" style={{ fontSize: 13, margin: "8px 0 0", lineHeight: 1.5 }}>
              매장 가까이에서 인증하면 골드 깃발과 경험치를 모두 받아요.
            </p>
          </>
        ) : (
          <p className="muted" style={{ fontSize: 13, margin: 0, lineHeight: 1.5 }}>
            예전에 다녀온 빵집도 사진과 함께 남길 수 있어요. 경험치 50%,
            하루 5곳까지. 다시 가서 인증하면 골드로 바뀌어요.
          </p>
        )}

        <label
          className="btn btn-ghost"
          style={{ marginTop: 12, cursor: "pointer" }}
        >
          <Icon name="camera" size={18} strokeWidth={2.25} />
          {photoName ?? "사진 첨부"}
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => onPhoto(e.target.files?.[0])}
          />
        </label>

        {exif && (
          <div
            className={`badge ${
              exif.trust === "HIGH"
                ? "badge-verified"
                : exif.trust === "MEDIUM"
                  ? "badge-gold"
                  : "badge-silver"
            }`}
            style={{ marginTop: 10 }}
          >
            {EXIF_LABEL[exif.trust]}
            {exif.captured_at ? ` · ${formatShortDate(exif.captured_at)}` : ""}
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}

      <button
        className="btn btn-primary"
        style={{ marginTop: 16 }}
        disabled={submitting || (mode === "GOLD" && !coords)}
        onClick={submit}
      >
        {!submitting && <FlagIcon size={18} />}
        {submitting ? "정복 중…" : "깃발 꽂기"}
      </button>
    </div>
  );
}
