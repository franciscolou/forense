import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getFirm } from "../api/directory";
import { errorMessage } from "../api/client";
import { Spinner, Tags, initials } from "../components/ui";
import type { FirmDetail } from "../types";

export default function FirmDetailPage() {
  const { id } = useParams();
  const [firm, setFirm] = useState<FirmDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getFirm(Number(id))
      .then(setFirm)
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  if (error) return <div className="container"><div className="alert alert-error" style={{ marginTop: 24 }}>{error}</div></div>;
  if (!firm) return <div className="container"><Spinner /></div>;

  return (
    <div className="container">
      <p style={{ marginTop: 16 }}>
        <Link to="/">← Voltar para a busca</Link>
      </p>

      <div className="detail-header">
        <div className="avatar">{initials(firm.legal_name)}</div>
        <div>
          <h1 style={{ margin: 0 }}>{firm.legal_name}</h1>
          <div className="muted">
            CNPJ {firm.cnpj} · {firm.oab_registration}
          </div>
          {firm.city && (
            <div className="muted">
              {firm.city}/{firm.state}
            </div>
          )}
        </div>
      </div>

      <div className="section">
        <h2>Áreas de atuação</h2>
        <Tags areas={firm.practice_areas} />
      </div>

      {firm.description && (
        <div className="section">
          <h2>Sobre o escritório</h2>
          <p style={{ margin: 0 }}>{firm.description}</p>
        </div>
      )}

      <div className="section">
        <h2>Advogados ({firm.lawyers.length})</h2>
        {firm.lawyers.map((l) => (
          <div className="list-row" key={l.id}>
            <Link to={`/advogados/${l.id}`}>{l.full_name}</Link>{" "}
            <span className="muted">
              · OAB/{l.oab_uf} {l.oab_number}
            </span>
          </div>
        ))}
      </div>

      <div className="section">
        <h2>Contato</h2>
        <p style={{ margin: 0 }}>
          <a href={`mailto:${firm.email}`}>{firm.email}</a>
          {firm.website && (
            <>
              {" · "}
              <a href={firm.website} target="_blank" rel="noreferrer">
                {firm.website}
              </a>
            </>
          )}
        </p>
      </div>
      <div className="spacer" />
    </div>
  );
}
