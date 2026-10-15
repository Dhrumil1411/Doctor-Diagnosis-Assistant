import React, { useState } from "react";
import { api } from "../api/client.js";

const SAMPLE_NOTES = [
  {
    label: "🫀 Acute Coronary Syndrome",
    badge: "Cardiovascular Emergency",
    text: `58-year-old male presents with sudden-onset crushing substernal chest pain that began 2 hours ago while mowing the lawn. Pain is 8/10, radiates to the left arm and jaw, and is associated with shortness of breath, diaphoresis (profuse sweating), and mild nausea. He denies vomiting, cough, or fever. 

Past Medical History: Essential hypertension (since 2018), Type 2 Diabetes Mellitus (since 2020), Hyperlipidemia.
Current Medications: Lisinopril 20mg once daily, Metformin 1000mg twice daily, Atorvastatin 40mg at bedtime.
Allergies: Penicillin (causes severe hives and anaphylaxis).
Social: Current smoker, 25 pack-years. Denies alcohol or illicit drugs.

Vitals: BP 155/95 mmHg, HR 102 bpm, RR 22/min, SpO2 95% on room air, Temp 37.1 C.
Physical Exam: Patient appears anxious, diaphoretic, no peripheral edema, lungs clear to auscultation bilaterally.`,
  },
  {
    label: "🫁 Community-Acquired Pneumonia",
    badge: "Respiratory Infection",
    text: `42-year-old female presenting with a 4-day history of worsening productive cough with purulent yellow sputum, high fever (measured 39.2 C at home), shaking chills, and right-sided pleuritic chest pain that worsens on deep inspiration. She also notes fatigue and shortness of breath with mild exertion. Denies nausea, vomiting, or hemoptysis.

PMH: Mild intermittent asthma (diagnosed 2015).
Medications: Albuterol MDI 2 puffs as needed.
Allergies: Sulfa drugs (skin rash).
Social: Non-smoker, works as an elementary school teacher.

Vitals: Temp 38.9 C, BP 118/76 mmHg, HR 108 bpm, RR 24/min, SpO2 93% on ambient air.
Physical Exam: Moderate respiratory distress, crackles and bronchial breath sounds over the right lower lung zone.`,
  },
  {
    label: "🩺 Acute Appendicitis",
    badge: "Acute Surgical Abdomen",
    text: `23-year-old male with 18 hours of severe abdominal pain. The pain initially started as dull and periumbilical, but has migrated to the right lower quadrant over the past 6 hours and is now constant and sharp (severity 7/10). Associated with anorexia, nausea, and 2 episodes of non-bilious vomiting. Denies diarrhea, dysuria, or hematochezia.

PMH: None. No prior surgeries.
Medications: None.
Allergies: No known drug allergies (NKDA).
Social: College student, occasional social alcohol on weekends.

Vitals: Temp 38.1 C, BP 122/78 mmHg, HR 96 bpm, RR 18/min, SpO2 99%.
Physical Exam: Significant tenderness at McBurney's point with guarding and positive rebound tenderness. Rovsing sign positive.`,
  },
  {
    label: "💬 Doctor-Patient Dialogue",
    badge: "Consultation Transcript",
    text: `Doctor: Good morning, what brings you to the clinic today?
Patient: Hi doctor. For the past 3 days, I've had this debilitating throbbing headache on the right side of my head. It feels like an 8 out of 10.
Doctor: Are you having any other symptoms with the headache?
Patient: Yes, bright lights and loud sounds make it so much worse. I've been feeling very nauseous and threw up once yesterday. My vision is also slightly blurry.
Doctor: Any fever, neck stiffness, or weakness in your arms or legs?
Patient: No fever, no neck stiffness, and no numbness or weakness.
Doctor: Any medical conditions or regular medications?
Patient: I have migraines in the family, and I take oral contraceptives. I'm allergic to Ibuprofen—it gives me facial swelling.
Vitals recorded by triage nurse: BP 120/80, Pulse 78, Temp 36.8 C, Oxygen saturation 99%.`,
  },
];

export default function ClinicalNoteExtractor({ onExtractAndFill }) {
  const [isOpen, setIsOpen] = useState(true);
  const [rawNote, setRawNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [extractedData, setExtractedData] = useState(null);

  const handleExtract = async () => {
    if (!rawNote.trim() || rawNote.trim().length < 5) {
      setError("Please paste or type a clinical note of at least 5 characters.");
      return;
    }
    setError("");
    setLoading(true);
    setExtractedData(null);
    try {
      const data = await api.post("/clinical-notes/extract", { raw_note: rawNote });
      setExtractedData(data);
    } catch (err) {
      setError(err.readableMessage || err.message || "Failed to extract clinical entities from note.");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (extractedData && onExtractAndFill) {
      onExtractAndFill(extractedData);
      setExtractedData(null);
    }
  };

  return (
    <div className="extractor-card">
      <div className="extractor-header">
        <div className="extractor-title-group">
          <div className="extractor-icon-box">📋</div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "1rem", fontWeight: "700", color: "var(--text-main)" }}>
                Smart Clinical Note & Transcript Extractor
              </span>
              <span className="badge badge-primary">SFT / HPO Powered</span>
            </div>
            <p className="text-muted" style={{ fontSize: "0.8rem", marginTop: "2px" }}>
              Paste unformatted doctor notes, dictations, or transcripts to automatically extract symptoms, vitals, history, and HPO codes.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="btn-secondary"
          style={{ padding: "0.35rem 0.75rem", fontSize: "0.78rem" }}
        >
          {isOpen ? "Hide Extractor ▲" : "Show Extractor ▼"}
        </button>
      </div>

      {isOpen && (
        <div style={{ marginTop: "1rem", paddingTop: "0.85rem", borderTop: "1px solid #e2e8f0" }}>
          {/* Preset Buttons */}
          <div style={{ marginBottom: "0.65rem" }}>
            <span style={{ fontSize: "0.78rem", fontWeight: "600", color: "var(--text-muted)", display: "block", marginBottom: "0.35rem" }}>
              ⚡ Quick Load Clinical Case:
            </span>
            <div className="preset-pills">
              {SAMPLE_NOTES.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setRawNote(sample.text);
                    setError("");
                    setExtractedData(null);
                  }}
                  className="preset-btn"
                >
                  <strong>{sample.label}</strong>
                  <span className="preset-tag">{sample.badge}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Text Area */}
          <div style={{ position: "relative", marginBottom: "0.75rem" }}>
            <textarea
              className="extractor-textarea"
              rows={6}
              value={rawNote}
              onChange={(e) => setRawNote(e.target.value)}
              placeholder="Paste doctor's clinical examination note, patient conversation dialogue, or SOAP summary here..."
            />
            {rawNote && (
              <button
                type="button"
                onClick={() => setRawNote("")}
                style={{
                  position: "absolute",
                  right: "8px",
                  bottom: "10px",
                  background: "transparent",
                  border: "none",
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "2px 6px",
                  borderRadius: "4px",
                }}
              >
                ✕ Clear
              </button>
            )}
          </div>

          {error && <div className="error">{error}</div>}

          {/* Action Row */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              {rawNote ? `${rawNote.length} characters` : "Tip: You can edit or customize the text before extracting"}
            </span>
            <button
              type="button"
              disabled={loading || !rawNote.trim()}
              onClick={handleExtract}
              className="btn-primary"
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  <span>Extracting Clinical Entities...</span>
                </>
              ) : (
                <>
                  <span>⚡ Extract & Parse Case</span>
                </>
              )}
            </button>
          </div>

          {/* Extracted Preview */}
          {extractedData && (
            <div className="extractor-preview">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ color: "var(--success-solid)", fontSize: "1.1rem" }}>✓</span>
                  <strong style={{ color: "var(--text-main)", fontSize: "0.95rem" }}>
                    Case Entities Extracted Successfully
                  </strong>
                </div>
                <button
                  type="button"
                  onClick={handleApply}
                  className="btn-success"
                  style={{ padding: "0.45rem 1rem", fontSize: "0.85rem" }}
                >
                  🚀 Populate Form Now
                </button>
              </div>

              {extractedData.summary && (
                <p style={{ fontSize: "0.85rem", color: "var(--text-body)", fontStyle: "italic", margin: "0.4rem 0" }}>
                  "{extractedData.summary}"
                </p>
              )}

              <div className="preview-grid">
                <div className="preview-stat">
                  <span className="preview-stat-label">Demographics</span>
                  <span className="preview-stat-val">
                    {extractedData.demographics?.sex || "unknown"},{" "}
                    {extractedData.demographics?.age_years ? `${extractedData.demographics.age_years} yo` : "Age N/A"}
                  </span>
                </div>
                <div className="preview-stat">
                  <span className="preview-stat-label">Symptoms Mapped</span>
                  <span className="preview-stat-val" style={{ color: "var(--primary)" }}>
                    {extractedData.symptoms_present?.length || 0} Standardized
                  </span>
                </div>
                <div className="preview-stat">
                  <span className="preview-stat-label">Vitals</span>
                  <span className="preview-stat-val" style={{ color: "var(--success-solid)" }}>
                    {extractedData.vitals?.systolic_bp ? `BP ${extractedData.vitals.systolic_bp}/${extractedData.vitals.diastolic_bp}` : "Parsed"}
                  </span>
                </div>
                <div className="preview-stat">
                  <span className="preview-stat-label">Antecedents</span>
                  <span className="preview-stat-val">
                    {(extractedData.medical_history?.length || 0) + (extractedData.medications?.length || 0)} Items
                  </span>
                </div>
              </div>

              {extractedData.symptoms_present?.length > 0 && (
                <div style={{ marginTop: "0.75rem" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)", display: "block", marginBottom: "0.35rem" }}>
                    Human Phenotype Ontology (HPO) Matches:
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                    {extractedData.symptoms_present.map((s, idx) => (
                      <span key={idx} className="badge badge-primary">
                        <span>{s.name}</span>
                        {s.hpo_id && <span style={{ opacity: 0.75, fontFamily: "monospace", fontSize: "0.7rem" }}>({s.hpo_id})</span>}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
