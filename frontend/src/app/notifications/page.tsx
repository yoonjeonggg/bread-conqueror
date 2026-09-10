"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AppNotification, NotificationType } from "@/lib/types";

const ICON: Record<NotificationType, string> = {
  FOLLOW: "👤",
  POST_COMMENT: "💬",
  POST_LIKE: "❤️",
  CLAIM_APPROVED: "✅",
  CLAIM_REJECTED: "🚫",
  TIER_UP: "🎉",
  FLAG_APPROVED: "🥇",
  FLAG_INVALIDATED: "⚠️",
  QR_CONQUEST: "🚩",
};

function hrefFor(n: AppNotification): string | null {
  switch (n.target_type) {
    case "USER":
      return n.target_id ? `/users/${n.target_id}` : null;
    case "POST":
      return n.target_id ? `/board/${n.target_id}` : null;
    case "STORE":
      return n.target_id ? `/stores/${n.target_id}` : null;
    case "FLAG":
      return "/profile";
    default:
      return null;
  }
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "방금";
  if (m < 60) return `${m}분 전`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
}

export default function NotificationsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login?next=/notifications");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    api
      .notifications()
      .then((rows) => {
        setItems(rows);
        setReady(true);
        if (rows.some((r) => !r.is_read)) api.markNotificationsRead().catch(() => {});
      })
      .catch(() => setReady(true));
  }, [user]);

  if (!user) return null;

  const unreadCount = items.filter((n) => !n.is_read).length;

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🔔 알림</div>
        {unreadCount > 0 && (
          <button
            className="link-accent"
            style={{ background: "none", border: "none", cursor: "pointer" }}
            onClick={() => {
              api.markNotificationsRead().catch(() => {});
              setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
            }}
          >
            모두 읽음
          </button>
        )}
      </div>

      {!ready ? (
        <div className="card list-empty">불러오는 중…</div>
      ) : items.length === 0 ? (
        <div className="card list-empty">아직 알림이 없습니다.</div>
      ) : (
        items.map((n) => {
          const href = hrefFor(n);
          const body = (
            <div className={`card notif-item ${n.is_read ? "" : "unread"}`}>
              <span className="notif-dot">{ICON[n.type] ?? "🔔"}</span>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 14, margin: 0 }}>{n.message}</p>
                <span className="muted" style={{ fontSize: 12 }}>
                  {timeAgo(n.created_at)}
                </span>
              </div>
            </div>
          );
          return href ? (
            <Link key={n.id} href={href}>
              {body}
            </Link>
          ) : (
            <div key={n.id}>{body}</div>
          );
        })
      )}
    </div>
  );
}
