"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { api, ApiError, getToken, setToken } from "./api";
import type { Profile } from "./types";

interface AuthState {
  user: Profile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    // signed-out visitors would otherwise fire a guaranteed-401 /users/me on
    // every page load
    if (!getToken()) {
      setUser(null);
      return;
    }
    try {
      setUser(await api.me());
    } catch (e) {
      // expired/invalid token: drop it so we stop sending it everywhere.
      // Network errors keep the token — the session may still be fine.
      if (e instanceof ApiError && e.status === 401) setToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout, refresh }),
    [user, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// For pages that only make sense signed in: once auth has resolved and there is
// no user, go to /login and come back to this exact page afterwards. The
// redirect runs in an effect — calling router.replace during render re-fires on
// every render and trips React's "update while rendering" warning.
export function useRequireAuth(): AuthState {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (auth.loading || auth.user) return;
    const here = pathname + window.location.search;
    router.replace(`/login?next=${encodeURIComponent(here)}`);
  }, [auth.loading, auth.user, pathname, router]);

  return auth;
}
