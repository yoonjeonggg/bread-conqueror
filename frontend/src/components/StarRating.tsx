"use client";

export function Stars({ value }: { value: number }) {
  const full = Math.floor(value);
  const half = value - full >= 0.5;
  return (
    <span aria-label={`${value}점`}>
      {"★".repeat(full)}
      {half ? "⯨" : ""}
      <span style={{ color: "var(--line)" }}>
        {"★".repeat(Math.max(0, 5 - full - (half ? 1 : 0)))}
      </span>
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
    <div className="row" style={{ gap: 4, fontSize: 26 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: n <= value ? "var(--gold)" : "var(--line)",
            padding: 0,
          }}
        >
          ★
        </button>
      ))}
    </div>
  );
}
