import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// The lawyer/firm experience (managing your profile, leads, agenda, etc.) is
// intentionally out of scope for this milestone. This placeholder makes that
// explicit, as requested.
export default function DashboardStub() {
  const { user } = useAuth();
  const label = user?.role === "firm" ? "do escritório" : "do advogado";

  return (
    <div className="container stub">
      <span className="pill">🚧 To be implemented</span>
      <h1>Painel {label}</h1>
      <p className="muted">
        A área de gestão {label} (editar perfil, gerenciar advogados, visualizar contatos)
        ainda não foi implementada. Por enquanto, o foco está na visão do cliente — a busca
        por advogados e escritórios.
      </p>
      <p className="muted">
        Já disponível: configure seu fluxo de agendamento (triagem, agenda, aprovação, pagamento) e
        gerencie as solicitações recebidas.
      </p>
      <p style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
        <Link to="/painel/agendamentos" className="btn">
          Agenda
        </Link>
        <Link to="/painel/agendamento" className="btn btn-ghost">
          Configuração de agendamento
        </Link>
        <Link to="/" className="btn btn-ghost">
          Ir para a busca
        </Link>
      </p>
    </div>
  );
}
