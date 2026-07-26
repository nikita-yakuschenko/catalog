"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { api, type AuthStatus, type AuthUser } from "@/lib/api";

type AuthContextValue = {
  loading: boolean;
  status: AuthStatus | null;
  user: AuthUser | null;
  isAdmin: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const pathname = usePathname();
  const router = useRouter();
  const onLogin = pathname === "/login";

  const refresh = useCallback(async () => {
    try {
      const next = await api.authStatus();
      setStatus(next);
    } catch {
      // Fail closed: без ответа статуса не открываем приложение
      setStatus({ auth_enabled: true, authenticated: false, user: null });
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
    if (status.auth_enabled && !status.authenticated && !onLogin) {
      router.replace("/login");
    }
    if (status.auth_enabled && status.authenticated && onLogin) {
      router.replace("/");
    }
  }, [loading, status, onLogin, router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      loading,
      status,
      user: status?.user ?? null,
      isAdmin: Boolean(status?.user?.is_admin) || (status != null && !status.auth_enabled),
      refresh,
      logout,
    }),
    [loading, status, refresh, logout]
  );

  const ready = !loading && status != null;
  const allowed =
    ready && (!status.auth_enabled || status.authenticated || onLogin);

  if (!ready || !allowed) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        {onLogin ? "Загрузка…" : "Проверка доступа…"}
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
