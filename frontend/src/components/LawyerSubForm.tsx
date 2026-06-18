import type { LawyerRegisterPayload } from "../api/auth";
import type { PracticeArea } from "../types";
import PracticeAreaPicker from "./PracticeAreaPicker";

export const BR_STATES = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
];

export function emptyLawyer(): LawyerRegisterPayload {
  return {
    email: "",
    password: "",
    full_name: "",
    oab_uf: "",
    oab_number: "",
    bio: "",
    years_of_experience: undefined,
    city: "",
    state: "",
    practice_area_ids: [],
    educations: [],
    languages: [],
  };
}

// Controlled sub-form capturing every field of a lawyer profile. Reused by the
// standalone lawyer registration and by the firm registration (new members).
export default function LawyerSubForm({
  value,
  onChange,
  areas,
  showCredentials = true,
}: {
  value: LawyerRegisterPayload;
  onChange: (v: LawyerRegisterPayload) => void;
  areas: PracticeArea[];
  showCredentials?: boolean;
}) {
  const patch = (p: Partial<LawyerRegisterPayload>) => onChange({ ...value, ...p });

  return (
    <>
      {showCredentials && (
        <>
          <div className="field">
            <label>Nome completo</label>
            <input value={value.full_name} onChange={(e) => patch({ full_name: e.target.value })} required />
          </div>
          <div className="field">
            <label>Email</label>
            <input type="email" value={value.email} onChange={(e) => patch({ email: e.target.value })} required />
          </div>
          <div className="field">
            <label>Senha (mín. 8 caracteres)</label>
            <input
              type="password"
              minLength={8}
              value={value.password}
              onChange={(e) => patch({ password: e.target.value })}
              required
            />
          </div>
        </>
      )}

      {/* OAB id is collected as two separate fields (UF + número) as specified. */}
      <div className="row field">
        <div style={{ maxWidth: 140 }}>
          <label>OAB — UF</label>
          <select value={value.oab_uf} onChange={(e) => patch({ oab_uf: e.target.value })} required>
            <option value="">UF</option>
            {BR_STATES.map((uf) => (
              <option key={uf} value={uf}>
                {uf}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>OAB — Número</label>
          <input
            value={value.oab_number}
            onChange={(e) => patch({ oab_number: e.target.value.replace(/\D/g, "") })}
            placeholder="123456"
            required
          />
        </div>
      </div>

      <div className="row field">
        <div>
          <label>Cidade</label>
          <input value={value.city} onChange={(e) => patch({ city: e.target.value })} />
        </div>
        <div style={{ maxWidth: 110 }}>
          <label>UF de atuação</label>
          <input maxLength={2} value={value.state} onChange={(e) => patch({ state: e.target.value })} />
        </div>
        <div style={{ maxWidth: 140 }}>
          <label>Anos de atuação</label>
          <input
            type="number"
            min={0}
            value={value.years_of_experience ?? ""}
            onChange={(e) =>
              patch({ years_of_experience: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </div>
      </div>

      <div className="field">
        <label>Resumo profissional</label>
        <textarea rows={3} value={value.bio} onChange={(e) => patch({ bio: e.target.value })} />
      </div>

      <div className="field">
        <label>Áreas de atuação</label>
        <PracticeAreaPicker
          areas={areas}
          selected={value.practice_area_ids}
          onChange={(ids) => patch({ practice_area_ids: ids })}
        />
      </div>

      <EducationList value={value} patch={patch} />
      <LanguageList value={value} patch={patch} />
    </>
  );
}

function EducationList({
  value,
  patch,
}: {
  value: LawyerRegisterPayload;
  patch: (p: Partial<LawyerRegisterPayload>) => void;
}) {
  const add = () =>
    patch({ educations: [...value.educations, { degree: "graduacao", institution: "" }] });
  const update = (i: number, field: string, v: string | number | undefined) =>
    patch({
      educations: value.educations.map((e, idx) => (idx === i ? { ...e, [field]: v } : e)),
    });
  const remove = (i: number) =>
    patch({ educations: value.educations.filter((_, idx) => idx !== i) });

  return (
    <div className="field">
      <label>Formações e pós-graduações</label>
      {value.educations.map((e, i) => (
        <div className="row" key={i} style={{ marginBottom: 8 }}>
          <select value={e.degree} onChange={(ev) => update(i, "degree", ev.target.value)}>
            <option value="graduacao">Graduação</option>
            <option value="pos-graduacao">Pós-graduação</option>
            <option value="mestrado">Mestrado</option>
            <option value="doutorado">Doutorado</option>
            <option value="certificacao">Certificação</option>
          </select>
          <input
            placeholder="Instituição"
            value={e.institution}
            onChange={(ev) => update(i, "institution", ev.target.value)}
          />
          <input
            placeholder="Área"
            value={e.field_of_study ?? ""}
            onChange={(ev) => update(i, "field_of_study", ev.target.value)}
          />
          <input
            placeholder="Ano"
            type="number"
            style={{ maxWidth: 90 }}
            value={e.year ?? ""}
            onChange={(ev) => update(i, "year", ev.target.value ? Number(ev.target.value) : undefined)}
          />
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => remove(i)}>
            ✕
          </button>
        </div>
      ))}
      <button type="button" className="btn btn-sm" onClick={add}>
        + Adicionar formação
      </button>
    </div>
  );
}

function LanguageList({
  value,
  patch,
}: {
  value: LawyerRegisterPayload;
  patch: (p: Partial<LawyerRegisterPayload>) => void;
}) {
  const add = () => patch({ languages: [...value.languages, { language: "", proficiency: "fluente" }] });
  const update = (i: number, field: string, v: string) =>
    patch({ languages: value.languages.map((l, idx) => (idx === i ? { ...l, [field]: v } : l)) });
  const remove = (i: number) => patch({ languages: value.languages.filter((_, idx) => idx !== i) });

  return (
    <div className="field">
      <label>Idiomas</label>
      {value.languages.map((l, i) => (
        <div className="row" key={i} style={{ marginBottom: 8 }}>
          <input
            placeholder="Idioma"
            value={l.language}
            onChange={(ev) => update(i, "language", ev.target.value)}
          />
          <select value={l.proficiency ?? ""} onChange={(ev) => update(i, "proficiency", ev.target.value)}>
            <option value="basico">Básico</option>
            <option value="intermediario">Intermediário</option>
            <option value="avancado">Avançado</option>
            <option value="fluente">Fluente</option>
            <option value="nativo">Nativo</option>
          </select>
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => remove(i)}>
            ✕
          </button>
        </div>
      ))}
      <button type="button" className="btn btn-sm" onClick={add}>
        + Adicionar idioma
      </button>
    </div>
  );
}
