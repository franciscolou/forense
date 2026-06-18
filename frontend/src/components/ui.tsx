import type { PracticeArea } from "../types";

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[parts.length - 1]?.[0] ?? "")).toUpperCase();
}

export function Tags({ areas }: { areas: PracticeArea[] }) {
  return (
    <div className="tags">
      {areas.map((a) => (
        <span className="tag" key={a.id}>
          {a.name}
        </span>
      ))}
    </div>
  );
}

export function Spinner({ label = "Carregando..." }: { label?: string }) {
  return <div className="empty">{label}</div>;
}
