import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Discipline, Role, RoleAssignment, User } from "../../types";
import { clearSessionToken } from "../../api/auth";

interface Session {
  user: User;
  activeRole: Role;
  courseId?: string;
}

interface AuthCtx {
  session: Session | null;
  user: User | null;
  activeRole: Role | null;
  assignment: RoleAssignment | null;
  discipline: Discipline | undefined;
  courseId: string | undefined;
  signIn: (user: User) => void;
  signOut: () => void;
  switchRole: (role: Role) => void;
  selectCourse: (courseId: string) => void;
}

const KEY = "emr.session";
const AuthContext = createContext<AuthCtx | null>(null);

function load(): Session | null {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? "null");
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(load);

  const persist = useCallback((s: Session | null) => {
    setSession(s);
    try {
      if (s) sessionStorage.setItem(KEY, JSON.stringify(s));
      else sessionStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo<AuthCtx>(() => {
    const assignment = session?.user.roles.find((r) => r.role === session.activeRole) ?? null;
    return {
      session,
      user: session?.user ?? null,
      activeRole: session?.activeRole ?? null,
      assignment,
      discipline: assignment?.discipline,
      courseId: session?.courseId,
      signIn: (user) => {
        const first = user.roles[0];
        if (!first) {
          persist(null);
          return;
        }
        const onlyCourse = user.roles.length === 1 && first.courseIds.length === 1 ? first.courseIds[0] : undefined;
        persist({ user, activeRole: first.role, courseId: onlyCourse });
      },
      signOut: () => {
        clearSessionToken();
        persist(null);
      },
      switchRole: (role) => {
        if (!session) return;
        const next = session.user.roles.find((r) => r.role === role);
        const keepCourse = session.courseId && next?.courseIds.includes(session.courseId);
        persist({ ...session, activeRole: role, courseId: keepCourse ? session.courseId : undefined });
      },
      selectCourse: (courseId) => session && persist({ ...session, courseId }),
    };
  }, [session, persist]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** For pages behind RequireAuth, where a session is guaranteed. */
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
