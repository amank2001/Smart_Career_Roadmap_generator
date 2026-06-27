/**
 * Client-side validation matching backend constraints.
 */

export const CONSTRAINTS = {
  JOB_TITLE_MAX: 100,
  EXPERIENCE_MIN: 0,
  EXPERIENCE_MAX: 50,
  SKILLS_MIN: 1,
  SKILLS_MAX: 50,
  SKILL_NAME_MAX: 60,
  RESUME_MAX_SIZE_BYTES: 5 * 1024 * 1024, // 5 MB
  RESUME_ACCEPTED_TYPES: [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
  ],
  RESUME_ACCEPTED_EXTENSIONS: [".pdf", ".docx", ".txt"],
  ROLE_TITLE_MAX: 100,
  CUSTOM_ROLE_SKILLS_MIN: 3,
} as const;

export interface ValidationError {
  field: string;
  message: string;
}

export function validateJobTitle(title: string): string | null {
  if (!title.trim()) return "Job title is required";
  if (title.length > CONSTRAINTS.JOB_TITLE_MAX)
    return `Job title must be ${CONSTRAINTS.JOB_TITLE_MAX} characters or fewer`;
  return null;
}

export function validateExperience(years: number | string): string | null {
  const num = typeof years === "string" ? parseInt(years, 10) : years;
  if (isNaN(num)) return "Years of experience must be a number";
  if (!Number.isInteger(num)) return "Years of experience must be a whole number";
  if (num < CONSTRAINTS.EXPERIENCE_MIN || num > CONSTRAINTS.EXPERIENCE_MAX)
    return `Years of experience must be between ${CONSTRAINTS.EXPERIENCE_MIN} and ${CONSTRAINTS.EXPERIENCE_MAX}`;
  return null;
}

export function validateSkillName(name: string): string | null {
  if (!name.trim()) return "Skill name cannot be empty";
  if (name.length > CONSTRAINTS.SKILL_NAME_MAX)
    return `Skill name must be ${CONSTRAINTS.SKILL_NAME_MAX} characters or fewer`;
  return null;
}

export function validateSkillCount(count: number): string | null {
  if (count < CONSTRAINTS.SKILLS_MIN)
    return "At least one skill is required";
  if (count > CONSTRAINTS.SKILLS_MAX)
    return `Maximum ${CONSTRAINTS.SKILLS_MAX} skills allowed`;
  return null;
}

export function validateResumeFile(file: File): string | null {
  if (file.size > CONSTRAINTS.RESUME_MAX_SIZE_BYTES) {
    return "File size must be 5 MB or less";
  }

  const extension = "." + file.name.split(".").pop()?.toLowerCase();
  const isValidExtension = (CONSTRAINTS.RESUME_ACCEPTED_EXTENSIONS as readonly string[]).includes(extension);
  const isValidType = (CONSTRAINTS.RESUME_ACCEPTED_TYPES as readonly string[]).includes(file.type);

  // Check both extension and MIME type - accept if either matches
  if (!isValidExtension && !isValidType) {
    return "Supported formats: PDF, DOCX, plain text";
  }

  return null;
}

export function validateRoleTitle(title: string): string | null {
  if (!title.trim()) return "Role title is required";
  if (title.length > CONSTRAINTS.ROLE_TITLE_MAX)
    return `Role title must be ${CONSTRAINTS.ROLE_TITLE_MAX} characters or fewer`;
  return null;
}

export function validateCustomRoleSkillCount(count: number): string | null {
  if (count < CONSTRAINTS.CUSTOM_ROLE_SKILLS_MIN)
    return `At least ${CONSTRAINTS.CUSTOM_ROLE_SKILLS_MIN} skills are required for a custom role`;
  return null;
}

export function validateResponsibilities(text: string): string | null {
  if (!text.trim()) return "Responsibilities description is required";
  return null;
}
