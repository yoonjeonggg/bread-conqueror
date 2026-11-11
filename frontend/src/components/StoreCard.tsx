import Link from "next/link";

import { formatDistance } from "@/lib/format";
import type { Store } from "@/lib/types";
import { FlagCount, VerifiedBadge } from "./badges";
import { Icon } from "./Icon";

export function StoreCard({ store }: { store: Store }) {
  const s = store.stat;
  return (
    <Link href={`/stores/${store.id}`} className="card" style={{ display: "block" }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="stack">
          <strong style={{ fontSize: 16 }}>{store.name}</strong>
          <span className="muted" style={{ fontSize: 13 }}>
            {store.address}
          </span>
        </div>
        {store.conquered_by_me && (
          <span className="badge badge-accent">정복함</span>
        )}
      </div>

      <div className="divider" />

      <div className="row" style={{ justifyContent: "space-between" }}>
        <FlagCount
          gold={s?.gold_flag_count ?? 0}
          silver={s?.silver_flag_count ?? 0}
        />
        {typeof store.distance_m === "number" && (
          <span className="ii" style={{ fontSize: 13, fontWeight: 700 }}>
            <Icon name="mapPin" size={14} />
            {formatDistance(store.distance_m)}
          </span>
        )}
      </div>

      <div className="row" style={{ marginTop: 8, gap: 8 }}>
        <span className="muted ii" style={{ fontSize: 12 }}>
          <Icon name="users" size={13} strokeWidth={2} />
          정복자 {s?.conqueror_count ?? 0}명
        </span>
        {s?.average_rating != null && (
          <span className="muted ii" style={{ fontSize: 12 }}>
            <Icon name="star" size={13} color="var(--gold)" fill strokeWidth={1} />
            {s.average_rating}
          </span>
        )}
        {store.is_verified_owner && <VerifiedBadge />}
      </div>
    </Link>
  );
}
