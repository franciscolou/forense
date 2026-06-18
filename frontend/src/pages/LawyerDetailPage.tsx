import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getLawyer } from "../api/directory";
import { errorMessage } from "../api/client";
import { Spinner, Tags, initials } from "../components/ui";
import type { LawyerDetail } from "../types";

export default function LawyerDetailPage() {
  const { id } = useParams();
  const [lawyer, setLawyer] = useState<LawyerDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getLawyer(Number(id))
      .then(setLawyer)
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  if (error) return <div className="container"><div className="alert alert-error" style={{ marginTop: 24 }}>{error}</div></div>;
  if (!lawyer) return <div className="container"><Spinner /></div>;

  return (
    <div className="container">
      <p style={{ marginTop: 16 }}>
        <Link to="/">← Voltar para a busca</Link>
      </p>

      <div className="detail-header">
        <div className="avatar">{initials(lawyer.full_name)}</div>
        <div>
          <h1 style={{ margin: 0 }}>{lawyer.full_name}</h1>
          <div className="muted">
            OAB/{lawyer.oab_uf} {lawyer.oab_number}{" "}
            <span className={`tag ${lawyer.oab_verified ? "badge-verified" : "badge-pending"}`}>
              {lawyer.oab_verified ? "OAB verificada" : "OAB pendente"}
            </span>
          </div>
          {lawyer.city && (
            <div className="muted">
              {lawyer.city}/{lawyer.state}
              {lawyer.years_of_experience != null && ` · ${lawyer.years_of_experience} anos de atuação`}
            </div>
          )}
        </div>
      </div>

      <div className="section">
        <h2>Áreas de atuação</h2>
        <Tags areas={lawyer.practice_areas} />
      </div>

      {lawyer.bio && (
        <div className="section">
          <h2>Sobre</h2>
          <p style={{ margin: 0 }}>{lawyer.bio}</p>
        </div>
      )}

      {lawyer.educations.length > 0 && (
        <div className="section">
          <h2>Formação</h2>
          {lawyer.educations.map((e) => (
            <div className="list-row" key={e.id}>
              <strong>{e.field_of_study ?? e.degree}</strong> — {e.institution}
              {e.year ? ` (${e.year})` : ""}{" "}
              <span className="muted">· {e.degree}</span>
            </div>
          ))}
        </div>
      )}

      {lawyer.languages.length > 0 && (
        <div className="section">
          <h2>Idiomas</h2>
          {lawyer.languages.map((l) => (
            <div className="list-row" key={l.id}>
              {l.language}
              {l.proficiency ? <span className="muted"> · {l.proficiency}</span> : null}
            </div>
          ))}
        </div>
      )}

      <div className="section">
        <h2>Contato</h2>
        <p style={{ margin: 0 }}>
          <a href={`mailto:${lawyer.email}`}>{lawyer.email}</a>
        </p>
      </div>
      <div className="spacer" />
    </div>
  );
}
