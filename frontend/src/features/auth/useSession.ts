import { createContext, useContext } from "react";
import type { Discipline, Role, RoleAssignment, User } from "../../types";
import type { StoredSession } from "../../api/client";

export interface AuthCtx {
  session: StoredSession | null;
  user: User | null;
  activeRole: Role | null;
  assignment: RoleAssignment | null;
  discipline: Discipline | undefined;
  courseId: string | undefined;
  signIn: (user: User, accessToken: string, mustChangePassword: boolean, refreshToken?: string) => void;
  signOut: () => void;
  clearPasswordChange: () => void;
  switchRole: (role: Role) => void;
  selectCourse: (courseId: string) => void;
}

export const AuthContext = createContext<AuthCtx | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function useSession() {
  const ctx = useAuth();
  if (!ctx.user || !ctx.activeRole) throw new Error("No active session");
  return {
    ...ctx,
    user: ctx.user,
    activeRole: ctx.activeRole,
    courseId: ctx.courseId ?? "",
  };
}
