import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import LabResultsSection from "../components/LabResultsSection.jsx";

export default function ResultsPage() {
  const { visitId } = useParams();

  const [visit, setVisit] = useState(null);
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
        setError(`Failed to load AI evaluation: ${err.message}`);
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
      setDecisionSuccess("Doctor decision recorded successfully!");
    } catch (err) {
      setError(`Failed to record decision: ${err.message}`);
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

  if (loading) {
    return (
      <div className="container">
        <div className="card center" style={{ padding: "3rem 1rem" }}>
          <h2>Analyzing Clinical Case...</h2>
          <p className="muted">
            Running machine learning classifier & AI differential reasoning engine.
          </p>
        </div>
      </div>
    );
  }

  if (error && !reasonData) {
    return (
      <div className="container">
        <div className="card">
          <h2 style={{ color: "var(--error-text)" }}>Evaluation Error</h2>
          <p>{error}</p>
          <Link className="btn-link" to="/" style={{ marginTop: "1rem" }}>
            ← Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Header Navigation */}
      <div style={{ marginBottom: "1.25rem" }}>
        <Link to="/" style={{ textDecoration: "none", color: "#60a5fa", fontWeight: "600", fontSize: "0.9rem" }}>
          ← Back to Dashboard
        </Link>
        <h1 style={{ marginTop: "0.5rem" }}>Clinical Evaluation & AI Reasoning</h1>
        <p className="muted">
          Visit ID: {visitId.slice(0, 8)}... | Occurred:{" "}
          {new Date(visit?.occurred_at || Date.now()).toLocaleString()}
        </p>
      </div>

      {/* Case Summary Header Card */}
      <div className="card">
        <h3>Patient Case Overview</h3>
        <p>
          <strong>Chief Complaint:</strong>{" "}
          {visit?.chief_complaint || "Not specified"} (Severity:{" "}
          {visit?.severity_score || "N/A"}/10, Duration:{" "}
          {visit?.complaint_duration || "N/A"})
        </p>
        {reasonData?.summary && (
          <div
            style={{
              background: "var(--accent-light)",
              borderLeft: "3px solid var(--accent-primary)",
              padding: "0.85rem",
              borderRadius: "6px",
              marginTop: "0.75rem",
            }}
          >
            <strong style={{ color: "#93c5fd" }}>AI Clinical Synthesis:</strong>
            <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.92rem" }}>{reasonData.summary}</p>
          </div>
        )}
      </div>

      {/* Red Flags Alert Box */}
      {reasonData?.red_flags && reasonData.red_flags.length > 0 && (
        <div className="card warning-card">
          <h3 style={{ color: "#f87171", margin: "0 0 0.5rem 0" }}>
            ⚠️ Clinical Red Flags / Warning Signs
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "#fca5a5", fontSize: "0.92rem" }}>
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
        <h2>AI Differential Diagnoses</h2>
        <div style={{ display: "grid", gap: "0.85rem", marginTop: "0.85rem" }}>
          {reasonData?.differentials?.map((diff, index) => {
            const badgeClass =
              diff.confidence_band === "high"
                ? "badge-high"
                : diff.confidence_band === "moderate"
                ? "badge-moderate"
                : "badge-low";
            return (
              <div
                key={index}
                style={{
                  border: "1px solid var(--border-color)",
                  borderRadius: "8px",
                  padding: "1rem",
                  background: "rgba(15, 23, 42, 0.5)",
                }}
              >
                <div className="flex-between">
                  <h4 style={{ margin: 0, fontSize: "1.05rem" }}>
                    #{index + 1} {diff.condition}
                  </h4>
                  <span className={`badge ${badgeClass}`}>
                    {diff.confidence_band || "Likely"} confidence
                  </span>
                </div>
                <p style={{ margin: "0.5rem 0", color: "#cbd5e1", fontSize: "0.92rem" }}>
                  {diff.justification}
                </p>
                {diff.suggested_tests && diff.suggested_tests.length > 0 && (
                  <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--text-muted)" }}>
                    <strong>Recommended Tests:</strong> {diff.suggested_tests.join(", ")}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ML Classifier Cross-Check */}
      {reasonData?.classifier_predictions &&
        reasonData.classifier_predictions.length > 0 && (
          <div className="card">
            <h2>Multi-Disease ML Classifier Baseline</h2>
            <p className="muted">
              Pattern matching predictions generated by trained multi-disease classifier model.
            </p>
            <div className="table-responsive">
              <table className="entry-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Disease Category</th>
                    <th>Probability</th>
                  </tr>
                </thead>
                <tbody>
                  {reasonData.classifier_predictions.map((pred, i) => (
                    <tr key={i}>
                      <td>#{pred.rank}</td>
                      <td style={{ fontWeight: "bold" }}>{pred.disease}</td>
                      <td>{(pred.probability * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      {/* Suggested Next Steps & Patient Questions */}
      <div className="grid-2" style={{ marginBottom: "1.25rem" }}>
        {reasonData?.suggested_next_steps && (
          <div className="card" style={{ marginBottom: 0 }}>
            <h3>Suggested Next Steps</h3>
            <ul style={{ paddingLeft: "1.2rem", margin: 0, fontSize: "0.9rem" }}>
              {reasonData.suggested_next_steps.map((step, idx) => (
                <li key={idx} style={{ marginBottom: "0.4rem" }}>
                  {step}
                </li>
              ))}
            </ul>
          </div>
        )}
        {reasonData?.questions_for_patient && (
          <div className="card" style={{ marginBottom: 0 }}>
            <h3>Questions for Patient</h3>
            <ul style={{ paddingLeft: "1.2rem", margin: 0, fontSize: "0.9rem" }}>
              {reasonData.questions_for_patient.map((q, idx) => (
                <li key={idx} style={{ marginBottom: "0.4rem" }}>
                  {q}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Doctor Feedback & Decision Recording Form */}
      <div className="card" style={{ borderColor: "var(--accent-primary)" }}>
        <h2>Doctor Decision & Feedback Loop</h2>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          Review the AI differential diagnosis above and record your clinical confirmation.
        </p>

        {existingDecision && (
          <div className="success" style={{ marginBottom: "1rem" }}>
            <strong>Saved Doctor Decision: </strong>
            Confirmed <strong>{existingDecision.disease_label}</strong> (Action:{" "}
            <span style={{ textTransform: "uppercase", fontWeight: "bold" }}>
              {existingDecision.doctor_decision}
            </span>
            )
          </div>
        )}

        <form onSubmit={handleSaveDecision}>
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="disease-select">Select Final Diagnosis:</label>
            <select
              id="disease-select"
              value={selectedDisease}
              onChange={(e) => setSelectedDisease(e.target.value)}
            >
              {reasonData?.differentials?.map((diff, i) => (
                <option key={i} value={diff.condition}>
                  {diff.condition} ({diff.confidence_band || "likely"})
                </option>
              ))}
              <option value="custom">-- Other / Specify Custom Diagnosis --</option>
            </select>
          </div>

          {selectedDisease === "custom" && (
            <div style={{ marginBottom: "1rem" }}>
              <label htmlFor="custom-disease">Custom Diagnosis Label:</label>
              <input
                id="custom-disease"
                type="text"
                required
                placeholder="Type custom diagnosis..."
                value={customDisease}
                onChange={(e) => setCustomDisease(e.target.value)}
              />
            </div>
          )}

          <div style={{ marginBottom: "1.25rem" }}>
            <label>Doctor Decision Action:</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "0.4rem" }}>
              <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", margin: 0, cursor: "pointer" }}>
                <input
                  type="radio"
                  name="decision"
                  value="accepted"
                  style={{ width: "auto" }}
                  checked={decisionType === "accepted"}
                  onChange={() => setDecisionType("accepted")}
                />{" "}
                <span style={{ color: "#34d399", fontWeight: "bold" }}>
                  Accept Suggestion
                </span>
              </label>
              <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", margin: 0, cursor: "pointer" }}>
                <input
                  type="radio"
                  name="decision"
                  value="edited"
                  style={{ width: "auto" }}
                  checked={decisionType === "edited"}
                  onChange={() => setDecisionType("edited")}
                />{" "}
                <span style={{ color: "#fbbf24", fontWeight: "bold" }}>
                  Edit / Override
                </span>
              </label>
              <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", margin: 0, cursor: "pointer" }}>
                <input
                  type="radio"
                  name="decision"
                  value="rejected"
                  style={{ width: "auto" }}
                  checked={decisionType === "rejected"}
                  onChange={() => setDecisionType("rejected")}
                />{" "}
                <span style={{ color: "#f87171", fontWeight: "bold" }}>
                  Reject AI Suggestions
                </span>
              </label>
            </div>
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="doctor-notes">Attending Doctor Clinical Notes:</label>
            <textarea
              id="doctor-notes"
              rows={3}
              placeholder="Add optional notes or clinical rationale..."
              value={doctorNotes}
              onChange={(e) => setDoctorNotes(e.target.value)}
            />
          </div>

          {error && <div className="error" role="alert" style={{ marginBottom: "1rem" }}>{error}</div>}
          {decisionSuccess && <div className="success" role="status" style={{ marginBottom: "1rem" }}>{decisionSuccess}</div>}

          <button type="submit" disabled={savingDecision}>
            {savingDecision ? "Saving Decision..." : "Submit Doctor Decision"}
          </button>
        </form>
      </div>
    </div>
  );
}
