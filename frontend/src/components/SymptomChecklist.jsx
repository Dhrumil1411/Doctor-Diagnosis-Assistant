import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client.js";
import { toNum } from "./fields.jsx";

const CATEGORIES = [
  "All",
  "Constitutional",
  "Respiratory",
  "Cardiovascular",
  "Gastrointestinal",
  "Neurological",
  "Dermatological",
  "Genitourinary",
  "Musculoskeletal",
];

export default function SymptomChecklist({ entries, onChange }) {
  const [vocabulary, setVocabulary] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    api
      .get("/symptom-vocabulary")
      .then(setVocabulary)
      .catch(() => setLoadError("Could not load symptom vocabulary."));
  }, []);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    return vocabulary
      .filter((s) => {
        const matchesCategory =
          selectedCategory === "All" ||
          (s.category && s.category.toLowerCase() === selectedCategory.toLowerCase());
        if (!matchesCategory) return false;

        if (!q) return selectedCategory !== "All";

        return (
          s.display_name.toLowerCase().includes(q) ||
          s.id.includes(q) ||
          (s.hpo_id && s.hpo_id.toLowerCase().includes(q))
        );
      })
      .slice(0, 15);
  }, [query, selectedCategory, vocabulary]);

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

  const getSymptomMeta = (id) =>
    vocabulary.find((s) => s.id === id) || { display_name: id.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase()), hpo_id: null };

  return (
    <div>
      {/* Category Filter Pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginBottom: "0.85rem" }}>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setSelectedCategory(cat)}
            style={{
              padding: "0.3rem 0.75rem",
              fontSize: "0.78rem",
              fontWeight: selectedCategory === cat ? "700" : "500",
              borderRadius: "9999px",
              border: selectedCategory === cat ? "1px solid #0284c7" : "1px solid var(--border-medium)",
              background: selectedCategory === cat ? "var(--primary-light)" : "#ffffff",
              color: selectedCategory === cat ? "var(--primary-text)" : "var(--text-body)",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="field">
        <label htmlFor="symptom-search">Search symptoms (by name, keyword, or HPO code)</label>
        <input
          id="symptom-search"
          type="search"
          value={query}
          placeholder="e.g. fever, HP:0001945, chest pain, rash, dyspnea..."
          onChange={(e) => setQuery(e.target.value)}
        />
        {loadError && <p className="error">{loadError}</p>}
        {results.length > 0 && (
          <ul style={{ maxHeight: "240px", overflowY: "auto", display: "flex", flexWrap: "wrap", gap: "0.4rem", padding: "0.6rem 0", listStyle: "none" }}>
            {results.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => add(s)}
                  className="btn-secondary"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.78rem", padding: "0.3rem 0.65rem" }}
                >
                  <span style={{ color: "var(--primary)", fontWeight: "700" }}>+</span>
                  <span>{s.display_name}</span>
                  {s.hpo_id && (
                    <span className="badge badge-primary" style={{ fontSize: "0.68rem", padding: "0.05rem 0.35rem" }}>
                      {s.hpo_id}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {entries.length === 0 ? (
        <p className="text-muted" style={{ padding: "0.75rem", background: "var(--bg-subtle)", borderRadius: "6px", border: "1px dashed var(--border-medium)" }}>
          No symptoms marked yet. Type in the search box above, select a category pill, or use the <strong>Smart Note Extractor</strong> at the top of the page to auto-populate symptoms.
        </p>
      ) : (
        <div style={{ overflowX: "auto", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", marginTop: "0.75rem" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "var(--bg-subtle)", borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                <th style={{ padding: "0.65rem 0.85rem", fontWeight: "700", color: "var(--text-main)" }}>Symptom & HPO Phenotype</th>
                <th style={{ padding: "0.65rem 0.85rem", fontWeight: "700", color: "var(--text-main)", width: "130px" }}>Status</th>
                <th style={{ padding: "0.65rem 0.85rem", fontWeight: "700", color: "var(--text-main)", width: "110px" }}>Severity (1-10)</th>
                <th style={{ padding: "0.65rem 0.85rem", fontWeight: "700", color: "var(--text-main)", width: "150px" }}>Duration</th>
                <th style={{ padding: "0.65rem 0.85rem", width: "50px" }}></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => {
                const meta = getSymptomMeta(e.name);
                return (
                  <tr key={e.name} style={{ borderBottom: "1px solid var(--border-subtle)", background: i % 2 === 0 ? "#ffffff" : "#fafafa" }}>
                    <td style={{ padding: "0.5rem 0.85rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                        <strong style={{ color: "var(--text-main)" }}>{meta.display_name}</strong>
                        {meta.hpo_id && (
                          <span className="badge badge-primary" style={{ fontSize: "0.68rem" }}>
                            {meta.hpo_id}
                          </span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: "0.5rem 0.85rem" }}>
                      <select
                        value={e.status}
                        onChange={(ev) => update(i, { status: ev.target.value })}
                        style={{ padding: "0.35rem 0.5rem", fontSize: "0.82rem" }}
                      >
                        <option value="present">Present</option>
                        <option value="absent">Absent</option>
                        <option value="unsure">Unsure</option>
                      </select>
                    </td>
                    <td style={{ padding: "0.5rem 0.85rem" }}>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={e.severity}
                        disabled={e.status !== "present"}
                        onChange={(ev) => update(i, { severity: toNum(ev.target.value) ?? "" })}
                        style={{ padding: "0.35rem 0.5rem", fontSize: "0.82rem" }}
                      />
                    </td>
                    <td style={{ padding: "0.5rem 0.85rem" }}>
                      <input
                        type="text"
                        placeholder="e.g. 3 days"
                        value={e.duration}
                        onChange={(ev) => update(i, { duration: ev.target.value })}
                        style={{ padding: "0.35rem 0.5rem", fontSize: "0.82rem" }}
                      />
                    </td>
                    <td style={{ padding: "0.5rem 0.85rem", textAlign: "center" }}>
                      <button
                        type="button"
                        className="btn-danger"
                        onClick={() => remove(i)}
                        style={{ padding: "0.25rem 0.55rem", fontSize: "0.75rem" }}
                        aria-label={`Remove ${meta.display_name}`}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
