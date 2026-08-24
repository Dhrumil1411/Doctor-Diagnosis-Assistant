import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";

export default function HomePage() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const saved = location.state;

  return (
    <div className="card">
      <h1>Welcome, {user.full_name}</h1>
      <p>
        Signed in as <strong>{user.email}</strong> with role{" "}
        <strong>{user.role}</strong>.
      </p>

      {saved?.savedVisitId && (
        <div className="success" role="status">
          Saved consultation for {saved.patientName} (visit{" "}
          {saved.savedVisitId.slice(0, 8)}...). The results screen arrives in
          Step 10.
        </div>
      )}

      <Link className="btn-link" to="/new-visit">
        + Start new consultation
      </Link>

      <button onClick={logout}>Sign out</button>
    </div>
  );
}
