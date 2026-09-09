"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.register(nickname, email, password);
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "회원가입에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-title" style={{ marginBottom: 20 }}>
        회원가입
      </div>
      <form onSubmit={submit} className="card">
        <div className="field">
          <label htmlFor="nickname">닉네임</label>
          <input
            id="nickname"
            value={nickname}
            minLength={2}
            maxLength={30}
            onChange={(e) => setNickname(e.target.value)}
            required
          />
        </div>
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
          <label htmlFor="password">비밀번호 (8자 이상)</label>
          <input
            id="password"
            type="password"
            value={password}
            minLength={8}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "가입 중…" : "가입하고 시작하기"}
        </button>
      </form>
      <p className="muted" style={{ textAlign: "center", marginTop: 16, fontSize: 13 }}>
        이미 계정이 있나요?{" "}
        <Link href="/login" className="link-accent">
          로그인
        </Link>
      </p>
    </div>
  );
}
