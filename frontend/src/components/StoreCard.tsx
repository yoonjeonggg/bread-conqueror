import Link from "next/link";
import { memo } from "react";
import { MapPin, Star, UsersRound } from "lucide-react";

import type { Store } from "@/lib/types";
import { FlagCount, VerifiedBadge } from "./badges";

function formatDistance(m: number): string {
  return m < 1000 ? `${Math.round(m)}m` : `${(m / 1000).toFixed(1)}km`;
}

// memoized: /map re-renders on every radius toggle, but derived results reuse
// the same Store objects, so unchanged cards can skip rendering entirely
export const StoreCard = memo(function StoreCard({ store }: { store: Store }) {
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
          <span className="inline-ico" style={{ fontSize: 13, fontWeight: 700 }}>
            <MapPin size={14} strokeWidth={2.5} />
            {formatDistance(store.distance_m)}
          </span>
        )}
      </div>

      <div className="row" style={{ marginTop: 8, gap: 8 }}>
        <span className="muted inline-ico" style={{ fontSize: 12 }}>
          <UsersRound size={13} />
          정복자 {s?.conqueror_count ?? 0}명
        </span>
        {s?.average_rating != null && (
          <span className="muted inline-ico" style={{ fontSize: 12 }}>
            <Star size={13} color="var(--gold)" fill="var(--gold)" />
            {s.average_rating}
          </span>
        )}
        {store.is_verified_owner && <VerifiedBadge />}
      </div>
    </Link>
  );
});
