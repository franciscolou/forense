import { Fragment, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  addException,
  addQuestion,
  deleteException,
  deleteQuestion,
  getMyAvailability,
  getMyConfig,
  saveRules,
  updateMyConfig,
  updateQuestion,
  type ConfigUpdate,
  type QuestionInput,
} from "../api/bookingConfig";
import { errorMessage } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import { CheckIcon, CloseIcon, EditIcon, PlusIcon, TrashIcon } from "../components/icons";
import { useAuth } from "../context/AuthContext";
import type {
  AvailabilityException,
  AvailabilityRule,
  BookingConfiguration,
  QuestionType,
  Schedule,
  TriageQuestion,
} from "../types";

const QTYPE_LABEL: Record<QuestionType, string> = {
  text: "Texto",
  boolean: "Sim/Não",
  single_choice: "Escolha única",
  multi_choice: "Múltipla escolha",
};

const QTYPE_OPTIONS: [QuestionType, string][] = [
  ["text", "Texto"],
  ["boolean", "Sim/Não"],
  ["single_choice", "Escolha única"],
  ["multi_choice", "Múltipla escolha"],
];

const needsOptions = (t: QuestionType) => t === "single_choice" || t === "multi_choice";

function toDraft(c: BookingConfiguration): ConfigUpdate {
  return {
    triage_mode: c.triage_mode,
    agenda_visibility: c.agenda_visibility,
    approval_mode: c.approval_mode,
    payment_mode: c.payment_mode,
    min_advance_days: c.min_advance_days,
    max_advance_days: c.max_advance_days,
  };
}

// Provider-only screen. The rest of the painel remains "to be implemented";
// this is the slice that lets a provider compose their own booking flow.
export default function BookingConfigPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [config, setConfig] = useState<BookingConfiguration | null>(null);
  // Draft of the four settings; only persisted when the user clicks "Salvar".
  const [draft, setDraft] = useState<ConfigUpdate | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) return navigate("/entrar");
    if (user.role === "client") return navigate("/");
    getMyConfig()
      .then((c) => {
        setConfig(c);
        setDraft(toDraft(c));
      })
      .catch((e) => setError(errorMessage(e)));
  }, [user, loading, navigate]);

  if (!config || !draft) {
    return (
      <div className="container">
        {error ? <div className="alert alert-error" style={{ marginTop: 24 }}>{error}</div> : <p>Carregando...</p>}
      </div>
    );
  }

  const dirty =
    draft.triage_mode !== config.triage_mode ||
    draft.agenda_visibility !== config.agenda_visibility ||
    draft.approval_mode !== config.approval_mode ||
    draft.payment_mode !== config.payment_mode ||
    draft.min_advance_days !== config.min_advance_days ||
    draft.max_advance_days !== config.max_advance_days;

  const editDraft = (patch: Partial<ConfigUpdate>) => {
    setSaved("");
    setDraft({ ...draft, ...patch });
  };

  const saveConfig = async () => {
    setError("");
    setSaved("");
    setSaving(true);
    try {
      const updated = await updateMyConfig(draft);
      setConfig(updated);
      setDraft(toDraft(updated));
      setSaved("Configuração salva.");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const resetDraft = () => {
    setSaved("");
    setError("");
    setDraft(toDraft(config));
  };

  return (
    <div className="container" style={{ maxWidth: 760 }}>
      <p style={{ marginTop: 16 }}>
        <Link to="/painel">← Painel</Link>
      </p>
      <h1>Configuração de agendamento</h1>
      <p className="muted">
        Combine as opções abaixo para montar seu fluxo. Não há "modos" fixos — o fluxo do cliente é
        derivado destas configurações.
      </p>
      {error && <div className="alert alert-error">{error}</div>}
      {saved && <div className="alert alert-info">{saved}</div>}

      <div className="section">
        <h2>Etapas do fluxo</h2>
        <Selector
          label="Triagem"
          value={draft.triage_mode}
          options={[
            ["disabled", "Desabilitada"],
            ["optional", "Opcional"],
            ["required", "Obrigatória"],
          ]}
          onChange={(v) => editDraft({ triage_mode: v as ConfigUpdate["triage_mode"] })}
        />
        <Selector
          label="Exibição da agenda"
          value={draft.agenda_visibility}
          options={[
            ["immediate", "Mostrar imediatamente"],
            ["after_triage", "Mostrar após a triagem"],
            ["hidden", "Não mostrar (apenas solicitação)"],
          ]}
          onChange={(v) => editDraft({ agenda_visibility: v as ConfigUpdate["agenda_visibility"] })}
        />
        <Selector
          label="Aprovação"
          value={draft.approval_mode}
          options={[
            ["automatic", "Automática"],
            ["manual", "Manual"],
          ]}
          onChange={(v) => editDraft({ approval_mode: v as ConfigUpdate["approval_mode"] })}
        />
        <Selector
          label="Pagamento"
          value={draft.payment_mode}
          options={[
            ["none", "Não cobrar"],
            ["before_confirmation", "Cobrar antes da confirmação"],
            ["after_confirmation", "Cobrar após a confirmação"],
          ]}
          onChange={(v) => editDraft({ payment_mode: v as ConfigUpdate["payment_mode"] })}
        />
        <div className="field">
          <label>Antecedência mínima para agendamento</label>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="number"
              min={0}
              max={365}
              value={draft.min_advance_days}
              onChange={(e) =>
                editDraft({
                  min_advance_days: Math.min(365, Math.max(0, Number(e.target.value) || 0)),
                })
              }
              style={{ width: 110 }}
            />
            <span className="muted">dias a partir de hoje</span>
          </div>
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 13 }}>
            Exige uma antecedência mínima para marcar (0 = permite marcar para hoje). Não pode ser
            maior que a antecedência máxima.
          </p>
        </div>
        <div className="field">
          <label>Antecedência máxima para agendamento</label>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="number"
              min={1}
              max={365}
              value={draft.max_advance_days}
              onChange={(e) =>
                editDraft({
                  max_advance_days: Math.min(365, Math.max(1, Number(e.target.value) || 1)),
                })
              }
              style={{ width: 110 }}
            />
            <span className="muted">dias a partir de hoje</span>
          </div>
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 13 }}>
            Limita quão longe no futuro um cliente pode marcar um atendimento (1–365 dias).
          </p>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 8 }}>
          <button className="btn" onClick={saveConfig} disabled={!dirty || saving}>
            {saving ? "Salvando..." : "Salvar mudanças"}
          </button>
          {dirty && (
            <button className="btn btn-ghost" onClick={resetDraft} disabled={saving}>
              Descartar
            </button>
          )}
          {dirty && <span className="muted">Alterações não salvas</span>}
        </div>
      </div>

      <QuestionsEditor config={config} onChange={setConfig} setError={setError} />
      <ScheduleEditor setError={setError} />
    </div>
  );
}

function Selector({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (v: string) => void;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}

function QuestionsEditor({
  config,
  onChange,
  setError,
}: {
  config: BookingConfiguration;
  onChange: (c: BookingConfiguration) => void;
  setError: (s: string) => void;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  // Question pending deletion confirmation (null = no dialog open).
  const [pendingDelete, setPendingDelete] = useState<TriageQuestion | null>(null);

  const create = async (input: QuestionInput) => {
    setError("");
    setBusy(true);
    try {
      onChange(await addQuestion({ ...input, order: config.questions.length + 1 }));
      setCreating(false);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = async (id: number, input: QuestionInput) => {
    setError("");
    setBusy(true);
    try {
      onChange(await updateQuestion(id, input));
      setEditingId(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setError("");
    setBusy(true);
    try {
      onChange(await deleteQuestion(pendingDelete.id));
      setPendingDelete(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="section">
      <h2>Perguntas de triagem</h2>
      {config.questions.length === 0 && !creating && (
        <p className="muted">Nenhuma pergunta cadastrada.</p>
      )}

      {config.questions.map((q) =>
        editingId === q.id ? (
          <div className="question-edit" key={q.id}>
            <QuestionForm
              initial={q}
              submitLabel="Salvar pergunta"
              busy={busy}
              onSubmit={(input) => saveEdit(q.id, input)}
              onCancel={() => setEditingId(null)}
            />
          </div>
        ) : (
          <QuestionRow
            key={q.id}
            question={q}
            disabled={busy || editingId !== null || creating}
            onEdit={() => setEditingId(q.id)}
            onRemove={() => setPendingDelete(q)}
          />
        ),
      )}

      {creating ? (
        <div className="question-edit">
          <QuestionForm
            submitLabel="Adicionar pergunta"
            busy={busy}
            onSubmit={create}
            onCancel={() => setCreating(false)}
          />
        </div>
      ) : (
        <div style={{ marginTop: 12 }}>
          <button
            className="btn btn-sm btn-icon"
            onClick={() => setCreating(true)}
            disabled={editingId !== null}
          >
            <PlusIcon /> Adicionar pergunta
          </button>
        </div>
      )}

      {pendingDelete && (
        <ConfirmDialog
          title="Excluir pergunta"
          message={
            <>
              Tem certeza que deseja excluir a pergunta{" "}
              <strong>"{pendingDelete.text}"</strong>? Esta ação não pode ser desfeita.
            </>
          }
          confirmLabel="Excluir"
          danger
          busy={busy}
          onConfirm={confirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
}

function QuestionRow({
  question,
  disabled,
  onEdit,
  onRemove,
}: {
  question: TriageQuestion;
  disabled: boolean;
  onEdit: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="list-row" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
      <div style={{ flex: 1 }}>
        <div>
          {question.text}
          {question.required && <span title="Obrigatória"> *</span>}
        </div>
        <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>
          {QTYPE_LABEL[question.qtype]}
        </div>
        {needsOptions(question.qtype) && question.options.length > 0 && (
          <div className="tags" style={{ marginTop: 6 }}>
            {question.options.map((o, i) => (
              <span className="tag" key={i}>
                {o}
              </span>
            ))}
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <button
          className="btn btn-sm btn-ghost btn-icon"
          onClick={onEdit}
          disabled={disabled}
          title="Editar"
        >
          <EditIcon />
        </button>
        <button
          className="btn btn-sm btn-ghost btn-icon btn-danger"
          onClick={onRemove}
          disabled={disabled}
          title="Excluir"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  );
}

function QuestionForm({
  initial,
  submitLabel,
  busy,
  onSubmit,
  onCancel,
}: {
  initial?: TriageQuestion;
  submitLabel: string;
  busy: boolean;
  onSubmit: (input: QuestionInput) => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState(initial?.text ?? "");
  const [qtype, setQtype] = useState<QuestionType>(initial?.qtype ?? "text");
  const [options, setOptions] = useState<string[]>(initial?.options ?? []);
  const [required, setRequired] = useState(initial?.required ?? true);
  const [localError, setLocalError] = useState("");

  const submit = () => {
    if (!text.trim()) {
      setLocalError("Informe o texto da pergunta.");
      return;
    }
    if (needsOptions(qtype) && options.length < 2) {
      setLocalError("Perguntas de escolha precisam de ao menos duas opções.");
      return;
    }
    setLocalError("");
    onSubmit({
      text: text.trim(),
      qtype,
      options: needsOptions(qtype) ? options : [],
      order: initial?.order ?? 0,
      required,
      is_active: initial?.is_active ?? true,
    });
  };

  return (
    <div>
      <div className="field">
        <label>Texto da pergunta</label>
        <input
          placeholder="ex: Qual é a área do seu problema?"
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus
        />
      </div>
      <div className="row field">
        <div>
          <label>Tipo de resposta</label>
          <select value={qtype} onChange={(e) => setQtype(e.target.value as QuestionType)}>
            {QTYPE_OPTIONS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <label className="checkbox-pill" style={{ width: "fit-content" }}>
            <input
              type="checkbox"
              checked={required}
              onChange={(e) => setRequired(e.target.checked)}
            />
            Obrigatória
          </label>
        </div>
      </div>

      {needsOptions(qtype) && <OptionsEditor options={options} onChange={setOptions} />}

      {localError && <div className="alert alert-error">{localError}</div>}

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button className="btn btn-sm btn-icon" onClick={submit} disabled={busy}>
          <CheckIcon /> {busy ? "Salvando..." : submitLabel}
        </button>
        <button className="btn btn-sm btn-ghost btn-icon" onClick={onCancel} disabled={busy}>
          <CloseIcon /> Cancelar
        </button>
      </div>
    </div>
  );
}

// Structured option management: add via an inline input, then edit or remove
// each option individually.
function OptionsEditor({
  options,
  onChange,
}: {
  options: string[];
  onChange: (opts: string[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");

  const confirmAdd = () => {
    const v = draft.trim();
    if (!v) return;
    onChange([...options, v]);
    setDraft("");
    setAdding(false);
  };

  const confirmEdit = (i: number) => {
    const v = editDraft.trim();
    if (!v) return;
    onChange(options.map((o, idx) => (idx === i ? v : o)));
    setEditingIndex(null);
    setEditDraft("");
  };

  const remove = (i: number) => onChange(options.filter((_, idx) => idx !== i));

  return (
    <div className="field">
      <label>Opções de resposta</label>
      {options.length === 0 && !adding && (
        <p className="muted" style={{ margin: "0 0 8px" }}>
          Nenhuma opção adicionada.
        </p>
      )}

      {options.map((o, i) => (
        <div className="list-row" key={i} style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {editingIndex === i ? (
            <>
              <input
                value={editDraft}
                onChange={(e) => setEditDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && confirmEdit(i)}
                autoFocus
                style={{ flex: 1 }}
              />
              <button className="btn btn-sm btn-icon-only" onClick={() => confirmEdit(i)} title="OK">
                <CheckIcon />
              </button>
              <button
                className="btn btn-sm btn-ghost btn-icon-only"
                onClick={() => setEditingIndex(null)}
                title="Cancelar"
              >
                <CloseIcon />
              </button>
            </>
          ) : (
            <>
              <span style={{ flex: 1 }}>{o}</span>
              <button
                className="btn btn-sm btn-ghost btn-icon-only"
                onClick={() => {
                  setEditingIndex(i);
                  setEditDraft(o);
                }}
                title="Editar"
              >
                <EditIcon />
              </button>
              <button
                className="btn btn-sm btn-ghost btn-icon-only btn-danger"
                onClick={() => remove(i)}
                title="Excluir"
              >
                <TrashIcon />
              </button>
            </>
          )}
        </div>
      ))}

      {adding ? (
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
          <input
            placeholder="Texto da opção"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") confirmAdd();
              if (e.key === "Escape") setAdding(false);
            }}
            autoFocus
            style={{ flex: 1 }}
          />
          <button className="btn btn-sm btn-icon-only" onClick={confirmAdd} title="OK">
            <CheckIcon />
          </button>
          <button
            className="btn btn-sm btn-ghost btn-icon-only"
            onClick={() => {
              setAdding(false);
              setDraft("");
            }}
            title="Cancelar"
          >
            <CloseIcon />
          </button>
        </div>
      ) : (
        <button
          className="btn btn-sm btn-ghost btn-icon"
          style={{ marginTop: 8 }}
          onClick={() => setAdding(true)}
        >
          <PlusIcon /> Adicionar opção
        </button>
      )}
    </div>
  );
}

// --- Availability schedule ---------------------------------------------
// Mon=0 … Sun=6 (matches the backend's datetime.weekday()).
const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
// Hours shown on the grid; each cell is a one-hour block starting at that hour.
const GRID_HOURS = Array.from({ length: 15 }, (_, i) => i + 7); // 07:00 … 21:00

const cellKey = (weekday: number, hour: number) => `${weekday}-${hour}`;
const serializeSet = (s: Set<string>) => [...s].sort().join(",");

function rulesToSet(rules: AvailabilityRule[]): Set<string> {
  const set = new Set<string>();
  for (const r of rules) {
    for (let h = r.start_hour; h < r.end_hour; h++) set.add(cellKey(r.weekday, h));
  }
  return set;
}

// Compress the painted cells back into contiguous per-weekday windows.
function setToRules(selected: Set<string>): AvailabilityRule[] {
  const rules: AvailabilityRule[] = [];
  for (let wd = 0; wd < 7; wd++) {
    const hours = GRID_HOURS.filter((h) => selected.has(cellKey(wd, h))).sort((a, b) => a - b);
    let runStart: number | null = null;
    let prev: number | null = null;
    const flush = () => {
      if (runStart !== null && prev !== null)
        rules.push({ weekday: wd, start_hour: runStart, end_hour: prev + 1 });
    };
    for (const h of hours) {
      if (runStart === null) runStart = h;
      else if (prev !== null && h !== prev + 1) {
        flush();
        runStart = h;
      }
      prev = h;
    }
    flush();
  }
  return rules;
}

function ScheduleEditor({ setError }: { setError: (s: string) => void }) {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [savedKey, setSavedKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");

  useEffect(() => {
    getMyAvailability()
      .then((s) => {
        setSchedule(s);
        const set = rulesToSet(s.rules);
        setSelected(set);
        setSavedKey(serializeSet(set));
      })
      .catch((e) => setError(errorMessage(e)));
  }, [setError]);

  if (!schedule) {
    return (
      <div className="section">
        <h2>Disponibilidade</h2>
        <p className="muted">Carregando...</p>
      </div>
    );
  }

  const dirty = serializeSet(selected) !== savedKey;

  const paint = (next: Set<string>) => {
    setSavedMsg("");
    setSelected(next);
  };

  const applyPreset = () => {
    const next = new Set<string>();
    for (let wd = 0; wd <= 4; wd++) for (let h = 9; h < 18; h++) next.add(cellKey(wd, h));
    paint(next);
  };

  const save = async () => {
    setSaving(true);
    setSavedMsg("");
    setError("");
    try {
      const updated = await saveRules(setToRules(selected));
      setSchedule({ ...schedule, rules: updated.rules });
      const set = rulesToSet(updated.rules);
      setSelected(set);
      setSavedKey(serializeSet(set));
      setSavedMsg("Grade de disponibilidade salva.");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="section">
      <h2>Disponibilidade</h2>
      <p className="muted">
        Pinte os horários em que você atende: clique numa célula ou arraste para marcar vários de
        uma vez. Clique no dia da semana para marcar/desmarcar a coluna inteira, ou na hora para a
        linha toda. Horários em UTC.
      </p>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <button className="btn btn-sm btn-ghost" onClick={applyPreset}>
          Dias úteis 09–18
        </button>
        <button className="btn btn-sm btn-ghost" onClick={() => paint(new Set())}>
          Limpar tudo
        </button>
      </div>

      <WeeklyGrid selected={selected} onChange={paint} />

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12 }}>
        <button className="btn btn-icon" onClick={save} disabled={!dirty || saving}>
          <CheckIcon /> {saving ? "Salvando..." : "Salvar grade"}
        </button>
        {dirty && <span className="muted">Alterações não salvas</span>}
        {savedMsg && !dirty && <span className="muted">{savedMsg}</span>}
      </div>

      <ExceptionsEditor
        exceptions={schedule.exceptions}
        onChange={(exceptions) => setSchedule({ ...schedule, exceptions })}
        setError={setError}
      />
    </div>
  );
}

function WeeklyGrid({
  selected,
  onChange,
}: {
  selected: Set<string>;
  onChange: (s: Set<string>) => void;
}) {
  // Painting: holding the mouse down sets a mode (add/remove) based on the first
  // cell, then dragging applies that mode to every cell entered.
  const [painting, setPainting] = useState<"add" | "remove" | null>(null);

  useEffect(() => {
    const stop = () => setPainting(null);
    window.addEventListener("mouseup", stop);
    return () => window.removeEventListener("mouseup", stop);
  }, []);

  const apply = (key: string, mode: "add" | "remove") => {
    const next = new Set(selected);
    if (mode === "add") next.add(key);
    else next.delete(key);
    onChange(next);
  };

  const startPaint = (key: string) => {
    const mode = selected.has(key) ? "remove" : "add";
    setPainting(mode);
    apply(key, mode);
  };

  const toggleDay = (wd: number) => {
    const all = GRID_HOURS.every((h) => selected.has(cellKey(wd, h)));
    const next = new Set(selected);
    GRID_HOURS.forEach((h) => (all ? next.delete(cellKey(wd, h)) : next.add(cellKey(wd, h))));
    onChange(next);
  };

  const toggleHour = (hour: number) => {
    const all = WEEKDAYS.every((_, wd) => selected.has(cellKey(wd, hour)));
    const next = new Set(selected);
    WEEKDAYS.forEach((_, wd) =>
      all ? next.delete(cellKey(wd, hour)) : next.add(cellKey(wd, hour)),
    );
    onChange(next);
  };

  return (
    <div className="schedule-grid" onMouseLeave={() => setPainting(null)}>
      <div className="sg-corner" />
      {WEEKDAYS.map((label, wd) => (
        <button
          key={wd}
          type="button"
          className="sg-head"
          onClick={() => toggleDay(wd)}
          title="Marcar/desmarcar dia"
        >
          {label}
        </button>
      ))}

      {GRID_HOURS.map((hour) => (
        <Fragment key={hour}>
          <button
            type="button"
            className="sg-hour"
            onClick={() => toggleHour(hour)}
            title="Marcar/desmarcar hora"
          >
            {String(hour).padStart(2, "0")}:00
          </button>
          {WEEKDAYS.map((_, wd) => {
            const key = cellKey(wd, hour);
            const on = selected.has(key);
            return (
              <div
                key={key}
                className={`sg-cell${on ? " on" : ""}`}
                onMouseDown={() => startPaint(key)}
                onMouseEnter={() => painting && apply(key, painting)}
              />
            );
          })}
        </Fragment>
      ))}
    </div>
  );
}

// Format a UTC ISO instant for display (platform-UTC convention).
const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("pt-BR", {
    timeZone: "UTC",
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("pt-BR", { timeZone: "UTC", hour: "2-digit", minute: "2-digit" });

function isAllDay(e: AvailabilityException): boolean {
  return e.start_at.slice(11, 16) === "00:00" && e.end_at.slice(11, 16) === "23:59";
}

// Human-readable summary of a blocked interval, handling single-day, multi-day
// and timed ranges (all in the platform-UTC convention).
function describeException(e: AvailabilityException): string {
  const sameDay = e.start_at.slice(0, 10) === e.end_at.slice(0, 10);
  if (isAllDay(e)) {
    return sameDay
      ? `${fmtDate(e.start_at)} · dia inteiro`
      : `${fmtDate(e.start_at)} → ${fmtDate(e.end_at)} · dias inteiros`;
  }
  return sameDay
    ? `${fmtDate(e.start_at)} · ${fmtTime(e.start_at)}–${fmtTime(e.end_at)}`
    : `${fmtDate(e.start_at)} ${fmtTime(e.start_at)} → ${fmtDate(e.end_at)} ${fmtTime(e.end_at)}`;
}

function ExceptionsEditor({
  exceptions,
  onChange,
  setError,
}: {
  exceptions: AvailabilityException[];
  onChange: (e: AvailabilityException[]) => void;
  setError: (s: string) => void;
}) {
  // A block spans from a start date/time to an end date/time. The end date is
  // optional — when left empty it defaults to the start date (single-day block).
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [allDay, setAllDay] = useState(true);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("18:00");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const add = async () => {
    if (!startDate) return;
    const endD = endDate || startDate;
    // Build UTC instants directly so the entered wall-clock is stored as-is.
    const start = allDay ? `${startDate}T00:00:00Z` : `${startDate}T${startTime}:00Z`;
    const end = allDay ? `${endD}T23:59:00Z` : `${endD}T${endTime}:00Z`;
    if (end <= start) {
      setError("O fim do bloqueio deve ser após o início.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await addException(start, end, note || undefined);
      onChange(
        [...exceptions, created].sort((a, b) => a.start_at.localeCompare(b.start_at)),
      );
      setStartDate("");
      setEndDate("");
      setNote("");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    setError("");
    try {
      await deleteException(id);
      onChange(exceptions.filter((e) => e.id !== id));
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div style={{ marginTop: 24 }}>
      <h3 style={{ fontSize: 15 }}>Indisponibilidades (feriados, férias, bloqueios)</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Intervalos removidos da disponibilidade recorrente acima. Defina um período de uma data
        (e hora) até outra — por exemplo, férias de uma semana de uma vez.
      </p>

      {exceptions.length === 0 && <p className="muted">Nenhuma indisponibilidade cadastrada.</p>}
      {exceptions.map((e) => (
        <div
          className="list-row"
          key={e.id}
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <span>
            {describeException(e)}
            {e.note ? ` — ${e.note}` : ""}
          </span>
          <button
            className="btn btn-sm btn-ghost btn-icon-only btn-danger"
            onClick={() => remove(e.id)}
            title="Remover bloqueio"
          >
            <TrashIcon />
          </button>
        </div>
      ))}

      <div className="row field" style={{ marginTop: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: "0 0 160px" }}>
          <label>Início</label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        {!allDay && (
          <div style={{ flex: "0 0 110px" }}>
            <label>Hora</label>
            <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
          </div>
        )}
        <div style={{ flex: "0 0 160px" }}>
          <label>Fim</label>
          <input
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
        {!allDay && (
          <div style={{ flex: "0 0 110px" }}>
            <label>Hora</label>
            <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
          </div>
        )}
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Observação (opcional)</label>
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="ex: Férias" />
        </div>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 4 }}>
        <label className="checkbox-pill" style={{ width: "fit-content" }}>
          <input type="checkbox" checked={allDay} onChange={(e) => setAllDay(e.target.checked)} />
          Dia(s) inteiro(s)
        </label>
        <button className="btn btn-sm btn-icon" onClick={add} disabled={busy || !startDate}>
          <PlusIcon /> Adicionar bloqueio
        </button>
      </div>
    </div>
  );
}
