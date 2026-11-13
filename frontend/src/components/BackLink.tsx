import Link from "next/link";

import { Icon } from "./Icon";

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="back-link">
      <Icon name="chevronLeft" size={20} />
      {label}
    </Link>
  );
}
