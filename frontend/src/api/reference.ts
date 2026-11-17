import type { IcdCode } from "../types";
import { request } from "./client";

export function searchIcd10(q: string): Promise<IcdCode[]> {
  return request<IcdCode[]>("/reference/icd10", { query: { q } });
}

export function searchMedications(q: string): Promise<{ name: string; rxcui: string }[]> {
  return request<{ name: string; rxcui: string }[]>("/reference/medications", { query: { q } });
}

export function medicationDetails(rxcui: string): Promise<{ rxcui: string; genericName: string; brandNames: string[] }> {
  return request(`/reference/medications/${rxcui}`);
}

export function listCpt(q = ""): Promise<IcdCode[]> {
  return request<IcdCode[]>("/reference/cpt", { query: { q } });
}

export interface LexicompStatus {
  configured: boolean;
  url?: string | null;
  detail: string;
}

export function lexicompStatus(): Promise<LexicompStatus> {
  return request<LexicompStatus>("/reference/lexicomp");
}

export interface LexicompInteractions {
  configured: boolean;
  text: string | null;
}

export function lexicompInteractions(medications: string[]): Promise<LexicompInteractions> {
  return request<LexicompInteractions>("/reference/lexicomp/interactions", {
    method: "POST",
    json: { medications },
  });
}
