import { api } from "./client";
import type { Booking, OpenSlot, PublicFlow } from "../types";

export interface TriageAnswerInput {
  question_id: number;
  value: unknown;
}

export async function getPublicFlow(providerUserId: number): Promise<PublicFlow> {
  const { data } = await api.get<PublicFlow>(`/providers/${providerUserId}/booking-flow`);
  return data;
}

export async function getOpenSlots(providerUserId: number): Promise<OpenSlot[]> {
  const { data } = await api.get<OpenSlot[]>(`/providers/${providerUserId}/slots`);
  return data;
}

export async function initiateBooking(
  providerUserId: number,
  notes?: string,
): Promise<Booking> {
  const { data } = await api.post<Booking>("/bookings", {
    provider_user_id: providerUserId,
    notes,
  });
  return data;
}

export async function submitTriage(
  bookingId: number,
  answers: TriageAnswerInput[],
): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/triage`, { answers });
  return data;
}

export async function selectSlot(bookingId: number, startAt: string): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/slot`, { start_at: startAt });
  return data;
}

export async function submitPayment(bookingId: number): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/payment`, {});
  return data;
}

export async function listMyBookings(): Promise<Booking[]> {
  const { data } = await api.get<Booking[]>("/bookings");
  return data;
}

export async function approveBooking(bookingId: number): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/approve`, {});
  return data;
}

export async function rejectBooking(bookingId: number, reason?: string): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/reject`, { reason });
  return data;
}

export async function cancelBooking(bookingId: number, reason?: string): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/cancel`, { reason });
  return data;
}

export async function completeBooking(bookingId: number): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/complete`, {});
  return data;
}
