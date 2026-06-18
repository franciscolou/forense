import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerLawyer } from "../api/auth";
import type { LawyerRegisterPayload } from "../api/auth";
import { errorMessage } from "../api/client";
import { listPracticeAreas } from "../api/directory";
import LawyerSubForm, { emptyLawyer } from "../components/LawyerSubForm";
import { useAuth } from "../context/AuthContext";
import type { PracticeArea } from "../types";

export default function RegisterLawyerPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [areas, setAreas] = useState<PracticeArea[]>([]);
  const [form, setForm] = useState<LawyerRegisterPayload>(emptyLawyer());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listPracticeAreas().then(setAreas).catch(() => undefined);
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const auth = await registerLawyer(form);
      setSession(auth);
      navigate("/painel");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="form-card" style={{ maxWidth: 720 }}>
      <h1>Cadastro de advogado(a)</h1>
      <div className="alert alert-info">
        A validação do número da OAB será feita posteriormente — seu perfil ficará marcado como
        "OAB pendente" até lá.
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={onSubmit}>
        <LawyerSubForm value={form} onChange={setForm} areas={areas} />
        <button className="btn btn-block" disabled={loading}>
          {loading ? "Criando conta..." : "Criar conta"}
        </button>
      </form>
    </div>
  );
}
