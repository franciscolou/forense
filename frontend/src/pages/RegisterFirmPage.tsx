import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerFirm } from "../api/auth";
import type { FirmRegisterPayload, LawyerRegisterPayload } from "../api/auth";
import { errorMessage } from "../api/client";
import { listPracticeAreas } from "../api/directory";
import LawyerSubForm, { emptyLawyer } from "../components/LawyerSubForm";
import PracticeAreaPicker from "../components/PracticeAreaPicker";
import { useAuth } from "../context/AuthContext";
import type { PracticeArea } from "../types";

export default function RegisterFirmPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [areas, setAreas] = useState<PracticeArea[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [firm, setFirm] = useState({
    email: "",
    password: "",
    legal_name: "",
    cnpj: "",
    oab_registration: "",
    description: "",
    city: "",
    state: "",
    website: "",
    practice_area_ids: [] as number[],
  });
  // Composition: existing lawyers referenced by id, and/or brand-new lawyers.
  const [existingIds, setExistingIds] = useState("");
  const [newLawyers, setNewLawyers] = useState<LawyerRegisterPayload[]>([]);

  useEffect(() => {
    listPracticeAreas().then(setAreas).catch(() => undefined);
  }, []);

  const setF = (k: keyof typeof firm) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setFirm({ ...firm, [k]: e.target.value });

  const parsedExisting = existingIds
    .split(",")
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isInteger(n) && n > 0);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (parsedExisting.length === 0 && newLawyers.length === 0) {
      setError("O escritório deve ter ao menos um advogado (existente ou novo).");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payload: FirmRegisterPayload = {
        ...firm,
        existing_lawyer_ids: parsedExisting,
        new_lawyers: newLawyers,
      };
      const auth = await registerFirm(payload);
      setSession(auth);
      navigate("/painel");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="form-card" style={{ maxWidth: 760 }}>
      <h1>Cadastro de escritório</h1>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label>Razão social</label>
          <input value={firm.legal_name} onChange={setF("legal_name")} required />
        </div>
        <div className="row field">
          <div>
            <label>CNPJ</label>
            <input value={firm.cnpj} onChange={setF("cnpj")} placeholder="00.000.000/0000-00" required />
          </div>
          <div>
            <label>Registro OAB do escritório</label>
            <input value={firm.oab_registration} onChange={setF("oab_registration")} required />
          </div>
        </div>
        <div className="field">
          <label>Email de contato</label>
          <input type="email" value={firm.email} onChange={setF("email")} required />
        </div>
        <div className="field">
          <label>Senha (mín. 8 caracteres)</label>
          <input type="password" minLength={8} value={firm.password} onChange={setF("password")} required />
        </div>
        <div className="row field">
          <div>
            <label>Cidade</label>
            <input value={firm.city} onChange={setF("city")} />
          </div>
          <div style={{ maxWidth: 110 }}>
            <label>UF</label>
            <input maxLength={2} value={firm.state} onChange={setF("state")} />
          </div>
          <div>
            <label>Website</label>
            <input value={firm.website} onChange={setF("website")} placeholder="https://" />
          </div>
        </div>
        <div className="field">
          <label>Descrição</label>
          <textarea rows={3} value={firm.description} onChange={setF("description")} />
        </div>
        <div className="field">
          <label>Áreas de atuação</label>
          <PracticeAreaPicker
            areas={areas}
            selected={firm.practice_area_ids}
            onChange={(ids) => setFirm({ ...firm, practice_area_ids: ids })}
          />
        </div>

        <hr style={{ margin: "24px 0", border: "none", borderTop: "1px solid var(--border)" }} />
        <h2 style={{ fontSize: 18 }}>Composição do escritório</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Um escritório precisa de ao menos um advogado. Informe IDs de advogados já cadastrados
          e/ou cadastre novos advogados abaixo.
        </p>

        <div className="field">
          <label>IDs de advogados já cadastrados (separados por vírgula)</label>
          <input
            value={existingIds}
            onChange={(e) => setExistingIds(e.target.value)}
            placeholder="ex: 1, 2"
          />
        </div>

        {newLawyers.map((nl, i) => (
          <div className="section" key={i}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>Novo advogado #{i + 1}</h2>
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={() => setNewLawyers(newLawyers.filter((_, idx) => idx !== i))}
              >
                Remover
              </button>
            </div>
            <LawyerSubForm
              value={nl}
              areas={areas}
              onChange={(v) => setNewLawyers(newLawyers.map((x, idx) => (idx === i ? v : x)))}
            />
          </div>
        ))}

        <div className="field">
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setNewLawyers([...newLawyers, emptyLawyer()])}
          >
            + Cadastrar novo advogado na composição
          </button>
        </div>

        <button className="btn btn-block" disabled={loading}>
          {loading ? "Criando escritório..." : "Criar escritório"}
        </button>
      </form>
    </div>
  );
}
