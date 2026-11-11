/** 2026-10-11T… → "2026.10.11" */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}.${mm}.${dd}`;
}

/** 320 → "320m", 999.7 → "1.0km", 1432 → "1.4km" */
export function formatDistance(m: number): string {
  const rounded = Math.round(m);
  return rounded < 1000 ? `${rounded}m` : `${(m / 1000).toFixed(1)}km`;
}
