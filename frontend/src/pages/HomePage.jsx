import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";

export default function HomePage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    async function loadPatients() {
      try {
        const list = await api.get("/patients");
        setPatients(list);
      } catch {
        // ignore load errors
      } finally {
        setLoading(false);
      }
    }
    loadPatients();
  }, []);

  const filteredPatients = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    if (!q) return patients;
    return patients.filter((p) =>
      (p.full_name && p.full_name.toLowerCase().includes(q)) ||
      (p.mrn && p.mrn.toLowerCase().includes(q)) ||
      (p.phone && p.phone.includes(q))
    );
  }, [patients, searchTerm]);

  return (
    <div className="container">
      {/* Top Banner / Actions */}
      <div className="card" style={{ background: "linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)", border: "1px solid #bae6fd" }}>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
          <div>
            <h1 style={{ color: "#0f172a" }}>Clinical Encounters & Patient Records</h1>
            <p className="text-muted">
              Select an existing patient file to review differential diagnoses or start a new encounter.
            </p>
          </div>
          <Link to="/new-visit" className="btn-link" style={{ fontSize: "0.95rem", padding: "0.65rem 1.25rem", boxShadow: "var(--shadow-md)" }}>
            ➕ Start New Consultation
          </Link>
        </div>
      </div>

      {/* Patients Section */}
      <div className="card">
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "0.75rem", marginBottom: "1.25rem" }}>
          <div>
            <h2 style={{ margin: 0 }}>Registered Patients ({filteredPatients.length})</h2>
            <span className="text-muted" style={{ fontSize: "0.8rem" }}>
              Electronic Health Records and Clinical Diagnostic Trajectories
            </span>
          </div>
          <div style={{ width: "100%", maxWidth: "300px" }}>
            <input
              type="search"
              placeholder="Search by patient name, MRN, phone..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ fontSize: "0.85rem", padding: "0.45rem 0.75rem" }}
            />
          </div>
        </div>

        {loading ? (
          <div style={{ padding: "2rem", textAlign: "center" }}>
            <div className="spinner spinner-primary" style={{ width: "28px", height: "28px", margin: "0 auto 0.5rem" }} />
            <p className="text-muted">Loading clinical records...</p>
          </div>
        ) : filteredPatients.length === 0 ? (
          <div style={{ padding: "2.5rem 1rem", textAlign: "center", background: "#f8fafc", borderRadius: "8px", border: "1px dashed #cbd5e1" }}>
            <p style={{ color: "var(--text-muted)", marginBottom: "0.75rem" }}>
              {searchTerm ? "No patient records match your search criteria." : "No patient consultations recorded in the clinic yet."}
            </p>
            <Link to="/new-visit" className="btn-primary" style={{ padding: "0.45rem 0.9rem", fontSize: "0.82rem" }}>
              Record First Consultation
            </Link>
          </div>
        ) : (
          <div style={{ display: "grid", gap: "0.85rem" }}>
            {filteredPatients.map((pt) => (
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
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-sm)",
        padding: "1rem",
        background: "#ffffff",
        boxShadow: "0 1px 2px rgba(0, 0, 0, 0.03)",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              background: "#e0f2fe",
              color: "#0369a1",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: "700",
              fontSize: "0.85rem",
            }}
          >
            {patient.full_name ? patient.full_name.charAt(0).toUpperCase() : "P"}
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-main)" }}>
              {patient.full_name}
            </h3>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              MRN: {patient.mrn || "N/A"} • Sex: {patient.sex} • DOB: {patient.date_of_birth || "N/A"}
            </span>
          </div>
        </div>

        <span className="badge badge-neutral">
          {visits.length} {visits.length === 1 ? "Encounter" : "Encounters"}
        </span>
      </div>

      <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.5rem", marginTop: "0.25rem" }}>
        {loadingVisits ? (
          <p className="text-muted" style={{ fontSize: "0.78rem" }}>Loading encounter history...</p>
        ) : visits.length === 0 ? (
          <p className="text-muted" style={{ fontSize: "0.78rem" }}>No visit encounters recorded for this patient.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.45rem" }}>
            {visits.map((v) => (
              <Link
                key={v.id}
                to={`/visits/${v.id}/results`}
                className="btn-secondary"
                style={{
                  fontSize: "0.75rem",
                  padding: "0.25rem 0.6rem",
                  borderRadius: "4px",
                  borderColor: "#bae6fd",
                  background: "#f0f9ff",
                  color: "#0369a1",
                }}
              >
                🔬 AI Differential ({new Date(v.occurred_at || Date.now()).toLocaleDateString()})
                {v.chief_complaint && (
                  <span style={{ opacity: 0.8, maxWidth: "160px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    — {v.chief_complaint}
                  </span>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
