import { api } from "./client";
import type {
  FirmDetail,
  FirmSummary,
  LawyerDetail,
  LawyerSummary,
  Page,
  PracticeArea,
} from "../types";

export interface SearchParams {
  practice_area_id?: number | null;
  q?: string | null;
  page?: number;
  page_size?: number;
}

function cleanParams(params: SearchParams): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (params.practice_area_id) out.practice_area_id = params.practice_area_id;
  if (params.q) out.q = params.q;
  if (params.page) out.page = params.page;
  if (params.page_size) out.page_size = params.page_size;
  return out;
}

export async function listPracticeAreas(): Promise<PracticeArea[]> {
  const { data } = await api.get<PracticeArea[]>("/practice-areas");
  return data;
}

export async function searchLawyers(params: SearchParams): Promise<Page<LawyerSummary>> {
  const { data } = await api.get<Page<LawyerSummary>>("/lawyers", { params: cleanParams(params) });
  return data;
}

export async function getLawyer(id: number): Promise<LawyerDetail> {
  const { data } = await api.get<LawyerDetail>(`/lawyers/${id}`);
  return data;
}

export async function searchFirms(params: SearchParams): Promise<Page<FirmSummary>> {
  const { data } = await api.get<Page<FirmSummary>>("/firms", { params: cleanParams(params) });
  return data;
}

export async function getFirm(id: number): Promise<FirmDetail> {
  const { data } = await api.get<FirmDetail>(`/firms/${id}`);
  return data;
}
