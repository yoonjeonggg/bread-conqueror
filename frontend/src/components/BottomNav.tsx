"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bell,
  House,
  Map as MapIcon,
  MessageSquareText,
  Trophy,
  UserRound,
  type LucideIcon,
} from "lucide-react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const ITEMS: { href: string; label: string; Icon: LucideIcon }[] = [
  { href: "/", label: "홈", Icon: House },
  { href: "/map", label: "지도", Icon: MapIcon },
  { href: "/board", label: "게시판", Icon: MessageSquareText },
  { href: "/notifications", label: "알림", Icon: Bell },
  { href: "/ranking", label: "랭킹", Icon: Trophy },
  { href: "/profile", label: "내정보", Icon: UserRound },
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
            <span className="ico">
              <it.Icon size={22} strokeWidth={active ? 2.5 : 2} />
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
