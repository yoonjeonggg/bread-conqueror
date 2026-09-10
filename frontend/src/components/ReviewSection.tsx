"use client";

import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Review } from "@/lib/types";
import { StarPicker, Stars } from "./StarRating";

export function ReviewSection({ storeId }: { storeId: number }) {
  const { user } = useAuth();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [rating, setRating] = useState(5);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.reviews(storeId).then(setReviews).catch(() => setReviews([]));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storeId]);

  const mine = user ? reviews.find((r) => r.user_id === user.id) : undefined;

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      await api.upsertReview(storeId, rating, content.trim() || undefined);
      setContent("");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "리뷰 등록에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (mine) {
      setRating(Number(mine.rating));
      setContent(mine.content ?? "");
    }
  }, [mine]);

  return (
    <>
      <div className="section-title">리뷰 {reviews.length}개</div>

      {user ? (
        <div className="card">
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
            {mine ? "내 리뷰 수정" : "이 빵집 리뷰 남기기"}
          </div>
          <StarPicker value={rating} onChange={setRating} />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="맛, 분위기, 추천 메뉴…"
            rows={3}
            style={{
              width: "100%",
              marginTop: 10,
              border: "1px solid var(--line)",
              borderRadius: 10,
              padding: 10,
              fontFamily: "inherit",
              fontSize: 14,
            }}
          />
          {error && <p className="error-text">{error}</p>}
          <button
            className="btn btn-secondary"
            style={{ marginTop: 8 }}
            disabled={busy}
            onClick={submit}
          >
            {busy ? "저장 중…" : mine ? "리뷰 수정" : "리뷰 등록"}
          </button>
        </div>
      ) : (
        <div className="card list-empty">로그인하면 리뷰를 남길 수 있습니다.</div>
      )}

      {reviews.map((r) => (
        <div key={r.id} className="card">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong style={{ fontSize: 14 }}>
              {r.author_nickname ?? `사용자 ${r.user_id}`}
            </strong>
            <span style={{ color: "var(--gold)" }}>
              <Stars value={Number(r.rating)} />
            </span>
          </div>
          {r.content && (
            <p style={{ fontSize: 14, margin: "6px 0 0" }}>{r.content}</p>
          )}
          <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
            {new Date(r.created_at).toLocaleDateString("ko-KR")}
            {r.author_tier_level ? ` · 티어 Lv.${r.author_tier_level}` : ""}
          </div>
        </div>
      ))}
    </>
  );
}
