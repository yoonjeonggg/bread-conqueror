"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { StoreCard } from "@/components/StoreCard";
import { api } from "@/lib/api";
import type { Store } from "@/lib/types";

type Sort = "popular" | "rating" | "recent";
const SORT_LABEL: Record<Sort, string> = {
  popular: "정복자순",
  rating: "평점순",
  recent: "최신순",
};
const PAGE = 20;

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("");
  const [category, setCategory] = useState("");
  const [verified, setVerified] = useState(false);
  const [sort, setSort] = useState<Sort>("popular");

  const [filters, setFilters] = useState<{
    regions: string[];
    categories: string[];
  }>({ regions: [], categories: [] });
  const [items, setItems] = useState<Store[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.storeFilters().then(setFilters).catch(() => {});
  }, []);

  const run = useCallback(
    async (offset: number) => {
      setLoading(true);
      try {
        const res = await api.searchStores({
          q: q.trim() || undefined,
          region_sido: region || undefined,
          category: category || undefined,
          verified_only: verified,
          sort,
          limit: PAGE,
          offset,
        });
        setTotal(res.total);
        setItems((prev) =>
          offset === 0 ? res.items : [...prev, ...res.items],
        );
      } finally {
        setLoading(false);
      }
    },
    [q, region, category, verified, sort],
  );

  // 필터 변경 시 자동 재검색 (키워드는 제출 시)
  useEffect(() => {
    run(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [region, category, verified, sort]);

  return (
    <div className="page">
      <div className="page-header">
        <div className="page-title">🔍 매장 검색</div>
        <Link href="/map" className="link-accent">
          지도
        </Link>
      </div>

      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          run(0);
        }}
      >
        <div className="field" style={{ marginBottom: 10 }}>
          <input
            placeholder="빵집 이름 · 주소"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="search-select"
          >
            <option value="">지역 전체</option>
            {filters.regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="search-select"
          >
            <option value="">종류 전체</option>
            {filters.categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as Sort)}
            className="search-select"
          >
            {(Object.keys(SORT_LABEL) as Sort[]).map((s) => (
              <option key={s} value={s}>
                {SORT_LABEL[s]}
              </option>
            ))}
          </select>
          <label
            className={`badge ${verified ? "badge-verified" : "badge-silver"}`}
            style={{ cursor: "pointer" }}
          >
            <input
              type="checkbox"
              checked={verified}
              onChange={(e) => setVerified(e.target.checked)}
              style={{ display: "none" }}
            />
            ✅ 인증 매장만
          </label>
        </div>
        <button className="btn btn-primary" style={{ marginTop: 12 }}>
          검색
        </button>
      </form>

      <div className="section-title">
        결과 {total}곳
      </div>
      {!loading && items.length === 0 ? (
        <div className="card list-empty">조건에 맞는 매장이 없습니다.</div>
      ) : (
        items.map((s) => <StoreCard key={s.id} store={s} />)
      )}
      {items.length < total && (
        <button
          className="btn btn-ghost"
          style={{ marginTop: 12 }}
          disabled={loading}
          onClick={() => run(items.length)}
        >
          {loading ? "불러오는 중…" : "더 보기"}
        </button>
      )}
    </div>
  );
}
