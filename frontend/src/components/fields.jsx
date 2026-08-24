export function FormSection({ title, hint, children }) {
  return (
    <section className="card section">
      <h2>{title}</h2>
      {hint && <p className="muted">{hint}</p>}
      {children}
    </section>
  );
}

export function Labeled({ label, htmlFor, children, className = "" }) {
  return (
    <div className={`field ${className}`}>
      <label htmlFor={htmlFor}>{label}</label>
      {children}
    </div>
  );
}

export function TextInput({ id, label, value, onChange, type = "text", placeholder, min, max, step }) {
  return (
    <Labeled label={label} htmlFor={id}>
      <input
        id={id}
        type={type}
        value={value}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(e.target.value)}
      />
    </Labeled>
  );
}

export function SelectInput({ id, label, value, onChange, options }) {
  return (
    <Labeled label={label} htmlFor={id}>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Labeled>
  );
}

export function TextArea({ id, label, value, onChange, rows = 3, placeholder }) {
  return (
    <Labeled label={label} htmlFor={id}>
      <textarea
        id={id}
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </Labeled>
  );
}

export function toNum(value) {
  if (value === "" || value === null || value === undefined) return undefined;
  const n = Number(value);
  return Number.isNaN(n) ? undefined : n;
}

export function compact(obj) {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v !== "" && v !== undefined && v !== null)
  );
}
