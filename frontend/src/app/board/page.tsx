"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Post } from "@/lib/types";

type Sort = "recent" | "popular";

export default function BoardPage() {
  const { user } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<Sort>("recent");

  const load = useCallback(
    (query?: string) => {
      setLoaded(false);
      api
        .posts({ q: query?.trim() || undefined, sort })
        .then(setPosts)
        .catch(() => setPosts([]))
        .finally(() => setLoaded(true));
    },
    [sort],
  );

  useEffect(() => {
    load(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort]);

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">📝 추천 게시판</div>
        {user && (
          <Link href="/board/new" className="link-accent">
            글쓰기
          </Link>
        )}
      </div>

      <form
        className="card"
        style={{ marginBottom: 12 }}
        onSubmit={(e) => {
          e.preventDefault();
          load(q);
        }}
      >
        <div className="field" style={{ marginBottom: 8 }}>
          <input
            placeholder="제목 · 내용 검색"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="pill-row">
          {(["recent", "popular"] as Sort[]).map((s) => (
            <button
              key={s}
              type="button"
              className={`badge ${sort === s ? "badge-gold" : "badge-silver"}`}
              style={{ border: "none", cursor: "pointer" }}
              onClick={() => setSort(s)}
            >
              {s === "recent" ? "최신순" : "인기순"}
            </button>
          ))}
        </div>
      </form>

      {loaded && posts.length === 0 && (
        <div className="card list-empty">
          {q ? "검색 결과가 없습니다." : "첫 추천 글을 남겨보세요."}
        </div>
      )}

      {posts.map((p) => (
        <Link
          key={p.id}
          href={`/board/${p.id}`}
          className="card"
          style={{ display: "block" }}
        >
          <strong style={{ fontSize: 15 }}>{p.title}</strong>
          <p className="muted" style={{ fontSize: 13, margin: "6px 0 0" }}>
            {p.content.slice(0, 90)}
            {p.content.length > 90 ? "…" : ""}
          </p>
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            <span className="badge badge-gold">
              티어 Lv.{p.author_tier_snapshot}
            </span>{" "}
            깃발 {p.author_flag_count_snapshot} · ♥ {p.like_count}
          </div>
        </Link>
      ))}
    </div>
  );
}
