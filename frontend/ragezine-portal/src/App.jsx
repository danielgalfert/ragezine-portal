import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import SubmissionPage from "./pages/SubmissionPage";
import SubmissionDetailsPage from "./pages/SubmissionDetailsPage";

export default function App() {
  const { pathname } = useLocation();

  useEffect(() => {
    const isAdminPage = pathname === "/login" || pathname === "/dashboard" || pathname.startsWith("/dashboard/");
    document.title = isAdminPage ? "RAGE Zine admin portal" : "RAGE Zine submission portal";
  }, [pathname]);

  return (
    <Routes>
      <Route
        path="/"
        element={
          <main>
            <SubmissionPage />
          </main>
        }
      />
      <Route
        path="/login"
        element={
          <main>
            <LoginPage />
          </main>
        }
      />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/dashboard/submissions/:id" element={<SubmissionDetailsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
