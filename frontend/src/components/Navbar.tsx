import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Lawyer/firm dashboards are not built yet; the navbar links there land on a
// "to be implemented" placeholder (see DashboardStub).
export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <header className="navbar">
      <div className="container">
        <Link to="/" className="brand">
          ⚖ Forense
        </Link>
        <nav className="nav-links">
          <Link to="/">Buscar</Link>
          {user ? (
            <>
              {user.role !== "client" && <Link to="/painel">Painel</Link>}
              <span className="muted">{user.full_name}</span>
              <button className="btn-link" onClick={onLogout}>
                Sair
              </button>
            </>
          ) : (
            <>
              <Link to="/entrar">Entrar</Link>
              <Link to="/cadastro" className="btn btn-sm">
                Cadastrar
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
