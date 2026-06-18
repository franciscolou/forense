import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../api/auth";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const auth = await login(email, password);
      setSession(auth);
      navigate(auth.user.role === "client" ? "/" : "/painel");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="form-card">
      <h1>Entrar</h1>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label>Senha</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button className="btn btn-block" disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
      <p className="center muted" style={{ marginTop: 16 }}>
        Não tem conta? <Link to="/cadastro">Cadastre-se</Link>
      </p>
    </div>
  );
}
