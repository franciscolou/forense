import { api } from "./client";
import type {
  AgendaVisibility,
  ApprovalMode,
  AvailabilityException,
  AvailabilityRule,
  BookingConfiguration,
  PaymentMode,
  QuestionType,
  Schedule,
  TriageMode,
} from "../types";

export interface ConfigUpdate {
  triage_mode: TriageMode;
  agenda_visibility: AgendaVisibility;
  approval_mode: ApprovalMode;
  payment_mode: PaymentMode;
  min_advance_days: number;
  max_advance_days: number;
}

export interface QuestionInput {
  text: string;
  qtype: QuestionType;
  options: string[];
  order: number;
  required: boolean;
  is_active: boolean;
}

export async function getMyConfig(): Promise<BookingConfiguration> {
  const { data } = await api.get<BookingConfiguration>("/me/booking-configuration");
  return data;
}

export async function updateMyConfig(payload: ConfigUpdate): Promise<BookingConfiguration> {
  const { data } = await api.put<BookingConfiguration>("/me/booking-configuration", payload);
  return data;
}

export async function addQuestion(payload: QuestionInput): Promise<BookingConfiguration> {
  const { data } = await api.post<BookingConfiguration>(
    "/me/booking-configuration/questions",
    payload,
  );
  return data;
}

export async function updateQuestion(
  id: number,
  payload: QuestionInput,
): Promise<BookingConfiguration> {
  const { data } = await api.put<BookingConfiguration>(
    `/me/booking-configuration/questions/${id}`,
    payload,
  );
  return data;
}

export async function deleteQuestion(id: number): Promise<BookingConfiguration> {
  const { data } = await api.delete<BookingConfiguration>(
    `/me/booking-configuration/questions/${id}`,
  );
  return data;
}

// --- Availability schedule (recurring rules + exception blocks) --------
export async function getMyAvailability(): Promise<Schedule> {
  const { data } = await api.get<Schedule>("/me/availability");
  return data;
}

export async function saveRules(rules: AvailabilityRule[]): Promise<Schedule> {
  const payload = {
    rules: rules.map((r) => ({
      weekday: r.weekday,
      start_hour: r.start_hour,
      end_hour: r.end_hour,
    })),
  };
  const { data } = await api.put<Schedule>("/me/availability/rules", payload);
  return data;
}

export async function addException(
  start_at: string,
  end_at: string,
  note?: string,
): Promise<AvailabilityException> {
  const { data } = await api.post<AvailabilityException>("/me/availability/exceptions", {
    start_at,
    end_at,
    note,
  });
  return data;
}

export async function deleteException(id: number): Promise<void> {
  await api.delete(`/me/availability/exceptions/${id}`);
}
