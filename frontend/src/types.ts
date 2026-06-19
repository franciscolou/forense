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
  user_id: number;
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
  user_id: number;
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

// --- Booking ------------------------------------------------------------
export type TriageMode = "disabled" | "optional" | "required";
export type AgendaVisibility = "immediate" | "after_triage" | "hidden";
export type ApprovalMode = "automatic" | "manual";
export type PaymentMode = "none" | "before_confirmation" | "after_confirmation";

export type QuestionType = "text" | "boolean" | "single_choice" | "multi_choice";

export interface TriageQuestion {
  id: number;
  text: string;
  qtype: QuestionType;
  options: string[];
  order: number;
  required: boolean;
  is_active: boolean;
}

export interface ConfigSnapshot {
  triage_mode: TriageMode;
  agenda_visibility: AgendaVisibility;
  approval_mode: ApprovalMode;
  payment_mode: PaymentMode;
}

export interface StepDescriptor {
  key: "triage" | "agenda" | "approval" | "payment";
  actor: "client" | "provider";
  action: string;
  label: string;
  required?: boolean | null;
  after_confirmation?: boolean | null;
}

export interface PublicFlow {
  provider_user_id: number;
  provider_name: string;
  config: ConfigSnapshot;
  steps: StepDescriptor[];
  questions: TriageQuestion[];
}

export interface BookingConfiguration extends ConfigSnapshot {
  id: number;
  min_advance_days: number;
  max_advance_days: number;
  questions: TriageQuestion[];
}

export interface Slot {
  id: number;
  start_at: string;
  end_at: string;
  is_booked: boolean;
}

// A derived, bookable one-hour window (no id until reserved).
export interface OpenSlot {
  start_at: string;
  end_at: string;
}

// Recurring weekly availability window (weekday 0=Mon … 6=Sun, hour grid).
export interface AvailabilityRule {
  id?: number;
  weekday: number;
  start_hour: number;
  end_hour: number;
}

export interface AvailabilityException {
  id: number;
  start_at: string;
  end_at: string;
  note: string | null;
}

export interface Schedule {
  rules: AvailabilityRule[];
  exceptions: AvailabilityException[];
}

export type BookingStatus =
  | "pending"
  | "awaiting_approval"
  | "confirmed"
  | "rejected"
  | "cancelled"
  | "completed";

export type PaymentState = "not_required" | "pending" | "paid";

export interface TriageAnswerRead {
  question_id: number;
  question_text: string;
  value: unknown;
}

export interface Booking {
  id: number;
  status: BookingStatus;
  current_step: string | null;
  pending_action: StepDescriptor | null;
  config: ConfigSnapshot;
  provider: { id: number; full_name: string };
  client: { id: number; full_name: string };
  slot: Slot | null;
  scheduled_at: string | null;
  payment_state: PaymentState;
  notes: string | null;
  resolution_reason: string | null;
  triage_response: { id: number; answers: TriageAnswerRead[] } | null;
  created_at: string;
}
