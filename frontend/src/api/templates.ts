import type { Discipline, Role } from "../types";
import type { TemplateSection } from "../features/encounters/noteTemplates";
import { request } from "./client";

export interface SavedNoteTemplate {
  id: string;
  name: string;
  discipline: Discipline;
  scope: "shared" | "course";
  sensitive: boolean;
  sections: TemplateSection[];
}

export function listNoteTemplates(role: Role, courseId?: string): Promise<SavedNoteTemplate[]> {
  return request<SavedNoteTemplate[]>("/note-templates", { query: { role, course_id: courseId } });
}

export function createNoteTemplate(
  role: Role,
  body: { name: string; discipline: Discipline; courseId?: string; sensitive: boolean; sections: TemplateSection[] },
): Promise<SavedNoteTemplate> {
  return request<SavedNoteTemplate>("/note-templates", { method: "POST", query: { role }, json: body });
}
