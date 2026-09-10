"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function NewPostPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!loading && !user) {
    router.replace("/login");
    return null;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const post = await api.createPost(title.trim(), content.trim());
      router.replace(`/board/${post.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "작성에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <Link href="/board" className="link-accent">
          ← 게시판
        </Link>
        <div className="page-title" style={{ fontSize: 18 }}>
          빵집 추천 글쓰기
        </div>
      </div>

      <form onSubmit={submit} className="card">
        <div className="field">
          <label htmlFor="title">제목</label>
          <input
            id="title"
            value={title}
            maxLength={100}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="content">내용</label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={8}
            required
            style={{
              border: "1px solid var(--line)",
              borderRadius: 10,
              padding: 12,
              fontFamily: "inherit",
              fontSize: 14,
            }}
          />
        </div>
        <p className="muted" style={{ fontSize: 12 }}>
          작성 시점의 티어·깃발 수가 함께 표시되어 추천의 신뢰도가 됩니다.
        </p>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" style={{ marginTop: 8 }} disabled={busy}>
          {busy ? "게시 중…" : "게시하기"}
        </button>
      </form>
    </div>
  );
}
