"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, type IconName } from "./Icon";

// 알림은 홈·지도 헤더의 벨 아이콘으로 들어간다 (HeaderActions).
const ITEMS: { href: string; label: string; ico: IconName }[] = [
  { href: "/", label: "홈", ico: "home" },
  { href: "/map", label: "지도", ico: "map" },
  { href: "/board", label: "게시판", ico: "board" },
  { href: "/ranking", label: "랭킹", ico: "trophy" },
  { href: "/profile", label: "빵로그", ico: "user" },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="bottom-nav">
      {ITEMS.map((it) => {
        const active =
          it.href === "/" ? pathname === "/" : pathname.startsWith(it.href);
        return (
          <Link
            key={it.href}
            href={it.href}
            className={active ? "active" : undefined}
          >
            <span className="ico">
              <Icon name={it.ico} size={22} strokeWidth={active ? 2.2 : 2} />
            </span>
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
