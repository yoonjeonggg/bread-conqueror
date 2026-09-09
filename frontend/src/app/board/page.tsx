"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Post } from "@/lib/types";

export default function BoardPage() {
  const { user } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api
      .posts()
      .then(setPosts)
      .catch(() => setPosts([]))
      .finally(() => setLoaded(true));
  }, []);

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

      {loaded && posts.length === 0 && (
        <div className="card list-empty">첫 추천 글을 남겨보세요.</div>
      )}

      {posts.map((p) => (
        <Link key={p.id} href={`/board/${p.id}`} className="card" style={{ display: "block" }}>
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
