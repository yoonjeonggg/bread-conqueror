"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [next, setNext] = useState("/");

  useEffect(() => {
    const n = new URLSearchParams(window.location.search).get("next");
    if (n && n.startsWith("/")) setNext(n);
  }, []);
  const [email, setEmail] = useState("demo@bread.dev");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      router.replace(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-title" style={{ marginBottom: 20 }}>
        로그인
      </div>
      <form onSubmit={submit} className="card">
        <div className="field">
          <label htmlFor="email">이메일</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "확인 중…" : "로그인"}
        </button>
      </form>
      <p className="muted" style={{ textAlign: "center", marginTop: 16, fontSize: 13 }}>
        계정이 없나요?{" "}
        <Link href="/signup" className="link-accent">
          회원가입
        </Link>
      </p>
      <p className="muted" style={{ textAlign: "center", marginTop: 8, fontSize: 12 }}>
        데모 계정이 미리 입력되어 있습니다 (seed 실행 시).
      </p>
    </div>
  );
}
