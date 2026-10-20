import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Discipline, Role, RoleAssignment, User } from "../../types";
import { courseIdsForRole } from "../../utils/permissions";
import {
  readSession, refreshAccessToken, SESSION_EVENT, setSignedOutNotice, tokenExpiresAt, writeSession,
  type StoredSession,
} from "../../api/client";

const IDLE_MS = 15 * 60 * 1000;

interface AuthCtx {
  session: StoredSession | null;
  user: User | null;
  activeRole: Role | null;
  assignment: RoleAssignment | null;
  discipline: Discipline | undefined;
  courseId: string | undefined;
  signIn: (user: User, accessToken: string, mustChangePassword: boolean) => void;
  signOut: () => void;
  clearPasswordChange: () => void;
  switchRole: (role: Role) => void;
  selectCourse: (courseId: string) => void;
}

const AuthContext = createContext<AuthCtx | null>(null);

function load(): StoredSession | null {
  const session = readSession();
  if (!session) return null;
  const exp = tokenExpiresAt(session.accessToken);
  if (exp !== null && exp <= Date.now()) {
    writeSession(null, false);
    return null;
  }
  return session;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(load);
  const sessionRef = useRef(session);

  const persist = useCallback((next: StoredSession | null) => {
    setSession(next);
    writeSession(next, false);
  }, []);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    const sync = () => setSession(readSession());
    window.addEventListener(SESSION_EVENT, sync);
    return () => window.removeEventListener(SESSION_EVENT, sync);
  }, []);

  const accessToken = session?.accessToken;
  useEffect(() => {
    if (!accessToken) return;

    let idle = 0;
    const arm = () => {
      window.clearTimeout(idle);
      idle = window.setTimeout(() => {
        setSignedOutNotice("You were signed out after 15 minutes of inactivity.");
        persist(null);
      }, IDLE_MS);
    };

    let lastRefreshCheck = 0;
    const onActivity = () => {
      arm();
      const now = Date.now();
      if (now - lastRefreshCheck < 30_000) return;
      lastRefreshCheck = now;
      const token = sessionRef.current?.accessToken;
      const exp = token ? tokenExpiresAt(token) : null;
      if (exp !== null && exp - now < 5 * 60 * 1000) void refreshAccessToken();
    };

    arm();
    const events = ["pointerdown", "keydown"] as const;
    events.forEach((name) => window.addEventListener(name, onActivity));
    return () => {
      window.clearTimeout(idle);
      events.forEach((name) => window.removeEventListener(name, onActivity));
    };
  }, [accessToken, persist]);

  const value = useMemo<AuthCtx>(() => {
    const assignment = session?.user.roles.find((r) => r.role === session.activeRole) ?? null;
    return {
      session,
      user: session?.user ?? null,
      activeRole: session?.activeRole ?? null,
      assignment,
      discipline: assignment?.discipline,
      courseId: session?.courseId,
      signIn: (user, accessToken, mustChangePassword) => {
        const first = user.roles[0];
        const onlyCourse = user.roles.length === 1 && first?.courseIds.length === 1 ? first.courseIds[0] : undefined;
        persist({
          user,
          activeRole: first?.role ?? "student",
          courseId: onlyCourse,
          accessToken,
          mustChangePassword,
        });
      },
      signOut: () => persist(null),
      clearPasswordChange: () => {
        if (!sessionRef.current) return;
        persist({ ...sessionRef.current, mustChangePassword: false });
      },
      switchRole: (role) => {
        const current = sessionRef.current;
        if (!current) return;
        const keepCourse = current.courseId && courseIdsForRole(current.user, role).includes(current.courseId);
        persist({ ...current, activeRole: role, courseId: keepCourse ? current.courseId : undefined });
      },
      selectCourse: (courseId) => {
        const current = sessionRef.current;
        if (current) persist({ ...current, courseId });
      },
    };
  }, [session, persist]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

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
