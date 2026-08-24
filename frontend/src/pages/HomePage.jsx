import { useAuth } from "../context/AuthContext.jsx";

export default function HomePage() {
  const { user, logout } = useAuth();

  return (
    <div className="card">
      <h1>Welcome, {user.full_name}</h1>
      <p>
        Signed in as <strong>{user.email}</strong> with role{" "}
        <strong>{user.role}</strong>.
      </p>
      <p className="muted">
        Patient intake (Step 9) and the diagnosis results screen (Step 10) will
        live here. This skeleton proves login + API wiring works.
      </p>
      <button onClick={logout}>Sign out</button>
    </div>
  );
}
