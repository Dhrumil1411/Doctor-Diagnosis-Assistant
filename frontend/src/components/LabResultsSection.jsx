import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function LabResultsSection({ visitId, onLabUpdated }) {
  const [labs, setLabs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Upload Form State
  const [category, setCategory] = useState("other");
  const [testName, setTestName] = useState("");
  const [resultSummary, setResultSummary] = useState("");
  const [performedAt, setPerformedAt] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);

  async function loadLabs() {
    if (!visitId) return;
    setLoading(true);
    try {
      const data = await api.get(`/visits/${visitId}/labs`);
      setLabs(data || []);
    } catch (err) {
      setError(`Failed to load lab results: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLabs();
  }, [visitId]);

  async function handleUpload(e) {
    e.preventDefault();
    if (!testName.trim()) {
      setError("Please provide a test name.");
      return;
    }

    setError("");
    setSuccess("");
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("category", category);
      formData.append("test_name", testName.trim());
      if (resultSummary.trim()) formData.append("result_summary", resultSummary.trim());
      if (performedAt) formData.append("performed_at", performedAt);
      if (selectedFile) formData.append("file", selectedFile);

      // Perform multipart upload via fetch client
      const token = localStorage.getItem("dda_token");
      const resp = await fetch(`/api/visits/${visitId}/labs`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(errJson.detail || "Upload failed");
      }

      setSuccess("Lab result uploaded successfully!");
      setTestName("");
      setResultSummary("");
      setPerformedAt("");
      setSelectedFile(null);
      
      // Reset file input element
      const fileInput = document.getElementById(`lab-file-input-${visitId}`);
      if (fileInput) fileInput.value = "";

      await loadLabs();
      if (onLabUpdated) onLabUpdated();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(labId) {
    if (!window.confirm("Are you sure you want to delete this lab result?")) return;
    setError("");
    setSuccess("");
    try {
      await api.delete(`/labs/${labId}`);
      setSuccess("Lab result deleted.");
      await loadLabs();
      if (onLabUpdated) onLabUpdated();
    } catch (err) {
      setError(`Failed to delete: ${err.message}`);
    }
  }

  return (
    <div className="card">
      <div className="flex-between" style={{ marginBottom: "0.75rem" }}>
        <div>
          <h3 style={{ margin: 0 }}>Investigations, Labs & Imaging Uploads</h3>
          <p className="muted" style={{ margin: "0.25rem 0 0 0", fontSize: "0.88rem" }}>
            Upload lab reports, bloodwork, X-rays, ECGs or CT scans associated with this visit.
          </p>
        </div>
        <span className="badge badge-high" style={{ background: "rgba(59, 130, 246, 0.2)", color: "#93c5fd" }}>
          {labs.length} File{labs.length === 1 ? "" : "s"}
        </span>
      </div>

      {/* Uploaded Lab Items List */}
      {loading ? (
        <p className="muted" style={{ fontSize: "0.9rem" }}>Loading lab records...</p>
      ) : labs.length === 0 ? (
        <p className="muted" style={{ fontSize: "0.9rem", fontStyle: "italic" }}>
          No lab tests or imaging files uploaded for this visit yet.
        </p>
      ) : (
        <div style={{ display: "grid", gap: "0.75rem", marginBottom: "1.25rem" }}>
          {labs.map((lab) => (
            <div
              key={lab.id}
              style={{
                border: "1px solid var(--border-color)",
                borderRadius: "6px",
                padding: "0.85rem",
                background: "rgba(15, 23, 42, 0.4)",
              }}
            >
              <div className="flex-between">
                <div>
                  <span
                    className="badge"
                    style={{
                      textTransform: "uppercase",
                      fontSize: "0.7rem",
                      marginRight: "0.5rem",
                      background: "rgba(147, 197, 253, 0.15)",
                      color: "#93c5fd",
                    }}
                  >
                    {lab.category}
                  </span>
                  <strong style={{ fontSize: "0.95rem" }}>{lab.test_name}</strong>
                  {lab.performed_at && (
                    <span className="muted" style={{ fontSize: "0.8rem", marginLeft: "0.5rem" }}>
                      ({new Date(lab.performed_at).toLocaleDateString()})
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(lab.id)}
                  style={{
                    background: "transparent",
                    color: "#f87171",
                    border: "1px solid rgba(248, 113, 113, 0.3)",
                    padding: "0.2rem 0.5rem",
                    fontSize: "0.75rem",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  Delete
                </button>
              </div>

              {lab.result_summary && (
                <p style={{ margin: "0.4rem 0 0 0", fontSize: "0.9rem", color: "#cbd5e1" }}>
                  {lab.result_summary}
                </p>
              )}

              {lab.file_url && (
                <div style={{ marginTop: "0.5rem" }}>
                  <a
                    href={lab.file_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.3rem",
                      color: "#60a5fa",
                      fontSize: "0.85rem",
                      fontWeight: "500",
                    }}
                  >
                    📄 View / Download Attached Report ({lab.file_path ? lab.file_path.split(".").pop().toUpperCase() : "FILE"})
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload New Lab Form */}
      <form onSubmit={handleUpload} style={{ borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
        <h4 style={{ margin: "0 0 0.75rem 0", fontSize: "0.95rem" }}>Add New Lab Result / Imaging Report</h4>

        <div className="grid-2">
          <div>
            <label htmlFor={`lab-category-${visitId}`}>Category:</label>
            <select
              id={`lab-category-${visitId}`}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="blood">Blood Test</option>
              <option value="imaging">Imaging (X-Ray, CT, MRI, Ultrasound)</option>
              <option value="ecg">ECG / Electrocardiogram</option>
              <option value="other">Other / Pathology</option>
            </select>
          </div>

          <div>
            <label htmlFor={`lab-test-name-${visitId}`}>Test / Exam Name *:</label>
            <input
              id={`lab-test-name-${visitId}`}
              type="text"
              required
              placeholder="e.g. CBC, Chest X-Ray, Lipid Profile"
              value={testName}
              onChange={(e) => setTestName(e.target.value)}
            />
          </div>
        </div>

        <div className="grid-2">
          <div>
            <label htmlFor={`lab-summary-${visitId}`}>Result Findings / Summary:</label>
            <input
              id={`lab-summary-${visitId}`}
              type="text"
              placeholder="e.g. Hb 13.2 g/dL, clear lung fields, normal sinus rhythm"
              value={resultSummary}
              onChange={(e) => setResultSummary(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor={`lab-date-${visitId}`}>Date Performed:</label>
            <input
              id={`lab-date-${visitId}`}
              type="date"
              value={performedAt}
              onChange={(e) => setPerformedAt(e.target.value)}
            />
          </div>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor={`lab-file-input-${visitId}`}>Attach Report File (PDF, Image, DICOM, TXT, DOC):</label>
          <input
            id={`lab-file-input-${visitId}`}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.csv,.doc,.docx,.dcm,.dicom"
            onChange={(e) => setSelectedFile(e.target.files[0] || null)}
            style={{ fontSize: "0.85rem" }}
          />
        </div>

        {error && <div className="error" style={{ marginBottom: "0.75rem" }}>{error}</div>}
        {success && <div className="success" style={{ marginBottom: "0.75rem" }}>{success}</div>}

        <button type="submit" disabled={uploading} style={{ width: "auto" }}>
          {uploading ? "Uploading Attachment..." : "Upload Lab Attachment"}
        </button>
      </form>
    </div>
  );
}
