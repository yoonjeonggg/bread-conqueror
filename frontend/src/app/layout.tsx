import type { Metadata, Viewport } from "next";

import { BottomNav } from "@/components/BottomNav";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bread Conqueror · 빵 정복",
  description: "전국 베이커리를 방문하며 깃발을 꽂고 정복하는 게임형 빵 커뮤니티",
};

export const viewport: Viewport = {
  themeColor: "#c68642",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <AuthProvider>
          <div className="app-shell">
            {children}
            <BottomNav />
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
