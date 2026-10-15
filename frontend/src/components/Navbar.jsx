import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  if (!user) return null;

  const isActive = (path) => location.pathname === path;

  return (
    <header className="app-navbar">
      <div className="navbar-inner">
        <Link to="/" className="nav-brand">
          <div className="nav-logo-badge">⚕️</div>
          <div>
            <div style={{ lineHeight: "1.1", fontSize: "1rem", fontWeight: "800", color: "#0f172a" }}>
              Doctor Diagnosis Assistant
            </div>
            <div style={{ fontSize: "0.68rem", color: "#0284c7", fontWeight: "600", letterSpacing: "0.02em" }}>
              CLINICAL DECISION SUPPORT
            </div>
          </div>
        </Link>

        <nav className="nav-links">
          <Link to="/" className={`nav-link ${isActive("/") ? "active" : ""}`}>
            📋 Patients & Encounters
          </Link>
          <Link to="/new-visit" className={`nav-link ${isActive("/new-visit") ? "active" : ""}`}>
            ➕ New Consultation
          </Link>
          {user.role === "admin" && (
            <Link to="/audit-logs" className={`nav-link ${isActive("/audit-logs") ? "active" : ""}`}>
              🛡️ Audit Logs
            </Link>
          )}
        </nav>

        <div className="nav-user">
          <div className="user-badge">
            <span className="user-name">Dr. {user.full_name || user.email.split("@")[0]}</span>
            <span className="user-role-tag">{user.role}</span>
          </div>
          <button
            type="button"
            onClick={logout}
            className="btn-danger"
            style={{ padding: "0.35rem 0.75rem", fontSize: "0.78rem" }}
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
