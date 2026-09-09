import Link from "next/link";

import type { Store } from "@/lib/types";
import { FlagCount, VerifiedBadge } from "./badges";

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
          <span className="badge badge-gold">정복함</span>
        )}
      </div>

      <div className="divider" />

      <div className="row" style={{ justifyContent: "space-between" }}>
        <FlagCount
          gold={s?.gold_flag_count ?? 0}
          silver={s?.silver_flag_count ?? 0}
        />
        <span className="muted" style={{ fontSize: 12 }}>
          {typeof store.distance_m === "number"
            ? `${Math.round(store.distance_m)}m`
            : ""}
        </span>
      </div>

      <div className="row" style={{ marginTop: 8, gap: 8 }}>
        <span className="muted" style={{ fontSize: 12 }}>
          정복자 {s?.conqueror_count ?? 0}명
        </span>
        {s?.average_rating != null && (
          <span className="muted" style={{ fontSize: 12 }}>
            ⭐ {s.average_rating}
          </span>
        )}
        {store.is_verified_owner && <VerifiedBadge />}
      </div>
    </Link>
  );
}
