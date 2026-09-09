"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "홈", ico: "🏠" },
  { href: "/map", label: "지도", ico: "🗺️" },
  { href: "/ranking", label: "랭킹", ico: "🏆" },
  { href: "/profile", label: "내정보", ico: "🚩" },
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
            <span className="ico">{it.ico}</span>
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
