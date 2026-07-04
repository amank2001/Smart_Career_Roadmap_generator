"use client";

/**
 * AppDataContext — caches profile and target role in-memory so pages
 * don't lose state on navigation and don't refetch data unnecessarily.
 *
 * Data is fetched once after the user is authenticated and can be
 * manually refreshed via the provided refresh functions.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import { useAuth } from "@/context/AuthContext";
import { getProfile, type Profile } from "@/lib/api";
import { getTargetRole } from "@/lib/api/target-role";
import type { TargetRole } from "@/types/target-role";

interface AppDataState {
  /** null = not loaded yet, undefined = loaded but nothing saved */
  profile: Profile | null | undefined;
  targetRole: TargetRole | null | undefined;
  isLoadingProfile: boolean;
  isLoadingTargetRole: boolean;
  refreshProfile: () => Promise<void>;
  refreshTargetRole: () => Promise<void>;
}

const AppDataContext = createContext<AppDataState | undefined>(undefined);

export function AppDataProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  // null = haven't fetched yet; undefined = fetched, nothing there; Profile = loaded
  const [profile, setProfile] = useState<Profile | null | undefined>(null);
  const [targetRole, setTargetRole] = useState<TargetRole | null | undefined>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isLoadingTargetRole, setIsLoadingTargetRole] = useState(false);

  // Track whether we've done the initial load for this auth session
  const initialLoadDone = useRef(false);

  const fetchProfile = useCallback(async () => {
    setIsLoadingProfile(true);
    try {
      const data = await getProfile();
      setProfile(data);
    } catch {
      // 404 or any error = treat as no profile
      setProfile(undefined);
    } finally {
      setIsLoadingProfile(false);
    }
  }, []);

  const fetchTargetRole = useCallback(async () => {
    setIsLoadingTargetRole(true);
    try {
      const data = await getTargetRole();
      setTargetRole(data ?? undefined);
    } catch {
      setTargetRole(undefined);
    } finally {
      setIsLoadingTargetRole(false);
    }
  }, []);

  // Initial load: runs once when auth is confirmed
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      // Reset on logout
      setProfile(null);
      setTargetRole(null);
      initialLoadDone.current = false;
      return;
    }
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;
    fetchProfile();
    fetchTargetRole();
  }, [isAuthenticated, authLoading, fetchProfile, fetchTargetRole]);

  return (
    <AppDataContext.Provider
      value={{
        profile,
        targetRole,
        isLoadingProfile,
        isLoadingTargetRole,
        refreshProfile: fetchProfile,
        refreshTargetRole: fetchTargetRole,
      }}
    >
      {children}
    </AppDataContext.Provider>
  );
}

export function useAppData(): AppDataState {
  const ctx = useContext(AppDataContext);
  if (!ctx) {
    throw new Error("useAppData must be used within an AppDataProvider");
  }
  return ctx;
}
