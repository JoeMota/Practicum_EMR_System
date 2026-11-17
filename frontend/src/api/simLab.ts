import { request } from "./client";

export type SimLabRoomKind = "ward" | "big_lab" | "testing" | "exam";

export interface SimLabRoom {
  id: string;
  number: string;
  label: string;
  kind: SimLabRoomKind;
  bedCount: number;
  timing: "day" | "hour";
  sortOrder: number;
  mapX: number;
  mapY: number;
  mapW: number;
  mapH: number;
  softCapacity?: number | null;
  bedOptions: string[];
}

export interface SimLabAssignment {
  id: string;
  courseId: string;
  userId: string;
  studentName: string;
  room: SimLabRoom;
  sessionDate: string;
  bed?: string | null;
  roleLabel?: string | null;
  timeBlock?: string | null;
  assignedByName: string;
  createdAt: string;
}

export function listSimLabRooms(courseId: string, role: string): Promise<SimLabRoom[]> {
  return request<SimLabRoom[]>(`/courses/${courseId}/sim-lab/rooms`, { query: { role } });
}

export function listSimLabAssignments(
  courseId: string, role: string, sessionDate: string,
): Promise<SimLabAssignment[]> {
  return request<SimLabAssignment[]>(`/courses/${courseId}/sim-lab/assignments`, {
    query: { role, session_date: sessionDate },
  });
}

export function mySimLabAssignments(
  courseId: string, role: string, sessionDate?: string,
): Promise<SimLabAssignment[]> {
  return request<SimLabAssignment[]>(`/courses/${courseId}/sim-lab/mine`, {
    query: { role, session_date: sessionDate },
  });
}

export function assignSimLab(
  courseId: string,
  role: string,
  body: {
    userId: string;
    roomId: string;
    sessionDate: string;
    bed?: string;
    roleLabel?: string;
    timeBlock?: string;
  },
): Promise<SimLabAssignment> {
  return request<SimLabAssignment>(`/courses/${courseId}/sim-lab/assignments`, {
    method: "POST",
    query: { role },
    json: body,
  });
}

export function clearSimLabAssignment(
  courseId: string, role: string, assignmentId: string,
): Promise<SimLabAssignment> {
  return request<SimLabAssignment>(
    `/courses/${courseId}/sim-lab/assignments/${assignmentId}/clear`,
    { method: "POST", query: { role } },
  );
}

export function assignmentSummary(row: SimLabAssignment): string {
  const parts = [`Room ${row.room.number}`];
  if (row.bed) parts.push(`Bed ${row.bed}`);
  if (row.roleLabel) parts.push(row.roleLabel);
  if (row.timeBlock) parts.push(row.timeBlock);
  else if (row.room.timing === "day") parts.push("Today");
  return parts.join(" · ");
}
