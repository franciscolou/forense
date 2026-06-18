import type { PracticeArea } from "../types";

// Multi-select pill picker for areas of practice.
export default function PracticeAreaPicker({
  areas,
  selected,
  onChange,
}: {
  areas: PracticeArea[];
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  const toggle = (id: number) => {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  return (
    <div className="checkbox-list">
      {areas.map((a) => {
        const checked = selected.includes(a.id);
        return (
          <label key={a.id} className={`checkbox-pill ${checked ? "checked" : ""}`}>
            <input type="checkbox" checked={checked} onChange={() => toggle(a.id)} />
            {a.name}
          </label>
        );
      })}
    </div>
  );
}
