import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import SubmissionPage from "./pages/SubmissionPage";
import SubmissionDetailsPage from "./pages/SubmissionDetailsPage";
import ErrorPage from "./pages/ErrorPage";

export default function App() {
  const { pathname } = useLocation();

  useEffect(() => {
    const isAdminPage = pathname === "/login" || pathname === "/dashboard" || pathname.startsWith("/dashboard/");
    const isKnownPage = pathname === "/" || pathname === "/login"
      || pathname === "/dashboard" || /^\/dashboard\/submissions\/[^/]+$/.test(pathname);
    document.title = !isKnownPage ? "Page not found — RAGE Zine"
      : isAdminPage ? "RAGE Zine admin portal" : "RAGE Zine submission portal";
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
      <Route path="*" element={<ErrorPage status={404} />} />
    </Routes>
  );
}
