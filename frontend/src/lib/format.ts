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

/** 2026-10-11T… → "10.11" */
export function formatShortDate(iso: string): string {
  return formatDate(iso).slice(5);
}

/** Great-circle distance in metres between two lat/lng points. */
export function haversineM(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const rad = (d: number) => (d * Math.PI) / 180;
  const a =
    Math.sin(rad(lat2 - lat1) / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lng2 - lng1) / 2) ** 2;
  return 2 * 6_371_000 * Math.asin(Math.sqrt(a));
}
