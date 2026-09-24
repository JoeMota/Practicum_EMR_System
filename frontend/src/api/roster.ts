import type { Discipline, RosterRow, User } from "../types";
import { ApiError, USE_MOCK, apiFetch, clone, latency, uid } from "./client";
import { db } from "./mockDb";
import { recordAudit } from "./audit";

export async function listRoster(courseId: string): Promise<User[]> {
  if (!USE_MOCK) return apiFetch<User[]>(`/courses/${courseId}/roster`);
  await latency(150);
  return clone(
    db.users.filter((u) =>
      u.roles.some((r) => (r.role === "student" || r.role === "instructor") && r.courseIds.includes(courseId)),
    ),
  );
}

export async function addRosterMember(
  actor: User,
  courseId: string,
  input: {
    fullName: string;
    email: string;
    universityId?: string;
    discipline: Discipline;
    appRole: "student" | "instructor";
  },
): Promise<{ created: boolean; alreadyEnrolled: boolean; user: User }> {
  if (!USE_MOCK) {
    return apiFetch<{ created: boolean; alreadyEnrolled: boolean; user: User }>(
      `/courses/${courseId}/roster/members`,
      {
        method: "POST",
        body: {
          fullName: input.fullName.trim(),
          email: input.email.trim().toLowerCase(),
          universityId: input.universityId?.trim() || undefined,
          discipline: input.discipline,
          appRole: input.appRole,
        },
      },
    );
  }
  await latency(250);
  const email = input.email.trim().toLowerCase();
  if (!/@(miners\.)?utep\.edu$/i.test(email)) {
    throw new ApiError(400, "Use a UTEP email (@utep.edu or @miners.utep.edu).");
  }
  let user = db.users.find((u) => u.email.toLowerCase() === email);
  let created = false;
  if (!user) {
    user = {
      id: uid("u"),
      fullName: input.fullName.trim(),
      email,
      universityId: input.universityId?.trim() || undefined,
      roles: [],
      mustChangePassword: true,
    };
    db.users.push(user);
    created = true;
  }
  let assignment = user.roles.find(
    (r) => r.role === input.appRole && (input.appRole === "instructor" || r.discipline === input.discipline),
  );
  if (!assignment) {
    assignment = {
      role: input.appRole,
      discipline: input.appRole === "student" ? input.discipline : undefined,
      courseIds: [],
    };
    user.roles.push(assignment);
  }
  let alreadyEnrolled = false;
  if (assignment.courseIds.includes(courseId)) {
    alreadyEnrolled = true;
  } else {
    assignment.courseIds.push(courseId);
  }
  recordAudit(actor, "roster.add_member", `course/${courseId}`, "ok", `${email} as ${input.appRole}`);
  return { created, alreadyEnrolled, user: clone(user) };
}

export async function importRoster(
  actor: User, courseId: string, discipline: Discipline, rows: RosterRow[],
): Promise<{ added: number; alreadyEnrolled: number }> {
  if (!USE_MOCK) {
    return apiFetch<{ added: number; alreadyEnrolled: number }>(`/courses/${courseId}/roster/import`, {
      method: "POST",
      body: {
        discipline,
        rows: rows.map((r) => ({
          fullName: r.fullName,
          email: r.email,
          universityId: r.universityId,
          ...(r.problem ? { problem: r.problem } : {}),
        })),
      },
    });
  }
  await latency(400);
  if (rows.some((r) => r.problem)) throw new ApiError(400, "Fix the flagged rows before importing.");
  let added = 0;
  let alreadyEnrolled = 0;
  for (const row of rows) {
    let user = db.users.find((u) => u.email.toLowerCase() === row.email.toLowerCase());
    if (!user) {
      user = { id: uid("u"), fullName: row.fullName, email: row.email, universityId: row.universityId, roles: [] };
      db.users.push(user);
    }
    let assignment = user.roles.find((r) => r.role === "student" && r.discipline === discipline);
    if (!assignment) {
      assignment = { role: "student", discipline, courseIds: [] };
      user.roles.push(assignment);
    }
    if (assignment.courseIds.includes(courseId)) {
      alreadyEnrolled++;
    } else {
      assignment.courseIds.push(courseId);
      added++;
    }
  }
  recordAudit(actor, "roster.import", `course/${courseId}`, "ok", `${added} added, ${alreadyEnrolled} already enrolled`);
  return { added, alreadyEnrolled };
}

export async function removeFromCourse(actor: User, courseId: string, userId: string): Promise<void> {
  if (!USE_MOCK) {
    await apiFetch<void>(`/courses/${courseId}/roster/${userId}`, { method: "DELETE" });
    return;
  }
  await latency(200);
  const user = db.users.find((u) => u.id === userId);
  user?.roles.forEach((r) => {
    if (r.role === "student" || r.role === "instructor") {
      r.courseIds = r.courseIds.filter((c) => c !== courseId);
    }
  });
  recordAudit(actor, "roster.remove", `course/${courseId}`, "ok", `user/${userId}`);
}
