"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ReportButton } from "@/components/ReportButton";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Comment, Post } from "@/lib/types";

export default function PostDetailPage() {
  const params = useParams<{ id: string }>();
  const postId = Number(params.id);
  const { user } = useAuth();

  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [text, setText] = useState("");
  const [likes, setLikes] = useState(0);
  const [liked, setLiked] = useState(false);
  const [missing, setMissing] = useState(false);

  const loadComments = () =>
    api.postComments(postId).then(setComments).catch(() => setComments([]));

  useEffect(() => {
    api
      .post(postId)
      .then((p) => {
        setPost(p);
        setLikes(p.like_count);
      })
      .catch(() => setMissing(true));
    loadComments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId]);

  if (missing)
    return (
      <div className="page">
        <div className="card list-empty">글을 찾을 수 없습니다.</div>
      </div>
    );
  if (!post)
    return (
      <div className="page">
        <div className="card list-empty">불러오는 중…</div>
      </div>
    );

  return (
    <div className="page">
      <div className="page-header">
        <Link href="/board" className="link-accent">
          ← 게시판
        </Link>
      </div>

      <div className="card">
        <h2 style={{ margin: "0 0 6px", fontSize: 19 }}>{post.title}</h2>
        <div className="muted" style={{ fontSize: 12 }}>
          <span className="badge badge-gold">
            티어 Lv.{post.author_tier_snapshot}
          </span>{" "}
          깃발 {post.author_flag_count_snapshot} ·{" "}
          {new Date(post.created_at).toLocaleDateString("ko-KR")}
        </div>
        <p style={{ whiteSpace: "pre-wrap", marginTop: 12, fontSize: 15 }}>
          {post.content}
        </p>

        <div className="row" style={{ marginTop: 12, gap: 12 }}>
          <button
            className="btn btn-ghost"
            style={{ width: "auto", padding: "8px 14px" }}
            disabled={!user || liked}
            onClick={async () => {
              try {
                await api.likePost(postId);
                setLikes((n) => n + 1);
                setLiked(true);
              } catch (e) {
                if (e instanceof ApiError && e.status === 409) setLiked(true);
              }
            }}
          >
            ♥ {likes}
          </button>
          <ReportButton targetType="POST" targetId={postId} label="글 신고" />
        </div>
      </div>

      <div className="section-title">댓글 {comments.length}개</div>

      {user && (
        <div className="card">
          <div className="row" style={{ gap: 8 }}>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="댓글 달기"
              maxLength={500}
              style={{
                flex: 1,
                border: "1px solid var(--line)",
                borderRadius: 10,
                padding: 10,
                fontSize: 14,
              }}
            />
            <button
              className="btn btn-secondary"
              style={{ width: "auto", padding: "10px 14px" }}
              disabled={text.trim().length === 0}
              onClick={async () => {
                await api.addComment(postId, text.trim());
                setText("");
                await loadComments();
              }}
            >
              등록
            </button>
          </div>
        </div>
      )}

      {comments.map((c) => (
        <div key={c.id} className="card">
          <p style={{ fontSize: 14, margin: 0 }}>{c.content}</p>
          <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
            사용자 {c.user_id} ·{" "}
            {new Date(c.created_at).toLocaleDateString("ko-KR")}
          </div>
        </div>
      ))}
    </div>
  );
}
