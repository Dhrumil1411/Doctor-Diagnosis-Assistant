import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client.js";
import { toNum } from "./fields.jsx";

export default function SymptomChecklist({ entries, onChange }) {
  const [vocabulary, setVocabulary] = useState([]);
  const [query, setQuery] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    api
      .get("/symptom-vocabulary")
      .then(setVocabulary)
      .catch(() => setLoadError("Could not load symptom vocabulary."));
  }, []);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return vocabulary
      .filter(
        (s) => s.display_name.toLowerCase().includes(q) || s.id.includes(q)
      )
      .slice(0, 12);
  }, [query, vocabulary]);

  function add(symptom) {
    if (entries.some((e) => e.name === symptom.id)) return;
    onChange([...entries, { name: symptom.id, status: "present", severity: "", duration: "" }]);
    setQuery("");
  }

  function update(index, patch) {
    onChange(entries.map((e, i) => (i === index ? { ...e, ...patch } : e)));
  }

  function remove(index) {
    onChange(entries.filter((_, i) => i !== index));
  }

  const nameOf = (id) =>
    vocabulary.find((s) => s.id === id)?.display_name ?? id;

  return (
    <div>
      <div className="field">
        <label htmlFor="symptom-search">Search symptoms</label>
        <input
          id="symptom-search"
          type="search"
          value={query}
          placeholder="e.g. fever, rash, headache..."
          onChange={(e) => setQuery(e.target.value)}
        />
        {loadError && <p className="error">{loadError}</p>}
        {results.length > 0 && (
          <ul className="search-results">
            {results.map((s) => (
              <li key={s.id}>
                <button type="button" className="chip" onClick={() => add(s)}>
                  + {s.display_name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {entries.length === 0 ? (
        <p className="muted">No symptoms marked yet. Search above to add them.</p>
      ) : (
        <div className="table-responsive">
          <table className="entry-table">
            <thead>
              <tr>
                <th>Symptom</th>
                <th>Status</th>
                <th>Severity (1-10)</th>
                <th>Duration</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={e.name}>
                  <td>{nameOf(e.name)}</td>
                  <td>
                    <select
                      value={e.status}
                      onChange={(ev) => update(i, { status: ev.target.value })}
                    >
                      <option value="present">Present</option>
                      <option value="absent">Absent</option>
                      <option value="unsure">Unsure</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={e.severity}
                      disabled={e.status !== "present"}
                      onChange={(ev) => update(i, { severity: toNum(ev.target.value) ?? "" })}
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      placeholder="e.g. 3 days"
                      value={e.duration}
                      onChange={(ev) => update(i, { duration: ev.target.value })}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => remove(i)}
                      aria-label={`Remove ${nameOf(e.name)}`}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
