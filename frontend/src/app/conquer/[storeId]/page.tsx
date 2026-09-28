"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, Camera, ChevronLeft, Flag, MapPin, TrendingUp, TriangleAlert } from "lucide-react";

import { FlagMark } from "@/components/badges";
import { useGeolocation } from "@/components/useGeolocation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ConquestResponse, Store } from "@/lib/types";

type Mode = "GOLD" | "SILVER";

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

  if (result) {
    return (
      <div className="page">
        <div className="conquer-celebrate">
          <div className={`flag ${result.upgraded_from_silver ? "wide" : ""}`}>
            {result.upgraded_from_silver && (
              <>
                <FlagMark type="SILVER" size={44} />
                <ArrowRight size={28} color="#fff" strokeWidth={2.5} />
              </>
            )}
            <FlagMark
              type={result.upgraded_from_silver ? "GOLD" : mode}
              size={56}
            />
          </div>
          <h2 style={{ margin: "12px 0 4px" }}>
            {result.upgraded_from_silver ? "골드로 업그레이드!" : "정복 완료!"}
          </h2>
          <p className="muted">
            {store?.name}에 {mode === "GOLD" ? "골드" : "실버"} 깃발을 꽂았습니다.
          </p>
          <div className="hero" style={{ marginTop: 20, textAlign: "left" }}>
            <div className="big">+{result.exp_granted} EXP</div>
            {result.tier_changed && (
              <p
                className="hero-sub inline-ico"
                style={{ margin: "8px 0 0", fontSize: 14 }}
              >
                <TrendingUp size={16} color="var(--accent)" strokeWidth={2.5} />
                티어가 Lv.{result.new_tier_level}로 상승했습니다!
              </p>
            )}
            {result.is_flagged && (
              <p style={{ color: "#ff8a80", margin: "8px 0 0", fontSize: 13 }}>
                <TriangleAlert
                  size={14}
                  strokeWidth={2.5}
                  style={{ verticalAlign: -2, marginRight: 4 }}
                />
                이상 패턴이 감지되어 검토 대기 상태입니다.
                {result.abuse_reasons.map((r) => (
                  <span key={r}> {r}.</span>
                ))}
              </p>
            )}
          </div>
          <div style={{ marginTop: 20, display: "grid", gap: 10 }}>
            <Link href={`/stores/${storeId}`}>
              <button className="btn btn-secondary">매장으로 돌아가기</button>
            </Link>
            <Link href="/profile">
              <button className="btn btn-ghost">내 깃발 보기</button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <Link href={`/stores/${storeId}`} className="back-link">
          <ChevronLeft size={20} strokeWidth={2.5} />
          취소
        </Link>
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

      <div className="section-title">인증 방식</div>
      <div className="tabs">
        <button
          className={`tab ${mode === "GOLD" ? "active" : ""}`}
          onClick={() => setMode("GOLD")}
        >
          <FlagMark type="GOLD" />
          실시간 (GPS+사진)
        </button>
        <button
          className={`tab ${mode === "SILVER" ? "active" : ""}`}
          onClick={() => setMode("SILVER")}
        >
          <FlagMark type="SILVER" />
          과거 방문 등록
        </button>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        {mode === "GOLD" ? (
          <>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="inline-ico" style={{ fontWeight: 700 }}>
                <MapPin size={16} strokeWidth={2.5} />
                현재 위치
              </span>
              <span className="muted" style={{ fontSize: 12 }}>
                {coords
                  ? `${coords.lat.toFixed(5)}, ${coords.lng.toFixed(5)}`
                  : "확인 중…"}
              </span>
            </div>
            {geoError && (
              <p className="error-text">{geoError} 매장 근처에서 시도하세요.</p>
            )}
            <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
              매장 반경 50m 이내에서만 골드 깃발을 꽂을 수 있습니다. 경험치 100%.
            </p>
          </>
        ) : (
          <p className="muted" style={{ fontSize: 13 }}>
            과거에 방문한 빵집을 등록합니다. 경험치 50%, 하루 5곳까지.
            나중에 재방문해 실시간 인증하면 골드로 업그레이드됩니다.
          </p>
        )}

        <label
          className="btn btn-ghost"
          style={{ marginTop: 12, cursor: "pointer" }}
        >
          <Camera size={18} strokeWidth={2.25} />
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
                  : "badge-dark"
            }`}
            style={{ marginTop: 10 }}
          >
            EXIF 신뢰도 {exif.trust}
            {exif.captured_at
              ? ` · 촬영 ${new Date(exif.captured_at).toLocaleDateString("ko-KR")}`
              : ""}
            {exif.has_gps ? " · GPS 포함" : ""}
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
        {submitting ? (
          "정복 중…"
        ) : (
          <>
            <Flag size={18} strokeWidth={2.5} fill="currentColor" />
            깃발 꽂기
          </>
        )}
      </button>
    </div>
  );
}
