"use client";

import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function ReportButton({
  targetType,
  targetId,
  label = "신고",
}: {
  targetType: "FLAG" | "POST" | "COMMENT";
  targetId: number;
  label?: string;
}) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user) return null;
  if (done)
    return (
      <span className="muted" style={{ fontSize: 12 }}>
        신고 접수됨
      </span>
    );

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="muted"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: 12,
        }}
      >
        🚩 {label}
      </button>
      {open && (
        <div className="card" style={{ marginTop: 8 }}>
          <div className="field">
            <label>신고 사유</label>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="예: 허위 인증으로 의심됨"
            />
          </div>
          {error && <p className="error-text">{error}</p>}
          <button
            className="btn btn-ghost"
            disabled={reason.trim().length < 2}
            onClick={async () => {
              try {
                await api.report(targetType, targetId, reason.trim());
                setDone(true);
              } catch (e) {
                setError(
                  e instanceof ApiError ? e.message : "신고에 실패했습니다.",
                );
              }
            }}
          >
            신고 제출
          </button>
        </div>
      )}
    </>
  );
}
