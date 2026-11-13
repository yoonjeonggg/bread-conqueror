"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Icon } from "./Icon";

/** 페이지 헤더 오른쪽: 검색 링크 + 알림 벨(읽지 않은 개수 배지). */
export function HeaderActions() {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!user) {
      setUnread(0);
      return;
    }
    let alive = true;
    const poll = () =>
      api
        .unreadCount()
        .then((r) => alive && setUnread(r.count))
        .catch(() => {});
    poll();
    const id = setInterval(poll, 20000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [user, pathname]);

  return (
    <span className="header-actions">
      <Link href="/search" className="link-accent">
        <Icon name="search" size={18} />
        검색
      </Link>
      {user ? (
        <Link
          href="/notifications"
          className="header-bell"
          aria-label={unread > 0 ? `알림 ${unread}개 읽지 않음` : "알림"}
        >
          <Icon name="bell" size={22} strokeWidth={2} />
          {unread > 0 && (
            <span className="nav-badge">{unread > 9 ? "9+" : unread}</span>
          )}
        </Link>
      ) : (
        !loading && (
          <Link href="/login" className="link-accent">
            로그인
          </Link>
        )
      )}
    </span>
  );
}
