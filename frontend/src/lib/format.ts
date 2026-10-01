export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR");
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR");
}

export function timeAgo(iso: string, now = Date.now()): string {
  const m = Math.floor((now - new Date(iso).getTime()) / 60000);
  if (m < 1) return "방금";
  if (m < 60) return `${m}분 전`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
}
