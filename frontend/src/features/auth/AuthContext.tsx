import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { courseIdsForRole } from "../../utils/permissions";
import { logout, setActingRole } from "../../api/auth";
import {
  readSession, refreshAccessToken, SESSION_EVENT, setSignedOutNotice, tokenExpiresAt, writeSession,
  type StoredSession,
} from "../../api/client";
import { AuthContext, type AuthCtx } from "./useSession";
import type { Role } from "../../types";

const IDLE_MS = 15 * 60 * 1000;

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
      signIn: (user, accessToken, mustChangePassword, refreshToken) => {
        const first = user.roles[0];
        const onlyCourse = user.roles.length === 1 && first?.courseIds.length === 1 ? first.courseIds[0] : undefined;
        persist({
          user,
          activeRole: first?.role ?? "student",
          courseId: onlyCourse,
          accessToken,
          refreshToken,
          mustChangePassword,
        });
      },
      signOut: () => {
        const refreshToken = sessionRef.current?.refreshToken;
        if (refreshToken) void logout(refreshToken).catch(() => undefined);
        persist(null);
      },
      clearPasswordChange: () => {
        if (!sessionRef.current) return;
        persist({ ...sessionRef.current, mustChangePassword: false });
      },
      switchRole: (role: Role) => {
        const current = sessionRef.current;
        if (!current) return;
        const keepCourse = current.courseId && courseIdsForRole(current.user, role).includes(current.courseId);
        const nextCourse = keepCourse ? current.courseId : undefined;
        persist({ ...current, activeRole: role, courseId: nextCourse });
        void setActingRole(role)
          .then((result) => {
            const live = sessionRef.current;
            if (!live) return;
            persist({
              ...live,
              user: result.user,
              activeRole: role,
              courseId: live.courseId && courseIdsForRole(result.user, role).includes(live.courseId)
                ? live.courseId
                : nextCourse,
              accessToken: result.accessToken,
              refreshToken: result.refreshToken ?? live.refreshToken,
              mustChangePassword: result.mustChangePassword,
            });
          })
          .catch(() => undefined);
      },
      selectCourse: (courseId) => {
        const current = sessionRef.current;
        if (current) persist({ ...current, courseId });
      },
    };
  }, [session, persist]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
