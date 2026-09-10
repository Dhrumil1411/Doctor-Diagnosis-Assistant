import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function HomePage() {
  const { user, logout } = useAuth();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPatients() {
      try {
        const list = await api.get("/patients");
        setPatients(list);
      } catch {
        // ignore load errors for dashboard initial render
      } finally {
        setLoading(false);
      }
    }
    loadPatients();
  }, []);

  return (
    <div className="container">
      <div className="card flex-between">
        <div>
          <h1>Doctor Diagnosis Assistant</h1>
          <p className="muted">
            Signed in as <strong>{user.full_name}</strong> ({user.email}) | Role:{" "}
            <span style={{ textTransform: "uppercase", fontWeight: "bold" }}>{user.role}</span>
          </p>
        </div>
        <button
          onClick={logout}
          className="btn-danger"
          style={{ width: "auto", minWidth: "100px" }}
        >
          Sign out
        </button>
      </div>

      <div style={{ marginBottom: "1.25rem" }}>
        <Link className="btn-link" to="/new-visit">
          + Start New Patient Consultation
        </Link>
      </div>

      <div className="card">
        <h2>Recent Patient Records</h2>
        {loading ? (
          <p className="muted">Loading patient records...</p>
        ) : patients.length === 0 ? (
          <p className="muted">No patient consultations recorded yet.</p>
        ) : (
          <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
            {patients.map((pt) => (
              <PatientCard key={pt.id} patient={pt} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function PatientCard({ patient }) {
  const [visits, setVisits] = useState([]);
  const [loadingVisits, setLoadingVisits] = useState(true);

  useEffect(() => {
    async function fetchVisits() {
      try {
        const vList = await api.get(`/patients/${patient.id}/visits`);
        setVisits(vList);
      } catch {
        // ignore
      } finally {
        setLoadingVisits(false);
      }
    }
    fetchVisits();
  }, [patient.id]);

  return (
    <div
      style={{
        border: "1px solid var(--border-color)",
        borderRadius: "8px",
        padding: "1rem",
        background: "rgba(15, 23, 42, 0.4)",
      }}
    >
      <div className="flex-between">
        <h3 style={{ margin: 0 }}>{patient.full_name}</h3>
        <span className="muted">
          Sex: {patient.sex} | {patient.phone || "No phone"}
        </span>
      </div>

      <div style={{ marginTop: "0.75rem" }}>
        {loadingVisits ? (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Loading visits...
          </p>
        ) : visits.length === 0 ? (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            No visits recorded.
          </p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {visits.map((v) => (
              <Link
                key={v.id}
                to={`/visits/${v.id}/results`}
                className="chip"
                style={{ borderRadius: "6px" }}
              >
                🔍 View AI Results ({new Date(v.occurred_at || Date.now()).toLocaleDateString()})
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
