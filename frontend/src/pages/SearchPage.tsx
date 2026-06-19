import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPracticeAreas, searchFirms, searchLawyers } from "../api/directory";
import { errorMessage } from "../api/client";
import { Spinner, Tags, initials } from "../components/ui";
import type { FirmSummary, LawyerSummary, PracticeArea } from "../types";

type Mode = "lawyers" | "firms";

export default function SearchPage() {
  const [mode, setMode] = useState<Mode>("lawyers");
  const [areas, setAreas] = useState<PracticeArea[]>([]);
  const [areaId, setAreaId] = useState<number | null>(null);
  const [query, setQuery] = useState("");

  const [lawyers, setLawyers] = useState<LawyerSummary[]>([]);
  const [firms, setFirms] = useState<FirmSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listPracticeAreas().then(setAreas).catch(() => undefined);
  }, []);

  // Re-run the search whenever the tab or the area filter changes. The free-text
  // query is applied on submit so we don't fire a request per keystroke.
  useEffect(() => {
    runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, areaId]);

  async function runSearch(e?: React.FormEvent) {
    e?.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "lawyers") {
        const page = await searchLawyers({ practice_area_id: areaId, q: query });
        setLawyers(page.items);
        setTotal(page.total);
      } else {
        const page = await searchFirms({ practice_area_id: areaId, q: query });
        setFirms(page.items);
        setTotal(page.total);
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="hero">
        <div className="container">
          <h1>Facilite o Direito para o seu caso</h1>
          <p>Busque por área de atuação, nome ou cidade.</p>
        </div>
      </section>

      <div className="container">
        <div className="tabs" style={{ marginTop: 24 }}>
          <button
            className={`tab ${mode === "lawyers" ? "active" : ""}`}
            onClick={() => setMode("lawyers")}
          >
            Advogados
          </button>
          <button
            className={`tab ${mode === "firms" ? "active" : ""}`}
            onClick={() => setMode("firms")}
          >
            Escritórios
          </button>
        </div>

        <form className="toolbar" onSubmit={runSearch}>
          <div className="grow">
            <label>Área de atuação</label>
            <select
              value={areaId ?? ""}
              onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Todas as áreas</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grow">
            <label>Busca</label>
            <input
              placeholder={mode === "lawyers" ? "Nome, cidade..." : "Razão social, cidade..."}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button className="btn" type="submit">
            Buscar
          </button>
        </form>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <Spinner />
        ) : total === 0 ? (
          <div className="empty">Nenhum resultado encontrado.</div>
        ) : (
          <>
            <p className="muted">{total} resultado(s)</p>
            <div className="grid">
              {mode === "lawyers"
                ? lawyers.map((l) => <LawyerCard key={l.id} lawyer={l} />)
                : firms.map((f) => <FirmCard key={f.id} firm={f} />)}
            </div>
          </>
        )}
        <div className="spacer" />
      </div>
    </>
  );
}

function LawyerCard({ lawyer }: { lawyer: LawyerSummary }) {
  return (
    <Link to={`/advogados/${lawyer.id}`} className="card" style={{ color: "inherit" }}>
      <div className="card-head">
        <div className="avatar">{initials(lawyer.full_name)}</div>
        <div>
          <h3>{lawyer.full_name}</h3>
          <div className="meta">
            OAB/{lawyer.oab_uf} {lawyer.oab_number}
            {lawyer.city ? ` · ${lawyer.city}/${lawyer.state}` : ""}
          </div>
        </div>
      </div>
      {lawyer.years_of_experience != null && (
        <div className="meta">{lawyer.years_of_experience} anos de atuação</div>
      )}
      <Tags areas={lawyer.practice_areas} />
    </Link>
  );
}

function FirmCard({ firm }: { firm: FirmSummary }) {
  return (
    <Link to={`/escritorios/${firm.id}`} className="card" style={{ color: "inherit" }}>
      <div className="card-head">
        <div className="avatar">{initials(firm.legal_name)}</div>
        <div>
          <h3>{firm.legal_name}</h3>
          <div className="meta">
            {firm.city ? `${firm.city}/${firm.state}` : "Escritório de advocacia"}
          </div>
        </div>
      </div>
      <Tags areas={firm.practice_areas} />
    </Link>
  );
}
