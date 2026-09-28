"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BadgeCheck, Ban, Bell, Flag, Heart, type LucideIcon, MessageCircle, QrCode, TrendingUp, TriangleAlert, UserPlus } from "lucide-react";

import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { AppNotification, NotificationType } from "@/lib/types";
import { timeAgo } from "@/lib/format";

const ICON: Record<NotificationType, LucideIcon> = {
  FOLLOW: UserPlus,
  POST_COMMENT: MessageCircle,
  POST_LIKE: Heart,
  CLAIM_APPROVED: BadgeCheck,
  CLAIM_REJECTED: Ban,
  TIER_UP: TrendingUp,
  FLAG_APPROVED: Flag,
  FLAG_INVALIDATED: TriangleAlert,
  QR_CONQUEST: QrCode,
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

export default function NotificationsPage() {
  const { user } = useRequireAuth();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [ready, setReady] = useState(false);


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
        <div className="page-title">알림</div>
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
          const Icon = ICON[n.type] ?? Bell;
          const body = (
            <div className={`card notif-item ${n.is_read ? "" : "unread"}`}>
              <span className="notif-ico">
                <Icon size={18} strokeWidth={2.25} />
              </span>
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
