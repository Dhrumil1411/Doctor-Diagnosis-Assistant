export default function ListEditor({ entries, onChange, columns, makeNew, addLabel }) {
  function update(index, key, value) {
    onChange(entries.map((e, i) => (i === index ? { ...e, [key]: value } : e)));
  }

  return (
    <div>
      {entries.length > 0 && (
        <table className="entry-table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key}>{c.label}</th>
              ))}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => (
              <tr key={i}>
                {columns.map((c) => (
                  <td key={c.key}>
                    {c.type === "select" ? (
                      <select
                        value={entry[c.key] ?? ""}
                        onChange={(e) => update(i, c.key, e.target.value)}
                      >
                        {c.options.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    ) : c.type === "checkbox" ? (
                      <input
                        type="checkbox"
                        checked={Boolean(entry[c.key])}
                        onChange={(e) => update(i, c.key, e.target.checked)}
                      />
                    ) : (
                      <input
                        type={c.type ?? "text"}
                        value={entry[c.key] ?? ""}
                        placeholder={c.placeholder}
                        min={c.min}
                        max={c.max}
                        onChange={(e) =>
                          update(i, c.key, c.type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value)
                        }
                      />
                    )}
                  </td>
                ))}
                <td>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() => onChange(entries.filter((_, j) => j !== i))}
                  >
                    x
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <button type="button" className="btn-secondary" onClick={() => onChange([...entries, makeNew()])}>
        + {addLabel}
      </button>
    </div>
  );
}
