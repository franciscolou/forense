import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getOpenSlots,
  getPublicFlow,
  initiateBooking,
  selectSlot,
  submitPayment,
  submitTriage,
  type TriageAnswerInput,
} from "../api/bookings";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Booking, OpenSlot, PublicFlow, TriageQuestion } from "../types";

// Slot wall-times are platform-UTC by convention; format in UTC so what the
// provider painted on their grid is exactly what the client sees.
const dayLabel = (iso: string) =>
  new Date(iso).toLocaleDateString("pt-BR", {
    timeZone: "UTC",
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
  });

const hourLabel = (iso: string) =>
  new Date(iso).toLocaleTimeString("pt-BR", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
  });

const STATUS_LABEL: Record<string, string> = {
  pending: "Em andamento",
  awaiting_approval: "Aguardando aprovação",
  confirmed: "Confirmado",
  rejected: "Recusado",
  cancelled: "Cancelado",
  completed: "Concluído",
};

// Fully data-driven: the component renders whichever step the backend reports as
// pending (`booking.pending_action`). It contains no per-flow ("mode") logic —
// the same code drives every configuration.
export default function BookingFlow({ providerUserId }: { providerUserId: number }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [flow, setFlow] = useState<PublicFlow | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getPublicFlow(providerUserId)
      .then(setFlow)
      .catch((e) => setError(errorMessage(e)));
  }, [providerUserId]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!flow) return <p className="muted">Carregando opções de agendamento...</p>;

  const start = async () => {
    if (!user) return navigate("/entrar");
    if (user.role !== "client") {
      setError("Apenas clientes podem solicitar atendimento.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setBooking(await initiateBooking(providerUserId));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  // Before starting: show the flow preview so the client knows what to expect.
  if (!booking) {
    return (
      <div className="section">
        <h2>Agendamento</h2>
        <FlowPreview flow={flow} />
        <button className="btn" onClick={start} disabled={busy}>
          {flow.config.agenda_visibility === "hidden"
            ? "Solicitar atendimento"
            : "Agendar atendimento"}
        </button>
      </div>
    );
  }

  const pending = booking.pending_action;
  const isClientTurn = pending?.actor === "client";

  return (
    <div className="section">
      <h2>Agendamento</h2>
      <p>
        Status: <strong>{STATUS_LABEL[booking.status] ?? booking.status}</strong>
      </p>
      {error && <div className="alert alert-error">{error}</div>}

      {isClientTurn && pending ? (
        <StepInput
          stepKey={pending.key}
          flow={flow}
          booking={booking}
          onUpdated={setBooking}
          setError={setError}
        />
      ) : (
        <TerminalPanel booking={booking} />
      )}
    </div>
  );
}

function FlowPreview({ flow }: { flow: PublicFlow }) {
  if (flow.steps.length === 0) {
    return <p className="muted">Confirmação imediata — sem etapas adicionais.</p>;
  }
  return (
    <ol className="muted" style={{ paddingLeft: 18 }}>
      {flow.steps.map((s) => (
        <li key={s.key}>
          {s.label}
          {s.actor === "provider" ? " (analisado pelo profissional)" : ""}
          {s.key === "triage" && s.required === false ? " (opcional)" : ""}
        </li>
      ))}
    </ol>
  );
}

function TerminalPanel({ booking }: { booking: Booking }) {
  if (booking.status === "awaiting_approval")
    return (
      <div className="alert alert-info">
        Sua solicitação foi enviada e está aguardando a aprovação do profissional.
      </div>
    );
  if (booking.status === "confirmed")
    return (
      <div className="alert alert-info">
        Atendimento confirmado!
        {booking.scheduled_at && (
          <> Horário: {dayLabel(booking.scheduled_at)} às {hourLabel(booking.scheduled_at)}.</>
        )}
        {booking.payment_state === "pending" && " Pagamento pendente."}
      </div>
    );
  if (booking.status === "rejected")
    return (
      <div className="alert alert-error">
        Solicitação recusada.{booking.resolution_reason ? ` Motivo: ${booking.resolution_reason}` : ""}
      </div>
    );
  if (booking.status === "cancelled")
    return <div className="alert alert-error">Agendamento cancelado.</div>;
  return <p className="muted">Acompanhe pelo seu painel de solicitações.</p>;
}

// Dispatches to the right input for the pending step. Adding a new step type =
// add a branch here + the backend step; existing flows are untouched.
function StepInput({
  stepKey,
  flow,
  booking,
  onUpdated,
  setError,
}: {
  stepKey: string;
  flow: PublicFlow;
  booking: Booking;
  onUpdated: (b: Booking) => void;
  setError: (s: string) => void;
}) {
  if (stepKey === "triage")
    return <TriageStep flow={flow} booking={booking} onUpdated={onUpdated} setError={setError} />;
  if (stepKey === "agenda")
    return <AgendaStep booking={booking} onUpdated={onUpdated} setError={setError} />;
  if (stepKey === "payment")
    return <PaymentStep booking={booking} onUpdated={onUpdated} setError={setError} />;
  return <p className="muted">Etapa não reconhecida: {stepKey}</p>;
}

function TriageStep({
  flow,
  booking,
  onUpdated,
  setError,
}: {
  flow: PublicFlow;
  booking: Booking;
  onUpdated: (b: Booking) => void;
  setError: (s: string) => void;
}) {
  const [answers, setAnswers] = useState<Record<number, unknown>>({});
  const [busy, setBusy] = useState(false);
  const optional = flow.config.triage_mode === "optional";

  const setAnswer = (q: TriageQuestion, value: unknown) =>
    setAnswers((a) => ({ ...a, [q.id]: value }));

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const payload: TriageAnswerInput[] = Object.entries(answers)
        .filter(([, v]) => v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0))
        .map(([qid, value]) => ({ question_id: Number(qid), value }));
      onUpdated(await submitTriage(booking.id, payload));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <p className="muted">Triagem{optional ? " (opcional)" : ""}</p>
      {flow.questions.map((q) => (
        <div className="field" key={q.id}>
          <label>
            {q.text}
            {q.required && !optional ? " *" : ""}
          </label>
          {q.qtype === "boolean" ? (
            <select
              defaultValue=""
              onChange={(e) => setAnswer(q, e.target.value === "" ? undefined : e.target.value === "sim")}
            >
              <option value="">—</option>
              <option value="sim">Sim</option>
              <option value="nao">Não</option>
            </select>
          ) : q.qtype === "single_choice" ? (
            <select defaultValue="" onChange={(e) => setAnswer(q, e.target.value || undefined)}>
              <option value="">—</option>
              {q.options.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          ) : (
            <input onChange={(e) => setAnswer(q, e.target.value)} />
          )}
        </div>
      ))}
      <button className="btn" onClick={submit} disabled={busy}>
        {optional ? "Enviar / Pular triagem" : "Enviar triagem"}
      </button>
    </div>
  );
}

const DAY_MS = 24 * 60 * 60 * 1000;
const WEEKDAY_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const MONTH_SHORT = [
  "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez",
];

// Monday 00:00 UTC of the week containing `iso`.
function mondayOf(iso: string): Date {
  const d = new Date(iso);
  const mondayOffset = (d.getUTCDay() + 6) % 7; // Sun=0 → 6, Mon=1 → 0, …
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - mondayOffset));
}

const fmtDayNum = (d: Date) => `${String(d.getUTCDate()).padStart(2, "0")}/${MONTH_SHORT[d.getUTCMonth()]}`;

function AgendaStep({
  booking,
  onUpdated,
  setError,
}: {
  booking: Booking;
  onUpdated: (b: Booking) => void;
  setError: (s: string) => void;
}) {
  const [slots, setSlots] = useState<OpenSlot[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [weekIndex, setWeekIndex] = useState(0);

  useEffect(() => {
    getOpenSlots(booking.provider.id)
      .then(setSlots)
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoaded(true));
  }, [booking.provider.id, setError]);

  const pick = async (startAt: string) => {
    setBusy(true);
    setError("");
    try {
      onUpdated(await selectSlot(booking.id, startAt));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) return <p className="muted">Carregando horários...</p>;
  if (slots.length === 0) return <p className="muted">Nenhum horário disponível no momento.</p>;

  // Slots arrive sorted ascending. Build the navigable range of weeks spanning
  // the first and last available day.
  const firstMonday = mondayOf(slots[0].start_at);
  const lastMonday = mondayOf(slots[slots.length - 1].start_at);
  const weekCount = Math.round((lastMonday.getTime() - firstMonday.getTime()) / (7 * DAY_MS)) + 1;
  const index = Math.min(Math.max(weekIndex, 0), weekCount - 1);

  const weekStart = new Date(firstMonday.getTime() + index * 7 * DAY_MS);
  const weekEnd = new Date(weekStart.getTime() + 7 * DAY_MS);
  const days = Array.from({ length: 7 }, (_, i) => new Date(weekStart.getTime() + i * DAY_MS));

  // Bucket this week's slots by calendar day (UTC).
  const byDate = new Map<string, OpenSlot[]>();
  for (const s of slots) {
    const t = new Date(s.start_at);
    if (t >= weekStart && t < weekEnd) {
      const key = s.start_at.slice(0, 10);
      (byDate.get(key) ?? byDate.set(key, []).get(key)!).push(s);
    }
  }

  const lastDay = days[6];
  const rangeLabel =
    `${fmtDayNum(weekStart)} – ${fmtDayNum(lastDay)} de ${lastDay.getUTCFullYear()}`;

  return (
    <div>
      <p className="muted">Escolha um horário (UTC):</p>

      <div className="cal-nav">
        <button
          className="btn btn-sm btn-ghost"
          onClick={() => setWeekIndex(index - 1)}
          disabled={index <= 0}
        >
          ‹ Semana anterior
        </button>
        <span className="cal-range">{rangeLabel}</span>
        <button
          className="btn btn-sm btn-ghost"
          onClick={() => setWeekIndex(index + 1)}
          disabled={index >= weekCount - 1}
        >
          Próxima semana ›
        </button>
      </div>

      <div className="cal-week">
        {days.map((day, i) => {
          const key = day.toISOString().slice(0, 10);
          const daySlots = byDate.get(key) ?? [];
          return (
            <div className="cal-day" key={key}>
              <div className="cal-day-head">
                {WEEKDAY_SHORT[i]}
                <span className="num">{fmtDayNum(day)}</span>
              </div>
              <div className="cal-slots">
                {daySlots.length === 0 ? (
                  <span className="cal-empty">—</span>
                ) : (
                  daySlots.map((s) => (
                    <button
                      key={s.start_at}
                      className="cal-slot"
                      disabled={busy}
                      onClick={() => pick(s.start_at)}
                    >
                      {hourLabel(s.start_at)}
                    </button>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PaymentStep({
  booking,
  onUpdated,
  setError,
}: {
  booking: Booking;
  onUpdated: (b: Booking) => void;
  setError: (s: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const pay = async () => {
    setBusy(true);
    setError("");
    try {
      onUpdated(await submitPayment(booking.id));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <div className="alert alert-info">
        Pagamento (simulado — integração de meios de pagamento não faz parte desta etapa).
      </div>
      <button className="btn" onClick={pay} disabled={busy}>
        Confirmar pagamento
      </button>
    </div>
  );
}
