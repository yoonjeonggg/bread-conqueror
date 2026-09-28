// Only same-origin *paths* may be used as a post-login destination. A bare
// startsWith("/") check lets "//evil.com" and "/\evil.com" through, which
// browsers treat as protocol-relative URLs to another host (open redirect).
export function safeNextPath(raw: string | null | undefined, fallback = "/"): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return fallback;
  // backslashes and control chars (tab/newline are stripped by URL parsers,
  // turning "/\t/evil.com" into "//evil.com") are never legitimate here
  // eslint-disable-next-line no-control-regex
  if (/[\\\u0000-\u001f]/.test(raw)) return fallback;
  try {
    const base = "http://same-origin.invalid";
    const url = new URL(raw, base);
    if (url.origin !== base) return fallback;
    return url.pathname + url.search + url.hash;
  } catch {
    return fallback;
  }
}
