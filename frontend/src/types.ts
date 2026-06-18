// Shared types mirroring the backend schemas.

export type UserRole = "client" | "lawyer" | "firm";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface AuthResponse {
  token: { access_token: string; token_type: string };
  user: User;
}

export interface PracticeArea {
  id: number;
  name: string;
  slug: string;
}

export interface Education {
  id: number;
  degree: string;
  institution: string;
  field_of_study: string | null;
  year: number | null;
}

export interface Language {
  id: number;
  language: string;
  proficiency: string | null;
}

export interface LawyerSummary {
  id: number;
  full_name: string;
  oab_uf: string;
  oab_number: string;
  years_of_experience: number | null;
  city: string | null;
  state: string | null;
  photo_url: string | null;
  practice_areas: PracticeArea[];
}

export interface LawyerDetail extends LawyerSummary {
  email: string;
  oab_verified: boolean;
  bio: string | null;
  educations: Education[];
  languages: Language[];
}

export interface FirmSummary {
  id: number;
  legal_name: string;
  city: string | null;
  state: string | null;
  logo_url: string | null;
  practice_areas: PracticeArea[];
}

export interface FirmDetail extends FirmSummary {
  cnpj: string;
  oab_registration: string;
  email: string;
  description: string | null;
  website: string | null;
  lawyers: LawyerSummary[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
