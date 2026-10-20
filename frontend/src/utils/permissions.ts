import type { Role, User } from "../types";

export function courseIdsForRole(user: User, role: Role): string[] {
  return [...new Set(user.roles.filter((assignment) => assignment.role === role).flatMap((assignment) => assignment.courseIds))];
}

export function uniqueRoles(user: User): Role[] {
  return [...new Set(user.roles.map((assignment) => assignment.role))];
}

export type Action =
  | "patient:create"
  | "patient:update_status"
  | "patient:reset_practice"
  | "encounter:advance"
  | "note:author"
  | "note:cosign"
  | "referral:create"
  | "roster:import"
  | "audit:view"
  | "instructor:remove"
  | "course:create"
  | "course:manage_status"
  | "course:manage_access"
  | "user:manage_access"
  | "report:run";

const matrix: Record<Role, Action[]> = {
  student: ["encounter:advance", "note:author", "referral:create"],
  instructor: [
    "patient:create", "patient:update_status", "patient:reset_practice",
    "encounter:advance", "note:cosign", "referral:create", "roster:import", "audit:view", "instructor:remove",
  ],
  admin: [
    "patient:create", "patient:update_status", "patient:reset_practice", "roster:import", "audit:view",
    "instructor:remove", "course:create", "course:manage_status", "course:manage_access", "user:manage_access", "report:run",
  ],
  front_desk: ["patient:create"],
  patient: [],
};

export function can(role: Role, action: Action): boolean {
  return matrix[role].includes(action);
}

export function homePathFor(role: Role): string {
  switch (role) {
    case "student":
    case "instructor":
      return "/dashboard";
    case "admin":
      return "/admin/courses";
    default:
      return "/patients";
  }
}
