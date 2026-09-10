"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const ITEMS = [
  { href: "/", label: "홈", ico: "🏠" },
  { href: "/map", label: "지도", ico: "🗺️" },
  { href: "/board", label: "게시판", ico: "📝" },
  { href: "/notifications", label: "알림", ico: "🔔" },
  { href: "/ranking", label: "랭킹", ico: "🏆" },
  { href: "/profile", label: "내정보", ico: "🚩" },
];

export function BottomNav() {
  const pathname = usePathname();
  const { user } = useAuth();
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
    <nav className="bottom-nav">
      {ITEMS.map((it) => {
        const active =
          it.href === "/" ? pathname === "/" : pathname.startsWith(it.href);
        const showBadge = it.href === "/notifications" && unread > 0;
        return (
          <Link
            key={it.href}
            href={it.href}
            className={active ? "active" : undefined}
          >
            <span className="ico" style={{ position: "relative" }}>
              {it.ico}
              {showBadge && (
                <span className="nav-badge">{unread > 9 ? "9+" : unread}</span>
              )}
            </span>
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
