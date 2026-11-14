import { useState } from "react";
import { useNavigate } from "react-router-dom";

import DemoBanner from "../components/DemoBanner.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleLogin(loginEmail, loginPass) {
    setError("");
    setBusy(true);
    try {
      await login((loginEmail || email).trim(), loginPass || password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err.status === 401
          ? "Incorrect email or password."
          : err.status === 403
            ? "This account has been disabled. Contact an admin."
            : err.readableMessage || `Login failed (${err.message})`
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
      <div className="card" style={{ maxWidth: "440px", width: "100%", padding: "2rem", boxShadow: "var(--shadow-lg)" }}>
        <DemoBanner inline />
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              background: "linear-gradient(135deg, #0284c7, #0369a1)",
              borderRadius: "12px",
              color: "white",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.6rem",
              marginBottom: "0.75rem",
              boxShadow: "0 4px 8px rgba(2, 132, 199, 0.25)",
            }}
          >
            ⚕️
          </div>
          <h1 style={{ fontSize: "1.35rem", marginBottom: "0.25rem" }}>Doctor Diagnosis Assistant</h1>
          <p className="text-muted" style={{ fontSize: "0.85rem" }}>
            Clinical Decision Support & Diagnosis Workstation
          </p>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); handleLogin(); }}>
          <div className="field">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="doctor@example.com"
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && <div className="error">{error}</div>}

          <button
            type="submit"
            disabled={busy}
            style={{ width: "100%", marginTop: "0.5rem", padding: "0.65rem" }}
          >
            {busy ? (
              <>
                <span className="spinner" />
                <span>Signing in...</span>
              </>
            ) : (
              "Sign In to Clinic Portal"
            )}
          </button>
        </form>

        <div style={{ marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px solid var(--border-subtle)" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "var(--text-muted)", display: "block", marginBottom: "0.5rem", textTransform: "uppercase" }}>
            ⚡ 1-Click Demo Logins:
          </span>
          <div style={{ display: "grid", gap: "0.5rem" }}>
            <button
              type="button"
              onClick={() => handleLogin("doctor@example.com", "doctor123")}
              className="btn-secondary"
              style={{ justifyContent: "space-between", padding: "0.45rem 0.75rem", fontSize: "0.8rem" }}
            >
              <span>🩺 <strong>Dr. Emily Vance</strong> (Doctor)</span>
              <span className="badge badge-primary">Auto-fill</span>
            </button>
            <button
              type="button"
              onClick={() => handleLogin("admin@example.com", "admin123")}
              className="btn-secondary"
              style={{ justifyContent: "space-between", padding: "0.45rem 0.75rem", fontSize: "0.8rem" }}
            >
              <span>🛡️ <strong>Dr. Marcus Reed</strong> (Admin)</span>
              <span className="badge badge-neutral">Auto-fill</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
