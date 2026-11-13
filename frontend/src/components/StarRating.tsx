"use client";

import { Icon } from "./Icon";

// Filled Lucide star, as in the Showcase store cards.
function Star({ size, on }: { size: number; on: boolean }) {
  return (
    <Icon
      name="star"
      size={size}
      fill
      strokeWidth={1}
      color={on ? "var(--gold)" : "var(--line)"}
    />
  );
}

export function Stars({ value, size = 14 }: { value: number; size?: number }) {
  const full = Math.floor(value);
  const half = value - full >= 0.5;
  return (
    <span className="ii" style={{ gap: 2 }} role="img" aria-label={`${value}점`}>
      {[0, 1, 2, 3, 4].map((i) =>
        i === full && half ? (
          <span key={i} style={{ position: "relative", display: "inline-flex" }}>
            <Star size={size} on={false} />
            <span
              style={{
                position: "absolute",
                inset: 0,
                width: "50%",
                overflow: "hidden",
                display: "inline-flex",
              }}
            >
              <Star size={size} on />
            </span>
          </span>
        ) : (
          <Star key={i} size={size} on={i < full} />
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
    <div className="row" style={{ gap: 0 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          aria-label={`${n}점`}
          aria-pressed={n === value}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 9,
            display: "inline-flex",
          }}
        >
          <Star size={26} on={n <= value} />
        </button>
      ))}
    </div>
  );
}
