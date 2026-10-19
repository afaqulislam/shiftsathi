"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api } from "./api";
import { tokenStore } from "./token";
import type { Me } from "./types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (body: {
    organization_name: string;
    full_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      setMe(await api.me());
    } catch {
      tokenStore.clear();
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const token = await api.login({ email, password });
    tokenStore.set(token.access_token);
    setMe(await api.me());
  }, []);

  const register = useCallback(
    async (body: {
      organization_name: string;
      full_name: string;
      email: string;
      password: string;
    }) => {
      const token = await api.register(body);
      tokenStore.set(token.access_token);
      setMe(await api.me());
    },
    [],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setMe(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ me, loading, login, register, logout, refresh }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
