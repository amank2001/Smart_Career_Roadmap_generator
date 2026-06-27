"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getToken, isAuthenticated as checkAuth, logout as clearAuth } from "@/lib/auth";

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
  setAuthenticated: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    // Check stored token on mount
    const stored = getToken();
    if (stored) {
      setIsAuthenticated(true);
      setToken(stored);
    }
    setIsLoading(false);
  }, []);

  const handleSetAuthenticated = useCallback(() => {
    const stored = getToken();
    setIsAuthenticated(true);
    setToken(stored);
  }, []);

  const handleLogout = useCallback(() => {
    clearAuth();
    setIsAuthenticated(false);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        token,
        setAuthenticated: handleSetAuthenticated,
        logout: handleLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
