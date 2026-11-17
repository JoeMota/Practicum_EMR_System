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
  | "note:view_sensitive"
  | "referral:create"
  | "roster:import"
  | "audit:view"
  | "instructor:remove"
  | "course:create"
  | "course:manage_status"
  | "course:manage_access"
  | "user:manage_access"
  | "report:run"
  | "report:export_teaching"
  | "case:author"
  | "instructor:manage"
  | "portal:view"
  | "portal:edit";

const teaching: Action[] = [
  "patient:create", "patient:update_status", "patient:reset_practice",
  "encounter:advance", "note:cosign", "note:view_sensitive", "referral:create", "audit:view", "case:author", "report:export_teaching",
];

const matrix: Record<Role, Action[]> = {
  student: ["encounter:advance", "note:author", "referral:create"],
  instructor: teaching,
  course_coordinator: [...teaching, "instructor:manage"],
  admin: [
    "roster:import", "audit:view", "instructor:manage", "instructor:remove",
    "course:create", "course:manage_status", "course:manage_access", "user:manage_access",
    "report:run", "report:export_teaching", "note:view_sensitive",
  ],
  front_desk: [],
  patient: ["portal:view", "portal:edit"],
};

export function can(role: Role, action: Action): boolean {
  return matrix[role].includes(action);
}

export function homePathFor(role: Role): string {
  switch (role) {
    case "student":
    case "instructor":
    case "course_coordinator":
      return "/dashboard";
    case "admin":
      return "/admin";
    case "patient":
      return "/portal";
    default:
      return "/patients";
  }
}
