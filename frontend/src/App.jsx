import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./context/AuthContext.jsx";
import AuditLogsPage from "./pages/AuditLogsPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import NewVisitPage from "./pages/NewVisitPage.jsx";
import ResultsPage from "./pages/ResultsPage.jsx";

import Navbar from "./components/Navbar.jsx";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <div className="spinner spinner-primary" style={{ width: "32px", height: "32px" }}></div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return (
    <>
      <Navbar />
      <main className="main-layout">{children}</main>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        }
      />
      <Route
        path="/new-visit"
        element={
          <RequireAuth>
            <NewVisitPage />
          </RequireAuth>
        }
      />
      <Route
        path="/visits/:visitId/results"
        element={
          <RequireAuth>
            <ResultsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/audit-logs"
        element={
          <RequireAuth>
            <AuditLogsPage />
          </RequireAuth>
        }
      />
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
