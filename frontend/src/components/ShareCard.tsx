"use client";

import { useEffect, useRef, useState } from "react";

import { TIER_NAMES } from "@/lib/types";

const FONT_STACK =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

const W = 900;
const H = 1125;

export interface ShareCardData {
  storeName: string;
  flagType: "GOLD" | "SILVER";
  upgraded: boolean;
  nickname: string;
  tierLevel: number;
  expGranted: number;
  date: Date;
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function wrapLine(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (ctx.measureText(candidate).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines.slice(0, 2);
}

function draw(canvas: HTMLCanvasElement, data: ShareCardData) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.scale(dpr, dpr);

  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, "#c68642");
  bg.addColorStop(1, "#a56a2f");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = "rgba(255,255,255,0.92)";
  ctx.font = `700 34px ${FONT_STACK}`;
  ctx.fillText("🥐 Bread Conqueror", 56, 96);

  ctx.font = `800 120px ${FONT_STACK}`;
  ctx.textAlign = "center";
  ctx.fillText(
    data.upgraded ? "🥈➜🥇" : data.flagType === "GOLD" ? "🥇" : "🥈",
    W / 2,
    340,
  );

  ctx.font = `800 52px ${FONT_STACK}`;
  ctx.fillStyle = "#fff";
  ctx.fillText(
    data.upgraded ? "골드로 업그레이드!" : "정복 완료!",
    W / 2,
    420,
  );

  ctx.font = `600 36px ${FONT_STACK}`;
  ctx.fillStyle = "rgba(255,255,255,0.92)";
  const storeLines = wrapLine(ctx, data.storeName, W - 160);
  storeLines.forEach((line, i) => {
    ctx.fillText(line, W / 2, 480 + i * 46);
  });

  ctx.textAlign = "left";

  const cardY = 620;
  const cardH = H - cardY - 60;
  ctx.fillStyle = "#fffdf8";
  roundRect(ctx, 56, cardY, W - 112, cardH, 28);
  ctx.fill();

  ctx.fillStyle = "#2b2118";
  ctx.font = `700 40px ${FONT_STACK}`;
  ctx.fillText(data.nickname, 96, cardY + 70);

  ctx.fillStyle = "#6b5d4d";
  ctx.font = `500 30px ${FONT_STACK}`;
  const tierName = TIER_NAMES[data.tierLevel] ?? `Lv.${data.tierLevel}`;
  ctx.fillText(`🎖️ ${tierName}`, 96, cardY + 116);

  ctx.strokeStyle = "#ece2d2";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(96, cardY + 150);
  ctx.lineTo(W - 96, cardY + 150);
  ctx.stroke();

  ctx.fillStyle = "#e8b923";
  ctx.font = `800 44px ${FONT_STACK}`;
  ctx.fillText(`+${data.expGranted} EXP`, 96, cardY + 208);

  ctx.fillStyle = "#6b5d4d";
  ctx.font = `500 26px ${FONT_STACK}`;
  ctx.textAlign = "right";
  ctx.fillText(
    data.date.toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }),
    W - 96,
    cardY + 208,
  );
  ctx.textAlign = "left";
}

export function ShareCard({ data }: { data: ShareCardData }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [busy, setBusy] = useState<"download" | "share" | null>(null);
  const [canShareFiles, setCanShareFiles] = useState(false);

  useEffect(() => {
    if (canvasRef.current) draw(canvasRef.current, data);
    setCanShareFiles(
      typeof navigator !== "undefined" &&
        "canShare" in navigator &&
        navigator.canShare({
          files: [new File([], "x.png", { type: "image/png" })],
        }),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function toBlob(): Promise<Blob | null> {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  }

  async function download() {
    setBusy("download");
    try {
      const blob = await toBlob();
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bread-conqueror-${data.storeName}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(null);
    }
  }

  async function share() {
    setBusy("share");
    try {
      const blob = await toBlob();
      if (!blob) return;
      const file = new File([blob], "bread-conqueror.png", {
        type: "image/png",
      });
      await navigator.share({
        files: [file],
        title: "Bread Conqueror",
        text: `${data.storeName} 정복 완료! 🚩`,
      });
    } catch {
      /* user cancelled share sheet — no-op */
    } finally {
      setBusy(null);
    }
  }

  return (
    <div style={{ marginTop: 16 }}>
      <canvas
        ref={canvasRef}
        style={{
          width: "100%",
          borderRadius: "var(--radius)",
          boxShadow: "var(--shadow-lg)",
          display: "block",
        }}
      />
      <div className="row" style={{ gap: 10, marginTop: 12 }}>
        {canShareFiles && (
          <button
            className="btn btn-primary"
            disabled={busy !== null}
            onClick={share}
          >
            {busy === "share" ? "공유 준비 중…" : "📤 공유하기"}
          </button>
        )}
        <button
          className="btn btn-secondary"
          disabled={busy !== null}
          onClick={download}
        >
          {busy === "download" ? "저장 중…" : "💾 이미지 저장"}
        </button>
      </div>
    </div>
  );
}
