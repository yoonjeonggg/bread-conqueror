const isDev = process.env.NODE_ENV !== "production";

const apiOrigin = (() => {
  try {
    return new URL(
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
    ).origin;
  } catch {
    return "";
  }
})();

// Kakao Maps SDK: loader on dapi.kakao.com, which pulls its runtime and map
// tiles from *.daumcdn.net using the *page's* scheme (http on local dev). Kakao
// hosts are therefore scheme-less sources: they match the page scheme, so
// production over https still only allows https. Next's hydration bootstrap is inline, and dev mode
// (React Refresh) additionally needs eval + the HMR websocket.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""} dapi.kakao.com *.daumcdn.net`,
  "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
  "font-src 'self' data: https://cdn.jsdelivr.net",
  "img-src 'self' data: blob: *.daumcdn.net *.kakao.com *.kakaocdn.net",
  `connect-src 'self' ${apiOrigin} *.kakao.com *.daumcdn.net${isDev ? " ws://localhost:3000" : ""}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // the map/conquest pages need geolocation; nothing needs mic or payments.
  // camera stays blocked — photo evidence comes from a file input, not getUserMedia
  {
    key: "Permissions-Policy",
    value: "geolocation=(self), camera=(), microphone=(), payment=()",
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
