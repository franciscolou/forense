import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerClient } from "../api/auth";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function RegisterClientPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    phone: "",
    city: "",
    state: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const auth = await registerClient(form);
      setSession(auth);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="form-card">
      <h1>Cadastro de cliente</h1>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label>Nome completo</label>
          <input value={form.full_name} onChange={set("full_name")} required />
        </div>
        <div className="field">
          <label>Email</label>
          <input type="email" value={form.email} onChange={set("email")} required />
        </div>
        <div className="field">
          <label>Senha (mín. 8 caracteres)</label>
          <input type="password" minLength={8} value={form.password} onChange={set("password")} required />
        </div>
        <div className="field">
          <label>Telefone</label>
          <input value={form.phone} onChange={set("phone")} />
        </div>
        <div className="row field">
          <div>
            <label>Cidade</label>
            <input value={form.city} onChange={set("city")} />
          </div>
          <div style={{ maxWidth: 110 }}>
            <label>UF</label>
            <input maxLength={2} value={form.state} onChange={set("state")} />
          </div>
        </div>
        <button className="btn btn-block" disabled={loading}>
          {loading ? "Criando conta..." : "Criar conta"}
        </button>
      </form>
    </div>
  );
}
