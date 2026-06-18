import { Link } from "react-router-dom";

const OPTIONS = [
  {
    to: "/cadastro/cliente",
    title: "Sou cliente",
    desc: "Quero encontrar advogados e escritórios para o meu caso.",
  },
  {
    to: "/cadastro/advogado",
    title: "Sou advogado(a)",
    desc: "Quero divulgar meu perfil profissional e minha OAB.",
  },
  {
    to: "/cadastro/escritorio",
    title: "Sou um escritório",
    desc: "Quero cadastrar minha banca e seus advogados.",
  },
];

export default function RegisterChoicePage() {
  return (
    <div className="container" style={{ maxWidth: 720, margin: "32px auto" }}>
      <h1 className="center">Como você quer se cadastrar?</h1>
      <div className="grid" style={{ marginTop: 24 }}>
        {OPTIONS.map((o) => (
          <Link key={o.to} to={o.to} className="card" style={{ color: "inherit" }}>
            <h3>{o.title}</h3>
            <p className="meta">{o.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
