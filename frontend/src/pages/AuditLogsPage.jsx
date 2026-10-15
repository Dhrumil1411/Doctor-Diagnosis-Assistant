import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function AuditLogsPage() {
  const { user } = useAuth();
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  if (user && user.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  async function loadLogs() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append("limit", limit.toString());
      params.append("offset", offset.toString());
      if (actionFilter) params.append("action", actionFilter);
      if (entityFilter) params.append("entity_type", entityFilter);

      const data = await api.get(`/audit-logs?${params.toString()}`);
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLogs();
  }, [limit, offset, actionFilter, entityFilter]);

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  function getActionBadgeStyle(act) {
    switch (act) {
      case "create":
        return { background: "#e6f4ea", color: "#137333", border: "1px solid #ceead6" };
      case "update":
        return { background: "#e8f0fe", color: "#1a73e8", border: "1px solid #d2e3fc" };
      case "diagnosis_decision":
        return { background: "#f3e8fd", color: "#8430ce", border: "1px solid #e9d2fd" };
      case "predict":
        return { background: "#fef7e0", color: "#b06000", border: "1px solid #fde293" };
      case "reason":
        return { background: "#e0f2f1", color: "#00695c", border: "1px solid #b2dfdb" };
      case "delete":
        return { background: "#fce8e6", color: "#c5221f", border: "1px solid #fad2cf" };
      default:
        return { background: "#f1f3f4", color: "#5f6368", border: "1px solid #dadce0" };
    }
  }

  return (
    <div className="container">
      <div className="card flex-between" style={{ alignItems: "center" }}>
        <div>
          <Link to="/" style={{ color: "var(--primary)", textDecoration: "none", fontSize: "0.9rem" }}>
            ← Back to Dashboard
          </Link>
          <h1 style={{ marginTop: "0.25rem", marginBottom: "0.25rem" }}>Security & System Audit Log</h1>
          <p className="muted">
            Immutable regulatory audit trail tracking all clinical data creations, diagnostic inferences, and doctor actions.
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", display: "block" }}>
            Total Logged Events: <strong>{total}</strong>
          </span>
          <button
            onClick={() => loadLogs()}
            style={{
              marginTop: "0.5rem",
              padding: "0.4rem 0.8rem",
              fontSize: "0.85rem",
              background: "white",
              border: "1px solid var(--border)",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="card" style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ flex: "1 1 200px" }}>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: "bold", marginBottom: "0.25rem" }}>
            Filter by Action
          </label>
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setOffset(0);
            }}
            style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid var(--border)" }}
          >
            <option value="">All Actions</option>
            <option value="create">create</option>
            <option value="update">update</option>
            <option value="diagnosis_decision">diagnosis_decision</option>
            <option value="predict">predict</option>
            <option value="reason">reason</option>
            <option value="login">login</option>
            <option value="delete">delete</option>
          </select>
        </div>

        <div style={{ flex: "1 1 200px" }}>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: "bold", marginBottom: "0.25rem" }}>
            Filter by Entity Type
          </label>
          <select
            value={entityFilter}
            onChange={(e) => {
              setEntityFilter(e.target.value);
              setOffset(0);
            }}
            style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid var(--border)" }}
          >
            <option value="">All Entities</option>
            <option value="patient">patient</option>
            <option value="visit">visit</option>
            <option value="symptom">symptom</option>
            <option value="vitals">vitals</option>
            <option value="lab_result">lab_result</option>
            <option value="user">user</option>
          </select>
        </div>

        <div style={{ flex: "0 0 120px" }}>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: "bold", marginBottom: "0.25rem" }}>
            Per Page
          </label>
          <select
            value={limit}
            onChange={(e) => {
              setLimit(Number(e.target.value));
              setOffset(0);
            }}
            style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid var(--border)" }}
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="card" style={{ background: "#fce8e6", borderColor: "#fad2cf", color: "#c5221f" }}>
          Error loading logs: {error}
        </div>
      )}

      {/* Logs Table */}
      <div className="card" style={{ overflowX: "auto" }}>
        {loading ? (
          <p className="muted" style={{ padding: "1rem" }}>Loading audit records...</p>
        ) : logs.length === 0 ? (
          <p className="muted" style={{ padding: "1rem" }}>No audit log entries matching criteria.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--border)", textAlign: "left" }}>
                <th style={{ padding: "0.75rem 0.5rem" }}>ID</th>
                <th style={{ padding: "0.75rem 0.5rem" }}>Actor</th>
                <th style={{ padding: "0.75rem 0.5rem" }}>Action</th>
                <th style={{ padding: "0.75rem 0.5rem" }}>Entity</th>
                <th style={{ padding: "0.75rem 0.5rem" }}>Entity ID</th>
                <th style={{ padding: "0.75rem 0.5rem" }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => {
                const isExpanded = expandedId === log.id;
                return (
                  <tr
                    key={log.id}
                    style={{
                      borderBottom: "1px solid var(--border)",
                      verticalAlign: "top",
                    }}
                  >
                    <td style={{ padding: "0.6rem 0.5rem", fontWeight: "bold", color: "#5f6368" }}>
                      #{log.id}
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem" }}>
                      {log.actor_name ? (
                        <div>
                          <strong>{log.actor_name}</strong>
                          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{log.actor_email}</div>
                        </div>
                      ) : log.actor_user_id ? (
                        <code style={{ fontSize: "0.75rem" }}>{log.actor_user_id.slice(0, 8)}...</code>
                      ) : (
                        <span className="muted">System / Anonymous</span>
                      )}
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "0.2rem 0.5rem",
                          borderRadius: "4px",
                          fontSize: "0.78rem",
                          fontWeight: "bold",
                          ...getActionBadgeStyle(log.action),
                        }}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem" }}>
                      <span style={{ textTransform: "capitalize", fontWeight: "500" }}>{log.entity_type}</span>
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem" }}>
                      {log.entity_id ? (
                        <code style={{ fontSize: "0.78rem", background: "#f1f3f4", padding: "0.1rem 0.3rem", borderRadius: "3px" }}>
                          {log.entity_id.slice(0, 8)}...
                        </code>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem" }}>
                      {log.detail ? (
                        <div>
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : log.id)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--primary)",
                              cursor: "pointer",
                              fontSize: "0.8rem",
                              padding: 0,
                              textDecoration: "underline",
                            }}
                          >
                            {isExpanded ? "Hide JSON ▲" : "View JSON ▼"}
                          </button>
                          {isExpanded && (
                            <pre
                              style={{
                                marginTop: "0.5rem",
                                padding: "0.5rem",
                                background: "#202124",
                                color: "#8ab4f8",
                                borderRadius: "4px",
                                fontSize: "0.75rem",
                                overflowX: "auto",
                                maxHeight: "200px",
                              }}
                            >
                              {JSON.stringify(log.detail, null, 2)}
                            </pre>
                          )}
                        </div>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {/* Pagination controls */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: "1rem",
            paddingTop: "0.75rem",
            borderTop: "1px solid var(--border)",
          }}
        >
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            Showing {logs.length > 0 ? offset + 1 : 0} – {Math.min(offset + limit, total)} of {total}
          </span>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              disabled={offset === 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - limit))}
              style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "4px",
                border: "1px solid var(--border)",
                background: offset === 0 ? "#f1f3f4" : "white",
                cursor: offset === 0 ? "not-allowed" : "pointer",
              }}
            >
              ← Previous
            </button>
            <span style={{ alignSelf: "center", fontSize: "0.85rem", fontWeight: "bold" }}>
              Page {currentPage} of {totalPages}
            </span>
            <button
              disabled={offset + limit >= total || loading}
              onClick={() => setOffset(offset + limit)}
              style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "4px",
                border: "1px solid var(--border)",
                background: offset + limit >= total ? "#f1f3f4" : "white",
                cursor: offset + limit >= total ? "not-allowed" : "pointer",
              }}
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
