import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import LabResultsSection from "../components/LabResultsSection.jsx";

export default function ResultsPage() {
  const { visitId } = useParams();

  const [visit, setVisit] = useState(null);
  const [patient, setPatient] = useState(null);
  const [vocabulary, setVocabulary] = useState([]);
  const [reasonData, setReasonData] = useState(null);
  const [existingDecision, setExistingDecision] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Feedback form state
  const [selectedDisease, setSelectedDisease] = useState("");
  const [customDisease, setCustomDisease] = useState("");
  const [decisionType, setDecisionType] = useState("accepted");
  const [doctorNotes, setDoctorNotes] = useState("");
  const [savingDecision, setSavingDecision] = useState(false);
  const [decisionSuccess, setDecisionSuccess] = useState("");

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError("");
      try {
        const vDetail = await api.get(`/visits/${visitId}`);
        setVisit(vDetail);

        try {
          const pDetail = await api.get(`/patients/${vDetail.patient_id}`);
          setPatient(pDetail);
        } catch {
          // ignore if patient detail fetch fails
        }

        try {
          const vocab = await api.get("/symptom-vocabulary");
          setVocabulary(vocab);
        } catch {
          // ignore
        }

        // Fetch AI Differential & Reasoning
        const rData = await api.post("/reason", {
          visit_id: visitId,
          include_classifier: true,
        });
        setReasonData(rData);

        // Pre-select top differential if available
        if (rData.differentials && rData.differentials.length > 0) {
          setSelectedDisease(rData.differentials[0].condition);
        }

        // Fetch existing doctor decision if any
        try {
          const dec = await api.get(`/visits/${visitId}/diagnosis`);
          if (dec) {
            setExistingDecision(dec);
            setDecisionType(dec.doctor_decision || "accepted");
            if (dec.edited_label) {
              setCustomDisease(dec.edited_label);
              setSelectedDisease("custom");
            } else {
              setSelectedDisease(dec.disease_label);
            }
            if (dec.reasoning) setDoctorNotes(dec.reasoning);
          }
        } catch {
          // ignore if no prior decision
        }
      } catch (err) {
        setError(`Failed to load AI evaluation: ${err.readableMessage || err.message}`);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [visitId]);

  async function handleSaveDecision(e) {
    e.preventDefault();
    setDecisionSuccess("");
    setError("");

    const targetLabel =
      selectedDisease === "custom" ? customDisease.trim() : selectedDisease;

    if (!targetLabel) {
      setError("Please select or specify a diagnosis label.");
      return;
    }

    setSavingDecision(true);
    try {
      const payload = {
        doctor_decision: decisionType,
        disease_label: targetLabel,
        edited_label: selectedDisease === "custom" ? customDisease.trim() : null,
        reasoning: doctorNotes.trim() || null,
        source: "llm",
      };

      const updated = await api.post(`/visits/${visitId}/diagnosis`, payload);
      setExistingDecision(updated);
      setDecisionSuccess("Doctor diagnosis decision recorded successfully!");
    } catch (err) {
      setError(`Failed to record decision: ${err.readableMessage || err.message}`);
    } finally {
      setSavingDecision(false);
    }
  }

  async function handleLabUpdated() {
    try {
      const rData = await api.post("/reason", {
        visit_id: visitId,
        include_classifier: true,
        force_refresh: true,
      });
      setReasonData(rData);
    } catch {
      // ignore silently
    }
  }

  const getHpoMeta = (name) => {
    const found = vocabulary.find((v) => v.id === name || v.id === name?.replace(/\s+/g, "_").toLowerCase());
    return found || { display_name: name?.replace(/_/g, " "), hpo_id: null };
  };

  const presentSymptoms = visit?.symptoms?.filter((s) => s.status === "present") || [];
  const absentSymptoms = visit?.symptoms?.filter((s) => s.status === "absent") || [];

  if (loading) {
    return (
      <div className="container" style={{ padding: "4rem 1rem", textAlign: "center" }}>
        <div className="card" style={{ maxWidth: "500px", margin: "0 auto", padding: "3rem 2rem" }}>
          <div className="spinner spinner-primary" style={{ width: "36px", height: "36px", margin: "0 auto 1rem" }} />
          <h2>Analyzing Patient Encounter...</h2>
          <p className="text-muted">
            Running 773-disease classifier and AI differential diagnostic reasoner.
          </p>
        </div>
      </div>
    );
  }

  if (error && !reasonData) {
    return (
      <div className="container">
        <div className="card">
          <h2 style={{ color: "var(--danger-solid)" }}>Diagnostic Evaluation Error</h2>
          <p style={{ margin: "0.5rem 0 1rem 0" }}>{error}</p>
          <Link className="btn-secondary" to="/">
            ← Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Header Navigation */}
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "1.25rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Link to="/" style={{ textDecoration: "none", color: "var(--primary)", fontWeight: "600", fontSize: "0.85rem" }}>
              ← Encounters Dashboard
            </Link>
          </div>
          <h1 style={{ marginTop: "0.25rem" }}>Clinical Diagnostic Report</h1>
          <p className="text-muted">
            Patient: <strong>{patient?.full_name || "Patient"}</strong> (MRN: {patient?.mrn || "N/A"}) • Encounter Date:{" "}
            {new Date(visit?.occurred_at || Date.now()).toLocaleDateString()}
          </p>
        </div>

        <Link to="/new-visit" className="btn-secondary" style={{ fontSize: "0.85rem" }}>
          ➕ New Consultation
        </Link>
      </div>

      {/* Case Overview & Clinical Evidences */}
      <div className="card">
        <div className="flex-between" style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.75rem", marginBottom: "1rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Clinical Evidence & Antecedents</h2>
          <span className="badge badge-primary">
            DDXPlus & HPO Ontology Mapped
          </span>
        </div>

        <div className="grid-2" style={{ gap: "1rem", marginBottom: "1rem" }}>
          {/* Antecedents Column */}
          <div style={{ background: "var(--bg-subtle)", padding: "1rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
            <h3 style={{ color: "var(--primary-text)", margin: "0 0 0.5rem 0", fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              1. Antecedents & Medical History
            </h3>
            <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.4rem" }}>
              <div>
                <strong>Demographics:</strong> {patient?.sex || "Unknown"}
                {patient?.date_of_birth ? `, DOB: ${patient.date_of_birth}` : ""}
                {patient?.weight_kg ? ` | ${patient.weight_kg} kg` : ""}
                {patient?.height_cm ? ` | ${patient.height_cm} cm` : ""}
              </div>
              {patient?.history && patient.history.length > 0 && (
                <div>
                  <strong>Medical History:</strong> {patient.history.map((h) => h.name).join(", ")}
                </div>
              )}
              {patient?.medications && patient.medications.length > 0 && (
                <div>
                  <strong>Active Medications:</strong> {patient.medications.map((m) => `${m.name}${m.dose ? ` (${m.dose})` : ""}`).join(", ")}
                </div>
              )}
              {patient?.allergies && patient.allergies.length > 0 && (
                <div style={{ color: "var(--danger-solid)" }}>
                  <strong>Allergies:</strong> {patient.allergies.map((a) => `${a.allergen}${a.reaction ? ` (${a.reaction})` : ""}`).join(", ")}
                </div>
              )}
              {visit?.social_history && (
                <div style={{ color: "var(--text-muted)" }}>
                  <strong>Social:</strong> Smoking: {visit.social_history.smoking_status || "unknown"}
                  {visit.social_history.diet ? ` | Diet: ${visit.social_history.diet}` : ""}
                </div>
              )}
            </div>
          </div>

          {/* Active Evidences Column */}
          <div style={{ background: "var(--bg-subtle)", padding: "1rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
            <h3 style={{ color: "var(--primary-text)", margin: "0 0 0.5rem 0", fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              2. Active Clinical Evidences & Vitals
            </h3>
            <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.4rem" }}>
              <div>
                <strong>Chief Complaint:</strong> {visit?.chief_complaint || "None specified"}
                {visit?.severity_score ? ` (Severity: ${visit.severity_score}/10)` : ""}
                {visit?.complaint_duration ? ` • Duration: ${visit.complaint_duration}` : ""}
              </div>
              {visit?.vitals && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.25rem" }}>
                  {visit.vitals.temperature_c && (
                    <span className={`badge ${visit.vitals.temperature_c >= 38 ? "badge-danger" : "badge-neutral"}`}>
                      Temp: {visit.vitals.temperature_c}°C
                    </span>
                  )}
                  {visit.vitals.systolic_bp && (
                    <span className={`badge ${visit.vitals.systolic_bp >= 140 || visit.vitals.diastolic_bp >= 90 ? "badge-danger" : "badge-neutral"}`}>
                      BP: {visit.vitals.systolic_bp}/{visit.vitals.diastolic_bp} mmHg
                    </span>
                  )}
                  {visit.vitals.heart_rate && (
                    <span className={`badge ${visit.vitals.heart_rate >= 100 || visit.vitals.heart_rate < 60 ? "badge-warning" : "badge-neutral"}`}>
                      HR: {visit.vitals.heart_rate} bpm
                    </span>
                  )}
                  {visit.vitals.spo2 && (
                    <span className={`badge ${visit.vitals.spo2 <= 94 ? "badge-danger" : "badge-neutral"}`}>
                      SpO2: {visit.vitals.spo2}%
                    </span>
                  )}
                </div>
              )}
              {presentSymptoms.length > 0 && (
                <div style={{ marginTop: "0.35rem" }}>
                  <span style={{ fontSize: "0.78rem", fontWeight: "700", color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}>
                    Presenting Phenotypes (HPO):
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                    {presentSymptoms.map((s) => {
                      const meta = getHpoMeta(s.name);
                      return (
                        <span key={s.name} className="badge badge-primary">
                          <span>{meta.display_name}</span>
                          {meta.hpo_id && <span style={{ opacity: 0.75, fontFamily: "monospace", fontSize: "0.7rem" }}>({meta.hpo_id})</span>}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
              {absentSymptoms.length > 0 && (
                <div style={{ marginTop: "0.25rem", color: "var(--text-muted)", fontSize: "0.78rem" }}>
                  <strong>Pertinent Negatives (Ruled-out):</strong> {absentSymptoms.map((s) => getHpoMeta(s.name).display_name).join(", ")}
                </div>
              )}
            </div>
          </div>
        </div>

        {reasonData?.summary && (
          <div
            style={{
              background: "#f0f9ff",
              borderLeft: "4px solid var(--primary)",
              padding: "0.85rem 1rem",
              borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
              marginTop: "0.5rem",
            }}
          >
            <strong style={{ color: "var(--primary-text)", fontSize: "0.85rem", textTransform: "uppercase" }}>
              💡 Clinical Case Synthesis:
            </strong>
            <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.9rem", color: "var(--text-main)" }}>
              {reasonData.summary}
            </p>
          </div>
        )}
      </div>

      {/* Red Flags Alert Box */}
      {reasonData?.red_flags && reasonData.red_flags.length > 0 && (
        <div className="card" style={{ background: "var(--danger-bg)", borderColor: "var(--danger-border)" }}>
          <h3 style={{ color: "var(--danger-text)", margin: "0 0 0.5rem 0", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span>⚠️</span> Critical Clinical Red Flags / Urgent Considerations
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "var(--danger-text)", fontSize: "0.9rem" }}>
            {reasonData.red_flags.map((flag, idx) => (
              <li key={idx} style={{ marginBottom: "0.25rem" }}>
                <strong>{flag}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Lab Results & Attachment Upload Section */}
      <LabResultsSection visitId={visitId} onLabUpdated={handleLabUpdated} />

      {/* AI Differentials List */}
      <div className="card">
        <div className="flex-between" style={{ marginBottom: "1rem" }}>
          <div>
            <h2 style={{ margin: 0 }}>AI Differential Diagnoses</h2>
            <span className="text-muted" style={{ fontSize: "0.8rem" }}>
              Ranked etiologies generated by Clinical Chain-of-Thought reasoning
            </span>
          </div>
        </div>

        <div style={{ display: "grid", gap: "0.85rem" }}>
          {reasonData?.differentials?.map((diff, index) => {
            const likelihood = (diff.likelihood || "moderate").toLowerCase();
            const badgeType =
              likelihood === "high"
                ? "badge-success"
                : likelihood === "moderate"
                ? "badge-primary"
                : "badge-neutral";

            return (
              <div
                key={index}
                style={{
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  padding: "1rem",
                  background: index === 0 ? "linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%)" : "#ffffff",
                  boxShadow: "0 1px 2px rgba(0, 0, 0, 0.03)",
                }}
              >
                <div className="flex-between">
                  <h3 style={{ margin: 0, fontSize: "1.05rem", color: "var(--text-main)" }}>
                    #{diff.rank || index + 1} {diff.condition}
                  </h3>
                  <span className={`badge ${badgeType}`}>
                    {diff.likelihood || "Likely"} Likelihood
                  </span>
                </div>
                {diff.notes && (
                  <p style={{ margin: "0.5rem 0", color: "var(--text-body)", fontSize: "0.9rem", lineHeight: "1.5" }}>
                    {diff.notes}
                  </p>
                )}
                {diff.supporting_findings && diff.supporting_findings.length > 0 && (
                  <div style={{ marginTop: "0.35rem", fontSize: "0.82rem" }}>
                    <strong style={{ color: "var(--primary-text)" }}>Supporting Findings: </strong>
                    <span style={{ color: "var(--text-body)" }}>{diff.supporting_findings.join(", ")}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Multi-Disease ML Classifier Baseline */}
      {reasonData?.classifier_predictions && reasonData.classifier_predictions.length > 0 && (
        <div className="card">
          <h2>Statistical ML Multi-Disease Cross-Check</h2>
          <p className="text-muted" style={{ marginBottom: "0.75rem" }}>
            Trained Bernoulli Naive Bayes baseline predictions across 773 ICD disease categories.
          </p>
          <div className="table-responsive">
            <table className="entry-table">
              <thead>
                <tr>
                  <th style={{ width: "80px" }}>Rank</th>
                  <th>Predicted Pathology</th>
                  <th style={{ width: "160px" }}>Confidence Score</th>
                </tr>
              </thead>
              <tbody>
                {reasonData.classifier_predictions.map((pred, i) => {
                  const prob = pred.confidence !== undefined ? pred.confidence : (pred.probability || 0);
                  return (
                    <tr key={i}>
                      <td>
                        <span className="badge badge-neutral">#{pred.rank}</span>
                      </td>
                      <td style={{ fontWeight: "600", color: "var(--text-main)" }}>
                        {pred.display_name || pred.disease}
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <div style={{ flex: 1, height: "6px", background: "#e2e8f0", borderRadius: "9999px", overflow: "hidden" }}>
                            <div style={{ width: `${Math.min(prob * 100, 100)}%`, height: "100%", background: "var(--primary)" }} />
                          </div>
                          <span style={{ fontSize: "0.78rem", fontWeight: "700" }}>{(prob * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Suggested Workup & Questions */}
      <div className="grid-2" style={{ marginBottom: "1.25rem" }}>
        {reasonData?.suggested_next_steps && reasonData.suggested_next_steps.length > 0 && (
          <div className="card" style={{ marginBottom: 0 }}>
            <h3>Recommended Diagnostic Workup</h3>
            <ul style={{ paddingLeft: "1.2rem", margin: "0.5rem 0 0 0", fontSize: "0.88rem", lineHeight: "1.6" }}>
              {reasonData.suggested_next_steps.map((step, idx) => (
                <li key={idx}><strong>{step}</strong></li>
              ))}
            </ul>
          </div>
        )}

        {reasonData?.questions_for_patient && reasonData.questions_for_patient.length > 0 && (
          <div className="card" style={{ marginBottom: 0 }}>
            <h3>Suggested Follow-Up Questions</h3>
            <ul style={{ paddingLeft: "1.2rem", margin: "0.5rem 0 0 0", fontSize: "0.88rem", lineHeight: "1.6" }}>
              {reasonData.questions_for_patient.map((q, idx) => (
                <li key={idx}>{q}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Doctor Final Decision / Sign-off */}
      <div className="card" style={{ border: "2px solid #bae6fd", background: "linear-gradient(145deg, #ffffff 0%, #f0f9ff 100%)" }}>
        <h2>Attending Doctor Final Diagnosis & Sign-off</h2>
        <p className="text-muted" style={{ marginBottom: "1rem" }}>
          Select or record the final clinical diagnosis to close this encounter and train our reinforcement feedback loop.
        </p>

        {decisionSuccess && <div className="alert-success">{decisionSuccess}</div>}

        <form onSubmit={handleSaveDecision}>
          <div className="grid-2" style={{ marginBottom: "0.85rem" }}>
            <div className="field">
              <label htmlFor="decision-disease">Diagnosis Label</label>
              <select
                id="decision-disease"
                value={selectedDisease}
                onChange={(e) => setSelectedDisease(e.target.value)}
              >
                {reasonData?.differentials?.map((d, i) => (
                  <option key={i} value={d.condition}>
                    #{d.rank || i + 1}: {d.condition} ({d.likelihood || "Moderate"} likelihood)
                  </option>
                ))}
                <option value="custom">-- Custom / Other Pathology --</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="decision-action">Clinical Decision</label>
              <select
                id="decision-action"
                value={decisionType}
                onChange={(e) => setDecisionType(e.target.value)}
              >
                <option value="accepted">Accepted (Concur with AI differential)</option>
                <option value="modified">Modified (Alternative primary etiology)</option>
                <option value="rejected">Rejected (Clinical findings discordant)</option>
              </select>
            </div>
          </div>

          {selectedDisease === "custom" && (
            <div className="field" style={{ marginBottom: "0.85rem" }}>
              <label htmlFor="custom-disease">Specify Diagnosis Name</label>
              <input
                id="custom-disease"
                type="text"
                placeholder="e.g. Acute pericarditis, Tension headache..."
                value={customDisease}
                onChange={(e) => setCustomDisease(e.target.value)}
                required
              />
            </div>
          )}

          <div className="field" style={{ marginBottom: "1rem" }}>
            <label htmlFor="doctor-notes">Doctor Clinical Notes & Rationale</label>
            <textarea
              id="doctor-notes"
              rows={3}
              placeholder="Record any clinical justification, atypical presentation notes, or differential considerations..."
              value={doctorNotes}
              onChange={(e) => setDoctorNotes(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span className="text-muted" style={{ fontSize: "0.78rem" }}>
              {existingDecision ? `Last recorded by Dr. on ${new Date(existingDecision.created_at || Date.now()).toLocaleDateString()}` : "Encounter not yet finalized"}
            </span>
            <button
              type="submit"
              disabled={savingDecision}
              className="btn-primary"
              style={{ padding: "0.6rem 1.4rem" }}
            >
              {savingDecision ? (
                <>
                  <span className="spinner" />
                  <span>Recording Decision...</span>
                </>
              ) : (
                "✓ Finalize & Save Diagnosis Decision"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
