"use client";

import { Star, StarHalf } from "lucide-react";

const ON = "var(--gold)";
const OFF = "var(--line)";

export function Stars({ value, size = 14 }: { value: number; size?: number }) {
  const full = Math.floor(value);
  const half = value - full >= 0.5;
  return (
    <span className="inline-ico" style={{ gap: 1 }} aria-label={`${value}점`}>
      {[0, 1, 2, 3, 4].map((i) =>
        i < full ? (
          <Star key={i} size={size} color={ON} fill={ON} />
        ) : i === full && half ? (
          <span key={i} style={{ position: "relative", display: "inline-flex" }}>
            <Star size={size} color={OFF} fill={OFF} />
            <StarHalf
              size={size}
              color={ON}
              fill={ON}
              style={{ position: "absolute", inset: 0 }}
            />
          </span>
        ) : (
          <Star key={i} size={size} color={OFF} fill={OFF} />
        ),
      )}
    </span>
  );
}

export function StarPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="row" style={{ gap: 4 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          aria-label={`${n}점`}
          onClick={() => onChange(n)}
          className="text-btn"
        >
          <Star
            size={28}
            color={n <= value ? ON : OFF}
            fill={n <= value ? ON : OFF}
          />
        </button>
      ))}
    </div>
  );
}
