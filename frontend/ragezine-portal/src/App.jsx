import { Navigate, Route, Routes } from "react-router-dom";

import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import SubmissionPage from "./pages/SubmissionPage";

export default function App() {
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
