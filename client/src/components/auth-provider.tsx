"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { api, type AuthStatus, type AuthUser } from "@/lib/api";

type AuthContextValue = {
  loading: boolean;
  status: AuthStatus | null;
  user: AuthUser | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const refresh = useCallback(async () => {
    try {
      const next = await api.authStatus();
      setStatus(next);
    } catch {
      setStatus({ auth_enabled: false, authenticated: true, user: null });
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      await refresh();
      router.replace("/login");
    }
  }, [refresh, router]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (loading || !status) return;
    const onLogin = pathname === "/login";
    if (status.auth_enabled && !status.authenticated && !onLogin) {
      router.replace("/login");
    }
    if (status.authenticated && onLogin) {
      router.replace("/");
    }
  }, [loading, status, pathname, router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      loading,
      status,
      user: status?.user ?? null,
      refresh,
      logout,
    }),
    [loading, status, refresh, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
