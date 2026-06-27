/**
 * Shared API client utilities used by all API modules.
 * Centralizes auth header injection and error handling.
 */

import { getToken } from "@/lib/auth";

/**
 * Returns headers with Authorization token if available.
 */
export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Returns standard JSON headers with auth.
 */
export function jsonAuthHeaders(): Record<string, string> {
  return authHeaders({ "Content-Type": "application/json" });
}
