import { api } from "./client";
import type { AuthResponse } from "../types";

export interface ClientRegisterPayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  city?: string;
  state?: string;
}

export interface EducationInput {
  degree: string;
  institution: string;
  field_of_study?: string;
  year?: number;
}

export interface LanguageInput {
  language: string;
  proficiency?: string;
}

export interface LawyerRegisterPayload {
  email: string;
  password: string;
  full_name: string;
  oab_uf: string;
  oab_number: string;
  bio?: string;
  years_of_experience?: number;
  city?: string;
  state?: string;
  practice_area_ids: number[];
  educations: EducationInput[];
  languages: LanguageInput[];
}

export interface FirmRegisterPayload {
  email: string;
  password: string;
  legal_name: string;
  cnpj: string;
  oab_registration: string;
  description?: string;
  city?: string;
  state?: string;
  website?: string;
  practice_area_ids: number[];
  existing_lawyer_ids: number[];
  new_lawyers: LawyerRegisterPayload[];
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/auth/login", { email, password });
  return data;
}

export async function registerClient(payload: ClientRegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/register/client", payload);
  return data;
}

export async function registerLawyer(payload: LawyerRegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/register/lawyer", payload);
  return data;
}

export async function registerFirm(payload: FirmRegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/register/firm", payload);
  return data;
}
