import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import DashboardSubmissionsList from "../components/DashboardSubmissionsList";
import { getSession, logoutUser } from "../services/authService";
import { downloadCompleteArchive, downloadExcelReview } from "../services/downloadService";
import "../styles/dashboard.css";
import "../styles/nav.css";
import "../styles/description.css";
import "../styles/form.css";

function triggerBrowserDownload(blob, filename) {
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

export default function DashboardPage() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [hasStaffAccess, setHasStaffAccess] = useState(false);
  const [downloadingExcel, setDownloadingExcel] = useState(false);
  const [downloadingComplete, setDownloadingComplete] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function bootstrap() {
      try {
        const session = await getSession();
        if (!session?.authenticated || !session?.user?.is_staff) {
          navigate("/login", { replace: true });
          return;
        }
        setHasStaffAccess(true);
      } catch {
        navigate("/login", { replace: true });
        return;
      } finally {
        setCheckingSession(false);
      }
    }

    bootstrap();
  }, [navigate]);

  async function onLogout() {
    try {
      await logoutUser();
    } finally {
      navigate("/login", { replace: true });
    }
  }

  async function onDownloadComplete() {
    setDownloadingComplete(true);

    try {
      const { blob, filename } = await downloadCompleteArchive();
      triggerBrowserDownload(blob, filename);
    } finally {
      setDownloadingComplete(false);
    }
  }

  async function onDownloadExcel() {
    setDownloadingExcel(true);

    try {
      const { blob, filename } = await downloadExcelReview();
      triggerBrowserDownload(blob, filename);
    } finally {
      setDownloadingExcel(false);
    }
  }

  if (checkingSession) {
    return (
      <main>
        <div className="portal-page">
          <section className="hero" id="home">
            <div className="hero-panel">
              <div className="hero-copy">
                <p>Checking session...</p>
              </div>
            </div>
          </section>
        </div>
      </main>
    );
  }

  if (!hasStaffAccess) {
    return null;
  }

  return (
    <main>
      <div className="portal-page dashboard-page">
        <nav>
          <ul>
            <li><Link to="/">submissions</Link></li>
            <li>
              <button type="button" className="menu-button" onClick={onLogout}>
                log out
              </button>
            </li>
          </ul>

          <div className="buttons">
            <button
              type="button"
              className="menu-button"
              onClick={onDownloadExcel}
              disabled={downloadingExcel}
            >
              {downloadingExcel ? "downloading..." : "excel ↓"}
            </button>
            <button
              type="button"
              className="menu-button"
              onClick={onDownloadComplete}
              disabled={downloadingComplete}
            >
              {downloadingComplete ? "downloading..." : "complete ↓"}
            </button>
          </div>
        </nav>

        <DashboardSubmissionsList />
      </div>
    </main>
  );
}
