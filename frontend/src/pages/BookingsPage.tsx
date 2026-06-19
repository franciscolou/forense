import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  approveBooking,
  assignLawyer,
  cancelBooking,
  completeBooking,
  getMyFirmLawyers,
  getOpenSlots,
  listMyBookings,
  rejectBooking,
} from "../api/bookings";
import { addException, deleteException, getMyAvailability } from "../api/bookingConfig";
import { errorMessage } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import { CloseIcon } from "../components/icons";
import { Spinner, initials } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import type {
  AvailabilityException,
  Booking,
  BookingStatus,
  LawyerOption,
  OpenSlot,
  TriageAnswerRead,
} from "../types";

const STATUS_LABEL: Record<BookingStatus, string> = {
  pending: "Em andamento",
  awaiting_approval: "Aguardando aprovação",
  confirmed: "Confirmado",
  rejected: "Recusado",
  cancelled: "Cancelado",
  completed: "Concluído",
};

// Times follow the platform-UTC convention (same as the agenda/grid).
const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    timeZone: "UTC",
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

const CANCELLABLE: BookingStatus[] = ["pending", "awaiting_approval", "confirmed"];
const REJECTABLE: BookingStatus[] = ["pending", "awaiting_approval"];

function fmtAnswer(value: unknown): string {
  if (value === true) return "Sim";
  if (value === false) return "Não";
  if (Array.isArray(value)) return value.join(", ");
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

// --- Calendar helpers (platform-UTC convention, like the agenda picker) ---
const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;
const WEEKDAY_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const MONTH_SHORT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

const hourLabel = (iso: string) =>
  new Date(iso).toLocaleTimeString("pt-BR", { timeZone: "UTC", hour: "2-digit", minute: "2-digit" });

const dateKey = (iso: string) => iso.slice(0, 10);
const fmtDayNum = (d: Date) => `${String(d.getUTCDate()).padStart(2, "0")}/${MONTH_SHORT[d.getUTCMonth()]}`;

// Monday 00:00 UTC of the week containing `d`.
function mondayOfUTC(d: Date): Date {
  const mondayOffset = (d.getUTCDay() + 6) % 7; // Sun=0 → 6, Mon=1 → 0, …
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - mondayOffset));
}

export default function BookingsPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [firmLawyers, setFirmLawyers] = useState<LawyerOption[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading) return;
    if (!user) {
      navigate("/entrar");
      return;
    }
    listMyBookings()
      .then(setBookings)
      .catch((e) => setError(errorMessage(e)));
    // Firms may need to assign a responsible lawyer to received bookings.
    if (user.role === "firm") {
      getMyFirmLawyers()
        .then(setFirmLawyers)
        .catch((e) => setError(errorMessage(e)));
    }
  }, [user, loading, navigate]);

  if (loading || (!bookings && !error)) {
    return (
      <div className="container">
        <Spinner />
      </div>
    );
  }

  const isProvider = !!user && user.role !== "client";
  const isFirm = !!user && user.role === "firm";
  const replace = (b: Booking) =>
    setBookings((prev) => prev?.map((x) => (x.id === b.id ? b : x)) ?? null);

  // Provider view: a weekly calendar of free/blocked/booked slots + untimed requests.
  if (isProvider) {
    return (
      <div className="container" style={{ maxWidth: 1040 }}>
        <p style={{ marginTop: 16 }}>
          <Link to="/painel">← Painel</Link>
        </p>
        <h1>Agenda</h1>
        <p className="muted">
          Veja seus horários livres, bloqueados e agendamentos. Clique num horário livre para
          bloqueá-lo; clique num agendamento para ver os detalhes e gerenciá-lo.
        </p>
        {error && <div className="alert alert-error">{error}</div>}
        <ProviderCalendar
          bookings={bookings ?? []}
          isFirm={isFirm}
          firmLawyers={firmLawyers}
          providerUserId={user!.id}
          onChange={replace}
          setError={setError}
        />
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: 820 }}>
      <h1>Meus agendamentos</h1>
      <p className="muted">
        Acompanhe suas solicitações de atendimento e cancele quando precisar.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      {bookings && bookings.length === 0 && (
        <p className="muted">
          Você ainda não tem agendamentos. <Link to="/">Buscar profissionais</Link>
        </p>
      )}

      {bookings?.map((b) => (
        <BookingCard
          key={b.id}
          booking={b}
          isProvider={false}
          firmLawyers={firmLawyers}
          onChange={replace}
          setError={setError}
        />
      ))}
    </div>
  );
}

// Weekly calendar for providers: free slots (from their availability), blocked slots
// (exceptions they created), and booked slots (received bookings). Free → click to
// block; blocked → click to unblock; booked → click for full detail modal.
function ProviderCalendar({
  bookings,
  isFirm,
  firmLawyers,
  providerUserId,
  onChange,
  setError,
}: {
  bookings: Booking[];
  isFirm: boolean;
  firmLawyers: LawyerOption[];
  providerUserId: number;
  onChange: (b: Booking) => void;
  setError: (s: string) => void;
}) {
  const [openSlots, setOpenSlots] = useState<OpenSlot[]>([]);
  const [exceptions, setExceptions] = useState<AvailabilityException[]>([]);
  const [weekOffset, setWeekOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  // Free slot pending block confirmation.
  const [blocking, setBlocking] = useState<OpenSlot | null>(null);
  // Exception pending unblock confirmation.
  const [unblocking, setUnblocking] = useState<AvailabilityException | null>(null);
  const [busy, setBusy] = useState(false);

  const loadSlots = useCallback(() => {
    Promise.all([getOpenSlots(providerUserId), getMyAvailability()])
      .then(([slots, schedule]) => {
        setOpenSlots(slots);
        setExceptions(schedule.exceptions);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [providerUserId, setError]);

  useEffect(() => {
    loadSlots();
  }, [loadSlots]);

  // A booking change (cancel/reject/assign…) can free or move a slot, so refresh
  // the open slots too — keeps the calendar in sync without a page reload.
  const handleChange = (b: Booking) => {
    onChange(b);
    loadSlots();
  };

  const confirmBlock = async (note: string) => {
    if (!blocking) return;
    setBusy(true);
    setError("");
    try {
      await addException(blocking.start_at, blocking.end_at, note || undefined);
      setBlocking(null);
      loadSlots();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const confirmUnblock = async () => {
    if (!unblocking) return;
    setBusy(true);
    setError("");
    try {
      await deleteException(unblocking.id);
      setUnblocking(null);
      loadSlots();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const timed = bookings.filter((b) => b.scheduled_at);
  const untimed = bookings.filter((b) => !b.scheduled_at);
  const bookedStarts = new Set(timed.map((b) => b.scheduled_at as string));
  // Hide free slots that coincide with a booking.
  const free = openSlots.filter((s) => !bookedStarts.has(s.start_at));

  const weekStart = new Date(mondayOfUTC(new Date()).getTime() + weekOffset * 7 * DAY_MS);
  const weekEnd = new Date(weekStart.getTime() + 7 * DAY_MS);
  const days = Array.from({ length: 7 }, (_, i) => new Date(weekStart.getTime() + i * DAY_MS));

  const inWeek = (iso: string) => {
    const t = new Date(iso);
    return t >= weekStart && t < weekEnd;
  };

  type Item =
    | { kind: "booked"; start: string; booking: Booking }
    | { kind: "free"; start: string; slot: OpenSlot }
    | { kind: "unavailable"; start: string; exception: AvailabilityException };

  const byDay = new Map<string, Item[]>();
  for (const b of timed) {
    if (!inWeek(b.scheduled_at as string)) continue;
    const k = dateKey(b.scheduled_at as string);
    (byDay.get(k) ?? byDay.set(k, []).get(k)!).push({ kind: "booked", start: b.scheduled_at as string, booking: b });
  }
  for (const s of free) {
    if (!inWeek(s.start_at)) continue;
    const k = dateKey(s.start_at);
    (byDay.get(k) ?? byDay.set(k, []).get(k)!).push({ kind: "free", start: s.start_at, slot: s });
  }
  // Expand each exception into hourly blocks within the current week.
  for (const exc of exceptions) {
    let t = new Date(exc.start_at);
    const end = new Date(exc.end_at);
    while (t < end) {
      if (t >= weekStart && t < weekEnd) {
        const startIso = t.toISOString();
        const k = dateKey(startIso);
        (byDay.get(k) ?? byDay.set(k, []).get(k)!).push({ kind: "unavailable", start: startIso, exception: exc });
      }
      t = new Date(t.getTime() + HOUR_MS);
    }
  }
  for (const items of byDay.values()) items.sort((a, b) => a.start.localeCompare(b.start));

  const lastDay = days[6];
  const rangeLabel = `${fmtDayNum(weekStart)} – ${fmtDayNum(lastDay)} de ${lastDay.getUTCFullYear()}`;

  const selected = selectedId != null ? bookings.find((b) => b.id === selectedId) ?? null : null;

  return (
    <div className="section">
      <div className="cal-legend">
        <span><span className="dot" style={{ border: "1px dashed var(--border)" }} /> Livre</span>
        <span><span className="dot" style={{ background: "#fdecec", border: "1px solid #f5c2c0" }} /> Indisponível</span>
        <span><span className="dot" style={{ background: "#e7f7ee" }} /> Confirmado</span>
        <span><span className="dot" style={{ background: "#fdf3e7" }} /> Pendente</span>
        {isFirm && (
          <span>
            <span className="cal-avatar cal-avatar-none" style={{ width: 16, height: 16, fontSize: 9 }}>?</span>
            Sem advogado
          </span>
        )}
      </div>

      {bookings.length === 0 && (
        <p className="muted">Nenhuma solicitação recebida ainda. Seus horários livres aparecem abaixo.</p>
      )}

      <div className="cal-nav">
        <button className="btn btn-sm btn-ghost" onClick={() => setWeekOffset((w) => w - 1)}>
          ‹ Semana anterior
        </button>
        <span className="cal-range">{rangeLabel}</span>
        <button className="btn btn-sm btn-ghost" onClick={() => setWeekOffset((w) => w + 1)}>
          Próxima semana ›
        </button>
      </div>

      <div className="cal-week">
        {days.map((day, i) => {
          const key = day.toISOString().slice(0, 10);
          const items = byDay.get(key) ?? [];
          return (
            <div className="cal-day" key={key}>
              <div className="cal-day-head">
                {WEEKDAY_SHORT[i]}
                <span className="num">{fmtDayNum(day)}</span>
              </div>
              <div className="cal-slots">
                {items.length === 0 ? (
                  <span className="cal-empty">—</span>
                ) : (
                  items.map((it) =>
                    it.kind === "free" ? (
                      <button
                        className="cal-slot-free"
                        key={it.start}
                        title="Clique para bloquear este horário (indisponibilidade)"
                        onClick={() => setBlocking(it.slot)}
                      >
                        {hourLabel(it.start)}
                      </button>
                    ) : it.kind === "unavailable" ? (
                      <button
                        className="cal-slot-blocked"
                        key={it.exception.id + "-" + it.start}
                        title={
                          it.exception.note
                            ? `Bloqueado: ${it.exception.note} — clique para desbloquear`
                            : "Bloqueado — clique para desbloquear"
                        }
                        onClick={() => setUnblocking(it.exception)}
                      >
                        <span>{hourLabel(it.start)}</span>
                        {it.exception.note && (
                          <span className="cal-slot-blocked-note">{it.exception.note}</span>
                        )}
                      </button>
                    ) : (
                      <BookedSlot
                        key={it.start + "-" + it.booking.id}
                        booking={it.booking}
                        isFirm={isFirm}
                        firmLawyers={firmLawyers}
                        onClick={() => setSelectedId(it.booking.id)}
                      />
                    ),
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>

      {untimed.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h2>Solicitações sem horário definido</h2>
          {untimed.map((b) => (
            <BookingCard
              key={b.id}
              booking={b}
              isProvider
              firmLawyers={firmLawyers}
              onChange={handleChange}
              setError={setError}
            />
          ))}
        </div>
      )}

      {selected && (
        <div className="modal-overlay" onClick={() => setSelectedId(null)}>
          <div
            className="modal modal-wide modal-wide-wrap"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <button className="modal-close" onClick={() => setSelectedId(null)} title="Fechar">
              <CloseIcon />
            </button>
            <BookingCard
              booking={selected}
              isProvider
              firmLawyers={firmLawyers}
              onChange={handleChange}
              setError={setError}
              embedded
            />
          </div>
        </div>
      )}

      {blocking && (
        <BlockSlotModal
          slot={blocking}
          busy={busy}
          onConfirm={confirmBlock}
          onCancel={() => setBlocking(null)}
        />
      )}

      {unblocking && (
        <ConfirmDialog
          title="Desbloquear horário"
          message={
            <>
              Remover o bloqueio de <strong>{fmtDateTime(unblocking.start_at)}</strong>?
              {unblocking.note && (
                <>
                  {" "}Observação registrada: <em>{unblocking.note}</em>.
                </>
              )}
              {" "}O horário voltará a aparecer como disponível para os clientes.
            </>
          }
          confirmLabel="Desbloquear"
          busyLabel="Desbloqueando..."
          busy={busy}
          onConfirm={confirmUnblock}
          onCancel={() => setUnblocking(null)}
        />
      )}
    </div>
  );
}

// Custom block modal: lets the provider add an optional note alongside the block.
function BlockSlotModal({
  slot,
  busy,
  onConfirm,
  onCancel,
}: {
  slot: OpenSlot;
  busy: boolean;
  onConfirm: (note: string) => void;
  onCancel: () => void;
}) {
  const [note, setNote] = useState("");

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [busy, onCancel]);

  return (
    <div className="modal-overlay" onClick={() => !busy && onCancel()}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Bloquear horário"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="modal-title">Bloquear horário</h3>
        <div className="modal-body">
          Marcar <strong>{fmtDateTime(slot.start_at)}</strong> como indisponível? O horário
          deixará de ser oferecido aos clientes. Você pode desbloquear clicando nele na agenda
          ou acessar todos os bloqueios em{" "}
          <Link to="/painel/agendamento">Configuração de agendamento</Link>.
        </div>
        <div className="field">
          <label>Observação (opcional)</label>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Ex: reunião interna, feriado…"
            disabled={busy}
            autoFocus
          />
        </div>
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onCancel} disabled={busy}>
            Cancelar
          </button>
          <button
            className="btn btn-danger-solid"
            onClick={() => onConfirm(note)}
            disabled={busy}
          >
            {busy ? "Bloqueando..." : "Bloquear"}
          </button>
        </div>
      </div>
    </div>
  );
}

// A booked slot in the calendar: time + client name (truncated), and — for
// firms — a quick avatar of the responsible lawyer (or a "?" when none yet).
function BookedSlot({
  booking,
  isFirm,
  firmLawyers,
  onClick,
}: {
  booking: Booking;
  isFirm: boolean;
  firmLawyers: LawyerOption[];
  onClick: () => void;
}) {
  return (
    <button
      className={`cal-slot-booked cal-booked-${booking.status}`}
      onClick={onClick}
      title={`${booking.client.full_name} — ${STATUS_LABEL[booking.status]}`}
    >
      <span className="cal-slot-time">{hourLabel(booking.scheduled_at as string)}</span>
      <span className="cal-slot-name">{booking.client.full_name}</span>
      {isFirm && <LawyerBadge booking={booking} firmLawyers={firmLawyers} />}
    </button>
  );
}

function LawyerBadge({
  booking,
  firmLawyers,
}: {
  booking: Booking;
  firmLawyers: LawyerOption[];
}) {
  if (booking.lawyer_user_id == null) {
    return (
      <span className="cal-avatar cal-avatar-none" title="Sem advogado responsável">
        ?
      </span>
    );
  }
  const opt = firmLawyers.find((l) => l.user_id === booking.lawyer_user_id);
  const name = booking.lawyer?.full_name ?? opt?.full_name ?? "";
  return (
    <span className="cal-avatar" title={`Advogado: ${name}`}>
      {opt?.photo_url ? <img src={opt.photo_url} alt={name} /> : initials(name)}
    </span>
  );
}

function BookingCard({
  booking,
  isProvider,
  firmLawyers,
  onChange,
  setError,
  embedded = false,
}: {
  booking: Booking;
  isProvider: boolean;
  firmLawyers: LawyerOption[];
  onChange: (b: Booking) => void;
  setError: (s: string) => void;
  // When shown inside the detail modal, drop the standalone card chrome.
  embedded?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  // Inline confirm panel for destructive actions (captures an optional reason).
  const [confirming, setConfirming] = useState<null | "cancel" | "reject">(null);
  const [reason, setReason] = useState("");

  const counterpart = isProvider ? booking.client : booking.provider;
  const pendingClientTurn = booking.pending_action?.actor === "client";

  // When the firm is responsible for choosing the lawyer, it must assign one
  // (and can only do so while the booking is still active).
  const mode = booking.config.lawyer_selection_mode;
  const firmAssigns = mode === "firm_chooses" || mode === "hybrid";
  const isActive = CANCELLABLE.includes(booking.status);
  const showResponsible = booking.lawyer != null || (isProvider && firmAssigns);
  const canAssign = isProvider && firmAssigns && isActive;

  const canCancel = CANCELLABLE.includes(booking.status);
  const canApprove =
    isProvider &&
    booking.status === "awaiting_approval" &&
    booking.pending_action?.action === "approve";
  const canReject = isProvider && REJECTABLE.includes(booking.status);
  const canComplete = isProvider && booking.status === "confirmed";

  const run = async (fn: () => Promise<Booking>) => {
    setBusy(true);
    setError("");
    try {
      onChange(await fn());
      setConfirming(null);
      setReason("");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={embedded ? "" : "section"}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div>
          <div style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5 }}>
            {isProvider ? "Cliente" : "Profissional"}
          </div>
          <h2 style={{ margin: "2px 0 0", textTransform: "none", letterSpacing: 0, fontSize: 18, color: "inherit" }}>
            {counterpart.full_name}
          </h2>
        </div>
        <span className={`status-badge status-${booking.status}`}>
          {STATUS_LABEL[booking.status] ?? booking.status}
        </span>
      </div>

      <div className="list-row" style={{ marginTop: 12 }}>
        <span className="muted">Horário: </span>
        {booking.scheduled_at ? fmtDateTime(booking.scheduled_at) : <span className="muted">a definir</span>}
      </div>
      <div className="list-row">
        <span className="muted">Solicitado em: </span>
        {fmtDateTime(booking.created_at)}
      </div>

      {showResponsible && (
        <div className="list-row">
          <span className="muted">Advogado responsável: </span>
          {booking.lawyer ? booking.lawyer.full_name : <span className="muted">a definir</span>}
        </div>
      )}

      {canAssign && (
        <AssignLawyer
          booking={booking}
          firmLawyers={firmLawyers}
          onChange={onChange}
          setError={setError}
        />
      )}

      {/* Provider-only: contact details of who booked + what they submitted. */}
      {isProvider && (
        <ClientDetails
          email={counterpart.email}
          phone={counterpart.phone}
          city={counterpart.city}
          state={counterpart.state}
          notes={booking.notes}
          answers={booking.triage_response?.answers ?? []}
        />
      )}

      {!isProvider && pendingClientTurn && booking.pending_action && (
        <div className="alert alert-info" style={{ marginTop: 12 }}>
          Ação pendente: {booking.pending_action.label}. Continue pelo perfil do profissional.
        </div>
      )}

      {booking.resolution_reason && (
        <div className="list-row">
          <span className="muted">Motivo: </span>
          {booking.resolution_reason}
        </div>
      )}

      {/* Actions */}
      {confirming ? (
        <div style={{ marginTop: 12 }}>
          <div className="field">
            <label>{confirming === "reject" ? "Motivo da recusa (opcional)" : "Motivo do cancelamento (opcional)"}</label>
            <input value={reason} onChange={(e) => setReason(e.target.value)} autoFocus />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn btn-sm btn-danger-solid"
              disabled={busy}
              onClick={() =>
                run(() =>
                  confirming === "reject"
                    ? rejectBooking(booking.id, reason || undefined)
                    : cancelBooking(booking.id, reason || undefined),
                )
              }
            >
              {busy ? "Processando..." : confirming === "reject" ? "Confirmar recusa" : "Confirmar cancelamento"}
            </button>
            <button
              className="btn btn-sm btn-ghost"
              disabled={busy}
              onClick={() => {
                setConfirming(null);
                setReason("");
              }}
            >
              Voltar
            </button>
          </div>
        </div>
      ) : (
        (canApprove || canComplete || canReject || canCancel) && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            {canApprove && (
              <button className="btn btn-sm" disabled={busy} onClick={() => run(() => approveBooking(booking.id))}>
                Aprovar
              </button>
            )}
            {canComplete && (
              <button className="btn btn-sm" disabled={busy} onClick={() => run(() => completeBooking(booking.id))}>
                Marcar como concluído
              </button>
            )}
            {canReject && (
              <button className="btn btn-sm btn-ghost btn-danger" disabled={busy} onClick={() => setConfirming("reject")}>
                Recusar
              </button>
            )}
            {canCancel && (
              <button className="btn btn-sm btn-ghost btn-danger" disabled={busy} onClick={() => setConfirming("cancel")}>
                Cancelar
              </button>
            )}
          </div>
        )
      )}
    </div>
  );
}

function AssignLawyer({
  booking,
  firmLawyers,
  onChange,
  setError,
}: {
  booking: Booking;
  firmLawyers: LawyerOption[];
  onChange: (b: Booking) => void;
  setError: (s: string) => void;
}) {
  const [selected, setSelected] = useState<string>(
    booking.lawyer_user_id ? String(booking.lawyer_user_id) : "",
  );
  const [busy, setBusy] = useState(false);

  const assign = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      onChange(await assignLawyer(booking.id, Number(selected)));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="field" style={{ marginTop: 10 }}>
      <label>{booking.lawyer ? "Trocar advogado responsável" : "Atribuir advogado responsável"}</label>
      <p className="muted" style={{ margin: "0 0 6px", fontSize: 13 }}>
        Obrigatório para concluir. O advogado precisa estar livre no horário do atendimento.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <select value={selected} onChange={(e) => setSelected(e.target.value)} disabled={busy}>
          <option value="">Selecione…</option>
          {firmLawyers.map((l) => (
            <option key={l.user_id} value={l.user_id}>
              {l.full_name}
            </option>
          ))}
        </select>
        <button className="btn btn-sm" onClick={assign} disabled={busy || !selected}>
          {busy ? "Atribuindo..." : "Atribuir"}
        </button>
      </div>
    </div>
  );
}

function ClientDetails({
  email,
  phone,
  city,
  state,
  notes,
  answers,
}: {
  email: string | null;
  phone: string | null;
  city: string | null;
  state: string | null;
  notes: string | null;
  answers: TriageAnswerRead[];
}) {
  const location = [city, state].filter(Boolean).join("/");
  return (
    <div style={{ marginTop: 8 }}>
      {email && (
        <div className="list-row">
          <span className="muted">E-mail: </span>
          <a href={`mailto:${email}`}>{email}</a>
        </div>
      )}
      {phone && (
        <div className="list-row">
          <span className="muted">Telefone: </span>
          {phone}
        </div>
      )}
      {location && (
        <div className="list-row">
          <span className="muted">Localização: </span>
          {location}
        </div>
      )}
      {notes && (
        <div className="list-row">
          <span className="muted">Observações do cliente: </span>
          {notes}
        </div>
      )}
      {answers.length > 0 && (
        <div className="list-row">
          <div className="muted" style={{ marginBottom: 6 }}>Respostas da triagem:</div>
          {answers.map((a) => (
            <div key={a.question_id} style={{ marginBottom: 4 }}>
              <strong>{a.question_text}</strong>
              <div className="muted" style={{ fontSize: 13 }}>{fmtAnswer(a.value)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
