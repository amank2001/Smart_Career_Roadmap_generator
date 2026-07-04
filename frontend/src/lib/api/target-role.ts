import type {
  TargetRole,
  TargetRoleRequirements,
  SkillRequirement,
  CustomRoleInput,
} from "@/types/target-role";
import { jsonAuthHeaders } from "./client";

const API_BASE = "/api/target-role";

export class TargetRoleApiError extends Error {
  public code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "TargetRoleApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? body;
    const code = detail?.error ?? "UNKNOWN";
    const message = detail?.message ?? "An unexpected error occurred";
    throw new TargetRoleApiError(code, message);
  }
  return response.json();
}

/**
 * Get the current user's saved target role (returns null if none set yet).
 * GET /api/target-role/requirements (no role_title param = returns saved role)
 */
export async function getTargetRole(): Promise<TargetRole | null> {
  const response = await fetch(`${API_BASE}/requirements`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? body;
    const code = detail?.error ?? "UNKNOWN";
    const message = detail?.message ?? "An unexpected error occurred";
    throw new TargetRoleApiError(code, message);
  }
  // /requirements returns TargetRoleRequirements shape; wrap into TargetRole-compatible
  const data = await response.json();
  // If no target role saved, backend returns empty/404-style; treat as null
  if (!data || !data.role_title) return null;
  return data as unknown as TargetRole;
}

/**
 * Set the target role for the authenticated user.
 * POST /api/target-role
 */
export async function setTargetRole(roleTitle: string): Promise<TargetRole> {
  const response = await fetch(API_BASE, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify({ role_title: roleTitle }),
  });
  return handleResponse<TargetRole>(response);
}

/**
 * Get the skills/competencies for a role.
 * GET /api/target-role/requirements?role_title=...
 */
export async function getTargetRoleRequirements(
  roleTitle: string
): Promise<TargetRoleRequirements> {
  const params = new URLSearchParams({ role_title: roleTitle });
  const response = await fetch(`${API_BASE}/requirements?${params}`, {
    method: "GET",
    headers: jsonAuthHeaders(),
  });
  return handleResponse<TargetRoleRequirements>(response);
}

/**
 * Update the skills for the user's target role.
 * PUT /api/target-role/skills
 */
export async function updateTargetRoleSkills(
  skills: SkillRequirement[]
): Promise<TargetRole> {
  const response = await fetch(`${API_BASE}/skills`, {
    method: "PUT",
    headers: jsonAuthHeaders(),
    body: JSON.stringify({ skills }),
  });
  return handleResponse<TargetRole>(response);
}

/**
 * Set a custom role for unrecognized role titles.
 * POST /api/target-role/custom
 */
export async function setCustomRole(data: CustomRoleInput): Promise<TargetRole> {
  const response = await fetch(`${API_BASE}/custom`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<TargetRole>(response);
}
